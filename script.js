const messagesEl = document.querySelector("#messages");
const form = document.querySelector("#chatForm");
const input = document.querySelector("#messageInput");
const sendBtn = document.querySelector("#sendBtn");
const clearBtn = document.querySelector("#clearBtn");
const modelName = document.querySelector("#modelName");
const apiStatus = document.querySelector("#apiStatus");

const welcomeText = `Hi! I am your GenAI Intern Assistant.\n\nAsk me to explain concepts, debug code, create project ideas, or improve your internship work.`;

function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

function addMessage(role, content, options = {}) {
  const msg = document.createElement("div");
  msg.className = `message ${role} ${options.error ? "error" : ""}`;

  const avatar = document.createElement("div");
  avatar.className = "avatar";
  avatar.textContent = role === "user" ? "U" : "AI";

  const bubble = document.createElement("div");
  bubble.className = "bubble";
  bubble.innerHTML = options.html ? content : escapeHtml(content);

  msg.appendChild(avatar);
  msg.appendChild(bubble);
  messagesEl.appendChild(msg);
  messagesEl.scrollTop = messagesEl.scrollHeight;
  return msg;
}

function typingMessage() {
  return addMessage("assistant", `<span class="typing"><span></span><span></span><span></span></span>`, { html: true });
}

function autoResize() {
  input.style.height = "auto";
  input.style.height = `${input.scrollHeight}px`;
}

async function loadHealth() {
  try {
    const res = await fetch("/api/health");
    const data = await res.json();
    modelName.textContent = data.model || "OpenAI model";
    apiStatus.textContent = data.apiKeyConfigured ? "API key configured" : "Missing API key in .env";
  } catch {
    modelName.textContent = "Backend offline";
    apiStatus.textContent = "Start Flask server first";
  }
}

async function loadHistory() {
  try {
    const res = await fetch("/api/history");
    const data = await res.json();
    messagesEl.innerHTML = "";
    if (!data.messages || data.messages.length === 0) {
      addMessage("assistant", welcomeText);
      return;
    }
    data.messages.forEach((m) => addMessage(m.role, m.content));
  } catch {
    addMessage("assistant", welcomeText);
  }
}

async function sendMessage(message) {
  addMessage("user", message);
  const loader = typingMessage();
  sendBtn.disabled = true;

  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message }),
    });
    const data = await res.json();
    loader.remove();

    if (!res.ok) {
      addMessage("assistant", data.error || "Something went wrong.", { error: true });
      return;
    }
    addMessage("assistant", data.reply);
  } catch (error) {
    loader.remove();
    addMessage("assistant", "Network error. Make sure Flask is running on http://127.0.0.1:5000", { error: true });
  } finally {
    sendBtn.disabled = false;
    input.focus();
  }
}

form.addEventListener("submit", (event) => {
  event.preventDefault();
  const message = input.value.trim();
  if (!message) return;
  input.value = "";
  autoResize();
  sendMessage(message);
});

input.addEventListener("input", autoResize);
input.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    form.requestSubmit();
  }
});

document.querySelectorAll(".prompt").forEach((button) => {
  button.addEventListener("click", () => {
    input.value = button.textContent;
    autoResize();
    input.focus();
  });
});

clearBtn.addEventListener("click", async () => {
  await fetch("/api/clear", { method: "POST" });
  messagesEl.innerHTML = "";
  addMessage("assistant", welcomeText);
});

loadHealth();
loadHistory();
