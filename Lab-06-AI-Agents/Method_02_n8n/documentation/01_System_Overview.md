---

## System Overview – n8n AI Agent

### 1. Introduction

This implementation explores the development of an AI-powered conversational agent using n8n and Ollama.

The agent was designed to interact with users through a chat interface and utilize connected tools to retrieve information from Google Calendar and Gmail.

A conversational memory component was incorporated to allow the agent to retain context during interactions.

### 2. System Objectives

- Develop an AI agent using a visual workflow automation platform.

- Utilize a locally hosted Large Language Model.

- Implement conversational memory.

- Integrate external services.

- Explore tool-based AI interactions.

- Understand the components of an AI agent workflow.

### 3. System Components

| `Component`| `Description` |
| ---------- | ----------- |
| `Chat Trigger` | Initiates the workflow when a chat message is received. |
| `AI Agent` | Processes the user request and determines the appropriate action. |
| `Ollama Chat Model` | Generates responses using a locally hosted LLM. |
| `Simple Memory` | Stores conversational context. |
| `Google Calendar` | Enables the agent to retrieve calendar events and create events. |
| `Gmail` | Enables the agent to retrieve email information. |

### 4. System Workflow

The system operates through the following process:

1. A user submits a message through the chat interface.

2. The Chat Trigger initiates the workflow.

3. The AI Agent receives the user message.

4. The Ollama Chat Model processes the request.

5. The agent uses conversational memory when relevant.

6. If necessary, the agent selects an appropriate tool.

7. The selected tool retrieves information or performs an action.

8. The AI Agent processes the returned information.

9. A response is provided to the user.

### 5. Architecture

The system consists of a chat interface, AI orchestration layer, local LLM, memory component, and external service integrations.

The AI Agent acts as the central component connecting the language model with available tools.

### 6. Workflow Files

The exported n8n workflows are available in the workflow/ directory.
