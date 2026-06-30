# GenAI Intern Assistant — Improved Version

A clean Flask + OpenAI chatbot project with a modern responsive frontend, chat history, better error handling and safe API-key usage through `.env`.

<img width="1536" height="1024" alt="Gen AI Intern Assistant" src="https://github.com/user-attachments/assets/a3ea5c87-4275-406c-b840-b81265673c35" />


## Setup in VS Code

```bash
cd genai_intern_assistant_improved
python -m venv .venv
.venv\Scripts\activate   # Windows
# source .venv/bin/activate  # macOS/Linux
pip install -r requirements.txt
copy .env.example .env     # Windows
# cp .env.example .env      # macOS/Linux
```

<img width="1586" height="992" alt="Gen AI Assistant" src="https://github.com/user-attachments/assets/48dbb3d2-850c-40c9-b78d-f608b5681d26" />


Open `.env` and add your API key:

```env
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-5.5
APP_SECRET_KEY=change-this-secret-key
```

Run:

```bash
python app.py
```

Open:

```text
http://127.0.0.1:5000
```

## Improvements made

- Modern glassmorphism UI with responsive layout
- Interactive prompt buttons
- Chat history saved in SQLite per browser session
- Clear-chat button
- Stronger Flask API validation and error handling
- Uses environment variables instead of exposing API keys in frontend code
- Uses the newer OpenAI Responses API style
- Cleaner code structure and comments-ready formatting

## Important

Do not upload your `.env` file to GitHub. Keep your OpenAI API key private.
