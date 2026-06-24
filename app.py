import os
import re
import sqlite3
import logging
from datetime import datetime
from difflib import SequenceMatcher
from typing import List, Dict, Optional

from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

APP_NAME = "Internee.pk AI Intern Assistant"
DB_PATH = "chatbot.db"
OPENAI_MODEL = "gpt-4.1-mini"

app = Flask(__name__)
CORS(app)

logging.basicConfig(level=logging.INFO)
api_key = os.getenv("OPENAI_API_KEY")

print("Key Found:", bool(api_key))

if not api_key:
    raise ValueError("OPENAI_API_KEY not found. Create a .env file in the same folder as app.py")

client = OpenAI(api_key=api_key)


KNOWLEDGE_BASE = [
    {
        "title": "Internship Tasks",
        "category": "task_guidelines",
        "content": """
Interns receive weekly or project-based tasks from their dashboard or supervisor.
Each task should be completed before the deadline. Submit clean, original work.
Always read task instructions carefully before starting. If unclear, ask your mentor.
"""
    },
    {
        "title": "Submission Policy",
        "category": "policy",
        "content": """
Submit tasks through the official Internee.pk portal or assigned submission method.
Late submissions may affect your evaluation. Do not submit copied or AI-generated work without understanding it.
Files should be properly named and formatted.
"""
    },
    {
        "title": "Attendance and Availability",
        "category": "policy",
        "content": """
Interns should remain active, check updates regularly, and respond to mentor messages.
If you cannot complete a task on time, inform your supervisor early with a valid reason.
"""
    },
    {
        "title": "Certificate Criteria",
        "category": "faq",
        "content": """
Certificates are usually issued after successful completion of assigned tasks,
proper participation, and meeting internship requirements.
Poor performance, plagiarism, or inactivity can affect certificate eligibility.
"""
    },
    {
        "title": "Code Quality Guidelines",
        "category": "task_guidelines",
        "content": """
Code should be clean, readable, tested, and well-structured.
Use meaningful variable names, comments where needed, and avoid unnecessary complexity.
Always check for bugs before submission.
"""
    }
]


FAQS = {
    "how to submit task": "Submit your task through the official Internee.pk portal or the method shared by your supervisor.",
    "certificate": "Certificates are usually given after successful completion of tasks, active participation, and meeting internship requirements.",
    "deadline": "You should complete tasks before the deadline. If you need extra time, contact your mentor early.",
    "mentor": "You can contact your assigned mentor or supervisor through the official communication channel.",
    "plagiarism": "Copied work is not allowed. Submit original work and understand anything you use from references or AI tools.",
    "task guidelines": "Read the instructions carefully, follow the required format, test your work, and submit before the deadline."
}


SYSTEM_PROMPT = """
You are Internee.pk's AI Intern Assistant.
Your job is to answer intern questions about tasks, policies, FAQs, deadlines, certificates, submissions, and guidelines.

Rules:
- Be clear, professional, and helpful.
- Use the provided knowledge base first.
- If information is missing, say that the intern should confirm with their mentor or official Internee.pk support.
- Do not invent official policy.
- Keep answers concise but useful.
"""


def init_db() -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS chats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_message TEXT NOT NULL,
                bot_response TEXT NOT NULL,
                intent TEXT,
                created_at TEXT NOT NULL
            )
        """)
        conn.commit()


def clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, clean_text(a), clean_text(b)).ratio()


def detect_intent(message: str) -> str:
    msg = clean_text(message)

    intent_keywords = {
        "task_guidelines": ["task", "assignment", "submit", "submission", "project", "guideline"],
        "policy": ["policy", "rule", "late", "attendance", "deadline", "plagiarism"],
        "certificate": ["certificate", "completion", "eligible"],
        "mentor_support": ["mentor", "supervisor", "help", "contact", "support"],
        "faq": ["how", "what", "when", "where", "why"]
    }

    best_intent = "general"
    best_score = 0

    for intent, keywords in intent_keywords.items():
        score = sum(1 for keyword in keywords if keyword in msg)
        if score > best_score:
            best_score = score
            best_intent = intent

    return best_intent


def faq_match(message: str) -> Optional[str]:
    msg = clean_text(message)

    best_answer = None
    best_score = 0.0

    for question, answer in FAQS.items():
        score = similarity(msg, question)
        if question in msg:
            score += 0.4
        if score > best_score:
            best_score = score
            best_answer = answer

    return best_answer if best_score >= 0.55 else None


def retrieve_knowledge(message: str, limit: int = 3) -> List[Dict]:
    msg = clean_text(message)
    results = []

    for item in KNOWLEDGE_BASE:
        searchable = clean_text(item["title"] + " " + item["category"] + " " + item["content"])
        score = similarity(msg, searchable)

        for word in msg.split():
            if len(word) > 3 and word in searchable:
                score += 0.08

        results.append({**item, "score": score})

    results.sort(key=lambda x: x["score"], reverse=True)
    return [r for r in results[:limit] if r["score"] > 0.18]


def build_context(docs: List[Dict]) -> str:
    if not docs:
        return "No matching knowledge-base content found."

    return "\n\n".join(
        f"Title: {doc['title']}\nCategory: {doc['category']}\nContent: {doc['content']}"
        for doc in docs
    )


def openai_answer(message: str, context: str) -> str:
    if not os.getenv("OPENAI_API_KEY"):
        return (
            "I found related information, but OpenAI API is not configured. "
            "Please add OPENAI_API_KEY in your .env file."
        )

    response = client.responses.create(
        model=OPENAI_MODEL,
        input=[
            {
                "role": "system",
                "content": SYSTEM_PROMPT
            },
            {
                "role": "user",
                "content": f"""
Knowledge base:
{context}

Intern question:
{message}

Answer using the knowledge base. If exact information is unavailable, say to confirm with mentor/support.
"""
            }
        ],
        temperature=0.2,
        max_output_tokens=350
    )

    return response.output_text.strip()


def save_chat(user_message: str, bot_response: str, intent: str) -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            INSERT INTO chats (user_message, bot_response, intent, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (user_message, bot_response, intent, datetime.utcnow().isoformat())
        )
        conn.commit()


@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "app": APP_NAME,
        "status": "running",
        "routes": {
            "chat": "POST /chat",
            "health": "GET /health",
            "history": "GET /history"
        }
    })


@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "healthy",
        "database": DB_PATH,
        "openai_configured": bool(os.getenv("OPENAI_API_KEY"))
    })


@app.route("/chat", methods=["POST"])
def chat():
    try:
        data = request.get_json(force=True)
        message = data.get("message", "").strip()

        if not message:
            return jsonify({"error": "Message is required."}), 400

        intent = detect_intent(message)

        faq_response = faq_match(message)
        if faq_response:
            response = faq_response
        else:
            docs = retrieve_knowledge(message)
            context = build_context(docs)
            response = openai_answer(message, context)

        save_chat(message, response, intent)

        return jsonify({
            "bot": response,
            "intent": intent,
            "timestamp": datetime.utcnow().isoformat()
        })

    except Exception as e:
        logging.exception("Chat error")
        return jsonify({
            "error": "Something went wrong. Please try again.",
            "details": str(e)
        }), 500


@app.route("/history", methods=["GET"])
def history():
    limit = min(int(request.args.get("limit", 20)), 100)

    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute(
            """
            SELECT user_message, bot_response, intent, created_at
            FROM chats
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,)
        ).fetchall()

    return jsonify([
        {
            "user": row[0],
            "bot": row[1],
            "intent": row[2],
            "created_at": row[3]
        }
        for row in rows
    ])


@app.errorhandler(404)
def not_found(_):
    return jsonify({"error": "Route not found."}), 404


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000, debug=True)