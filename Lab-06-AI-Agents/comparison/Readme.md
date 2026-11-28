
# Lab 06 Comparison — Python Agent vs. n8n Workflow

## Comparison Overview
This directory compares two approaches for building AI agents in Lab 06:
- **Method 01 (`Method_01_Python`):** Code-first local Python agent using Ollama (`llama3.2:3b`), custom Python tools, local memory/RAG stores, and direct Google API toolkits.
- **Method 02 (`Method_02_n8n`):** Visual node-based workflow orchestration using n8n.

## Side-by-Side Summary

| Dimension | Method 01 (`Method_01_Python`) | Method 02 (`Method_02_n8n`) |
| :--- | :--- | :--- |
| **Control & Customization** | Full programmatic control in Python over tool routing, error handling, and local state | Visual node graph configuration with built-in workflow triggers and nodes |
| **Model & Runtime** | Local execution via Python + Ollama (`llama3.2:3b`) | Workflow engine nodes and configured LLM/API connections |
| **Memory & Retrieval** | Direct integration with local SQLite memory and vector/RAG stores | Workflow state/context and connected data nodes |
| **Debugging & Version Control** | Standard Git diffs on `.py` code; terminal tracebacks | Workflow JSON exports and node execution logs |

## Key Takeaway
Python gives fine-grained control over local models, custom tool filtering, and OAuth/error handling, whereas n8n excels at visual workflow wiring and rapid node-based automation.
