# Documentation — Lab 06 (`Method_01_Python`)

## Architecture Summary
`src/mem_rag_agent.py` orchestrates a tool-calling loop backed by Ollama (`llama3.2:3b`):
1. **Prompt & Tool Binding:** Binds desktop utilities, memory/RAG tools, and filtered Google Calendar/Gmail tools to the LLM.
2. **Tool Execution:** Dispatches selected tool calls, captures outputs, and feeds results back into the conversation context.
3. **Persistence:** Retains conversational memory and knowledge retrieval state locally while excluding runtime artifacts and secrets via `.gitignore`.

## Google OAuth 2.0 & Toolkit Notes
- **Authentication Flow:** Uses `InstalledAppFlow` with `credentials.json` to generate `token.json` locally on first sign-in and refreshes expired tokens automatically.
- **Testing Access (`Error 403: access_denied`):** While the Google Cloud OAuth consent screen is in *Testing* mode, test accounts must be added under **Test users** before signing in.
- **Toolkit Instantiation:** Builds Google API service clients (`calendar` v3 and `gmail` v1) with OAuth credentials and wraps them in `CalendarToolkit` and `GmailToolkit`, filtering to focused tool names so smaller local models route reliably.

## Security & Repository Hygiene
- Ignored via `.gitignore`: `.venv/`, `__pycache__/`, `*.pyc`, `chroma_db/`, `student_memory.db`, `credentials.json`, `token.json`, and `.env`.
