# Lab 06 — Method 01: Local AI Agent (Python, Ollama, Memory & RAG)

## Overview
This implementation builds a local desktop AI assistant using Python 3.13 and Ollama (`llama3.2:3b`), combining tool calling, persistent SQLite memory, RAG/knowledge search, and Google Calendar / Gmail integration via OAuth 2.0.

## Key Capabilities
- **Local LLM & Tool Routing:** Runs `llama3.2:3b` locally via Ollama with bound tool definitions.
- **Desktop & Utility Tools:** Supports calculator/app launching, date/time lookups, file search, text file creation, and system information.
- **Persistent Memory & Knowledge Retrieval:** Stores and retrieves user/student memory and queries local knowledge/vector storage.
- **Google Workspace Integration:** Connects to Google Calendar and Gmail using `credentials.json` / `token.json` (kept out of version control via `.gitignore`) and `langchain-google-community` toolkits.

## Setup & Run
1. Create and activate the virtual environment:
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
