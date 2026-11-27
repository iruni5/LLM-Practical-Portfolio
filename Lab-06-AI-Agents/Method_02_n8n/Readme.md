# Method 2 – Intelligent University Assistant Using n8n

## Overview

This implementation explores the development of an Intelligent University Assistant using n8n, a visual workflow automation platform. The system integrates a locally hosted Large Language Model (LLM) with conversational memory and external services to create an interactive assistant.

## Objectives

- Integrate a locally hosted LLM using Ollama.
- Build an AI Agent using n8n.
- Implement conversational memory.
- Integrate Google Calendar for event retrieval and creation.
- Integrate Gmail for email retrieval.
- Explore visual workflow-based AI application development.

## Technologies Used

| Technology | Purpose |
|---|---|
| n8n | Workflow orchestration and AI Agent implementation |
| Ollama | Local LLM hosting |
| Llama 3.2 (3B) | Language model |
| Simple Memory | Conversational memory |
| Google Calendar API | Calendar event retrieval and creation |
| Gmail API | Email retrieval |

## Workflow

The assistant receives user queries through the chat interface. The AI Agent processes the queries using the connected language model and, when required, interacts with external tools such as Google Calendar and Gmail.

## Implementation Progress

- [x] n8n environment setup
- [x] Ollama integration
- [x] AI Agent configuration
- [x] Conversational memory
- [x] Google Calendar event retrieval
- [x] Google Calendar event creation
- [x] Gmail email retrieval – Get Many


## Evidence

Screenshots documenting the configurations and tests are available in the `screenshots` directory.

## Workflow Export

The n8n workflow export will be added to the `workflow` directory after completion.
