from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request, session
from flask_cors import CORS
from openai import OpenAI, OpenAIError

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "chat_history.db"

load_dotenv(BASE_DIR / ".env")

app = Flask(__name__)
app.secret_key = os.getenv("APP_SECRET_KEY", "dev-secret-change-me")
CORS(app)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY")) if os.getenv("OPENAI_API_KEY") else None
MODEL = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")

SYSTEM_PROMPT = """
You are GenAI Intern Assistant, a helpful AI mentor for interns and junior developers.
Give clear, practical, high-quality answers like a senior engineer: explain concepts, provide clean code,
point out mistakes, and keep the tone friendly. Use examples when useful. If code is requested, prefer
complete working code and mention how to run it.
""".strip()


def init_db() -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
                content TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.commit()


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_session_id() -> str:
    if "chat_session_id" not in session:
        session["chat_session_id"] = str(uuid4())
    return session["chat_session_id"]


def save_message(session_id: str, role: str, content: str) -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "INSERT INTO messages (session_id, role, content, created_at) VALUES (?, ?, ?, ?)",
            (session_id, role, content, now_iso()),
        )
        conn.commit()


def load_recent_messages(session_id: str, limit: int = 12) -> list[dict[str, str]]:
    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute(
            """
            SELECT role, content
            FROM messages
            WHERE session_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (session_id, limit),
        ).fetchall()
    return [{"role": role, "content": content} for role, content in reversed(rows)]


def build_openai_input(history: list[dict[str, str]], user_message: str) -> list[dict[str, str]]:
    items: list[dict[str, str]] = [
        {"role": "system", "content": SYSTEM_PROMPT}
    ]
    for msg in history:
        items.append({"role": msg["role"], "content": msg["content"]})
    items.append({"role": "user", "content": user_message})
    return items


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/health")
def health():
    return jsonify({"ok": True, "model": MODEL, "apiKeyConfigured": client is not None})


@app.route("/api/history")
def history():
    session_id = get_session_id()
    return jsonify({"messages": load_recent_messages(session_id, limit=30)})


@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.get_json(silent=True) or {}
    user_message = (data.get("message") or "").strip()

    if not user_message:
        return jsonify({"error": "Please type a message first."}), 400

    if client is None:
        return jsonify({"error": "OPENAI_API_KEY is missing. Add it in your .env file."}), 500

    session_id = get_session_id()
    history = load_recent_messages(session_id)

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=build_openai_input(history, user_message),
            temperature=0.7,
            max_tokens=1200,
        )
        assistant_reply = response.choices[0].message.content.strip()
        if not assistant_reply:
            assistant_reply = "I received your message, but I could not generate a response. Please try again."

        save_message(session_id, "user", user_message)
        save_message(session_id, "assistant", assistant_reply)
        return jsonify({"reply": assistant_reply})

    except OpenAIError as exc:
        return jsonify({"error": f"OpenAI API error: {str(exc)}"}), 502
    except Exception as exc:
        return jsonify({"error": f"Server error: {str(exc)}"}), 500


@app.route("/api/clear", methods=["POST"])
def clear_history():
    session_id = get_session_id()
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
        conn.commit()
    return jsonify({"ok": True})


if __name__ == "__main__":
    init_db()
    app.run(host="127.0.0.1", port=5000, debug=True)
else:
    init_db()
