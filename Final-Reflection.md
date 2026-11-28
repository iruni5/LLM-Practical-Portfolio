# Final Reflection — Practical LLM Portfolio

## What I Built and Learned
Across these practical labs, I moved from foundational model workflows and retrieval pipelines to building tool-using AI agents capable of interacting with local utilities, persistent memory, knowledge bases, and external APIs such as Google Calendar and Gmail.

## Engineering Challenges & Solutions
- **Environment & Dependency Alignment:** Resolved package/version mismatches and ensured installations targeted the active Python virtual environment.
- **Small-Model Tool Routing:** Smaller local models (such as 3B parameter models) perform best with clear prompts, focused tool sets, and explicit fallback/error handling.
- **OAuth & Secret Management:** Configured OAuth consent test users for unverified testing apps and kept `credentials.json`, `token.json`, virtual environments, and local databases out of Git using `.gitignore`.

## Future Improvements
- Add automated test scripts for tool routing and RAG/memory retrieval accuracy.
- Expand evaluation logging to compare response latency, tool-call precision, and failure recovery across models.
