# n8n Workflow Files

This directory contains the exported JSON files of the workflows developed using n8n during Lab 06 – AI Agents.

## Workflows

### 01 – Ollama AI Agent

An intelligent conversational assistant built using n8n, Ollama, and integrations with Google Calendar and Gmail.

**Main components:**
- AI Agent
- Ollama Chat Model
- Simple Memory
- Google Calendar integration
- Gmail integration

**File:** `01_Ollama_AI_Agent.json`

### 02 – First n8n Workflow

A basic workflow created to understand the fundamental workflow structure and data flow within n8n.

**Main components:**
- Manual Trigger
- Edit Fields

**File:** `02_First_n8n_Workflow.json`

## Importing the Workflows

1. Open n8n.
2. Create or open a workflow.
3. Open the workflow menu.
4. Select Import from File.
5. Select the desired JSON file.
6. Configure the required credentials and integrations.
7. Test the workflow.

Credentials are not included in these exported files. Integrations must be configured separately before use.

---
```

**Save it.**

---

# Step 3 – Complete `Method_02_n8n/Readme.md`

Now navigate to:

```text
Method_02_n8n/
```

Open the existing `Readme.md`.

Replace its content with the following.

# Method 02 – AI Agent Implementation Using n8n

## Overview

This implementation explores the development of an AI-powered agent using n8n, a visual workflow automation platform.

The AI agent was developed using Ollama as the local Large Language Model (LLM) provider and integrated with Google Calendar and Gmail to explore how AI agents can interact with external services and perform tasks using tools.

A separate simple workflow was also developed to understand the fundamental workflow creation and execution process in n8n.

## Objectives

- Understand visual workflow automation using n8n.
- Develop an AI agent using a locally hosted LLM.
- Connect an AI agent with external applications.
- Implement conversational memory.
- Explore tool-based interactions with Google Calendar and Gmail.
- Export workflows for documentation and reuse.

## Technology Stack

| Technology | Purpose |
|---|---|
| n8n | Workflow automation and AI agent orchestration |
| Ollama | Local LLM execution |
| Llama 3.2:3b | Language model used by the agent |
| Simple Memory | Maintaining conversational context |
| Google Calendar API | Calendar event retrieval and creation |
| Gmail API | Email retrieval |
| Docker | Running n8n in a containerized environment |

## Project Structure

```text
Method_02_n8n/
│
├── documentation/
│
├── screenshots/
│
├── workflow/
│
└── Readme.md
```

## Implementations

### 1. Basic n8n Workflow

A simple workflow was created using a Manual Trigger and Edit Fields node.

This implementation demonstrates:

- Manual workflow execution.
- Node-based workflow design.
- Data assignment.
- Workflow execution and output inspection.

### 2. Ollama AI Agent

An AI agent was created using n8n and Ollama.

The workflow incorporates:

- Chat Trigger.
- AI Agent.
- Ollama Chat Model.
- Simple Memory.
- Google Calendar tools.
- Gmail tools.

The agent was designed to interact with connected services through tools while maintaining conversational context.

## Documentation

Detailed implementation information, configuration instructions, testing evidence, and troubleshooting information are available in the `documentation/` directory.

## Workflow Files

The exported workflows are available in the `workflow/` directory.

## Screenshots

Screenshots demonstrating the setup, workflow configuration, integrations, and testing are available in the `screenshots/` directory.

## Notes

- Ollama must be installed and configured separately.
- The required Ollama model must be available locally.
- Google Calendar and Gmail require appropriate OAuth credentials.
- Imported workflows may require reconfiguration of credentials.
- The workflow exports do not contain actual authentication secrets.

---
```

---

# Step 4 – Complete the `documentation` folder

Inside:

```text
Method_02_n8n/documentation/
```

We will create **5 Markdown files**.

| File | Purpose |
|---|---|
| `01_System_Overview.md` | Explain the overall AI Agent system. |
| `02_Setup_and_Installation.md` | Explain the installation and setup. |
| `03_Integrations.md` | Explain Gmail and Google Calendar integrations. |
| `04_Testing_and_Evidence.md` | Explain testing and results. |
| `05_Troubleshooting.md` | Document errors and their solutions. |

---

## Step 4.1 – `01_System_Overview.md`

Create the file:

```text
01_System_Overview.md
```

Copy this content:

# System Overview – n8n AI Agent

## 1. Introduction

This implementation explores the development of an AI-powered conversational agent using n8n and Ollama.

The agent was designed to interact with users through a chat interface and utilize connected tools to retrieve information from Google Calendar and Gmail.

A conversational memory component was incorporated to allow the agent to retain context during interactions.

## 2. System Objectives

- Develop an AI agent using a visual workflow automation platform.
- Utilize a locally hosted Large Language Model.
- Implement conversational memory.
- Integrate external services.
- Explore tool-based AI interactions.
- Understand the components of an AI agent workflow.

## 3. System Components

| Component | Description |
|---|---|
| Chat Trigger | Initiates the workflow when a chat message is received. |
| AI Agent | Processes the user request and determines the appropriate action. |
| Ollama Chat Model | Generates responses using a locally hosted LLM. |
| Simple Memory | Stores conversational context. |
| Google Calendar | Enables the agent to retrieve calendar events and create events. |
| Gmail | Enables the agent to retrieve email information. |

## 4. System Workflow

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

## 5. Architecture

The system consists of a chat interface, AI orchestration layer, local LLM, memory component, and external service integrations.

The AI Agent acts as the central component connecting the language model with available tools.

## 6. Workflow Files

The exported n8n workflows are available in the `workflow/` directory.
```

---

## Step 4.2 – `02_Setup_and_Installation.md`

Create this file.

# Setup and Installation

## 1. Introduction

This document describes the environment and configuration used to develop and execute the n8n AI Agent.

## 2. Technologies

- Docker
- n8n
- Ollama
- Llama 3.2:3b
- Windows

## 3. Ollama Setup

Ollama was installed on the Windows environment to enable the local execution of Large Language Models.

The Llama 3.2:3b model was used for the AI agent.

The model was downloaded and executed through Ollama.

## 4. Docker and n8n Setup

n8n was executed using Docker.

The n8n interface was accessed through a web browser using the locally hosted n8n instance.

## 5. Connecting n8n with Ollama

The Ollama connection was configured within n8n using the Ollama API connection.

When n8n was running inside Docker and Ollama was running on the Windows host, the following host address was used:

`http://host.docker.internal:11434`

This allowed the n8n container to communicate with the Ollama service running on the host machine.

## 6. Workflow Import

To import an exported workflow:

1. Open n8n.
2. Create a new workflow or open the workflow editor.
3. Open the workflow menu.
4. Select the import option.
5. Import the exported JSON file.
6. Configure the required credentials.
7. Test the workflow.

## 7. Additional Configuration

Google Calendar and Gmail integrations require OAuth authentication.

Authentication credentials are not included in the exported workflow files.

These integrations must be configured separately when importing the workflows.
```

---

## Step 4.3 – `03_Integrations.md`

Create this file.

# AI Agent Integrations

## 1. Introduction

The n8n AI Agent was connected to Google Calendar and Gmail to explore the use of external applications as tools within an AI agent workflow.

These integrations allow the agent to retrieve information from connected services and perform selected operations.

## 2. Google Calendar Integration

Google Calendar was integrated into the AI agent using Google Calendar nodes.

### Implemented Operations

- Retrieve calendar events.
- Create calendar events.

### Event Creation

The agent was configured to collect relevant event details from the user's request and utilize the Google Calendar tool to create an event.

Event creation should be confirmed with the user before the action is performed.

### Event Retrieval

The agent can retrieve calendar information through the Google Calendar retrieval tool.

The retrieved information is used to answer relevant user questions.

## 3. Gmail Integration

Gmail was integrated into the AI agent using Gmail nodes.

### Implemented Operations

- Retrieve a list of emails.
- Retrieve the contents of a selected email.

### Email Retrieval Process

1. The agent identifies an email-related request.
2. The Gmail retrieval tool searches for relevant emails.
3. The returned information is used to identify the relevant email.
4. The agent retrieves the email contents when necessary.
5. The retrieved information is used to generate a response.

## 4. Authentication

Google Calendar and Gmail integrations require OAuth authentication.

Credentials are configured within n8n and are not included in the exported workflow files.

## 5. Limitations

- Access depends on the permissions granted during OAuth authentication.
- Google services may require additional configuration.
- The agent's ability to retrieve information depends on the available tools and their configurations.
- AI-generated responses should be verified against the actual retrieved information.
```

---

## Step 4.4 – `04_Testing_and_Evidence.md`

Create this file.

# Testing and Evidence

## 1. Introduction

Testing was conducted to verify the functionality of the n8n AI Agent, its memory component, and its connected tools.

Screenshots are included in the `screenshots/` directory as evidence of the implementation and testing process.

## 2. Basic Workflow Testing

The basic workflow was executed using the Manual Trigger.

The Edit Fields node was used to generate a message.

### Expected Output

`Hello from my first n8n workflow!`

## 3. AI Agent Testing

The AI Agent was tested using the n8n chat interface.

Testing focused on:

- General conversational interaction.
- Response generation through Ollama.
- Conversational context retention.
- Tool-based interactions.

## 4. Memory Testing

The memory component was tested to explore the agent's ability to retain conversational context.

## 5. Google Calendar Testing

The Google Calendar integration was tested to verify:

- Calendar event retrieval.
- Event creation.

## 6. Gmail Testing

The Gmail integration was tested to verify:

- Email retrieval.
- Retrieval of email contents.

## 7. Evidence

Screenshots demonstrating workflow execution, configuration, and integration testing are stored in the relevant screenshot folders.

## 8. Conclusion

The testing process provided an opportunity to explore the functionality of a locally hosted AI agent and its ability to interact with external applications through workflow automation.
```

---

## Step 4.5 – `05_Troubleshooting.md`

Create this file.

# Troubleshooting

## 1. Introduction

This document records common configuration and execution issues encountered during the development of the n8n AI Agent.

## 2. n8n and Ollama Connection

### Issue

The n8n container may be unable to communicate with Ollama when Ollama is running on the host machine.

### Solution

When n8n is running inside Docker on Windows, the following address can be used to access the Ollama service on the host:

`http://host.docker.internal:11434`

The Ollama service must be running before the connection is tested.

## 3. Ollama Model Availability

### Issue

The selected model may not be available locally.

### Solution

Verify that the model has been downloaded and is available through Ollama.

## 4. Google Authentication

### Issue

Google Calendar or Gmail operations may fail if authentication is missing or invalid.

### Solution

- Verify OAuth configuration.
- Reconnect the Google account if necessary.
- Check the permissions granted to the integration.

## 5. Workflow Import

### Issue

Imported workflows may not execute immediately.

### Solution

- Verify that the required nodes are installed or available.
- Configure the required credentials.
- Verify the Ollama connection.
- Check node configuration.
- Execute the workflow and inspect the execution logs.

## 6. AI Agent Responses

### Issue

The AI agent may not select the expected tool or may generate an incorrect response.

### Solution

- Review the AI Agent instructions.
- Verify tool configurations.
- Ensure the relevant tools are connected to the AI Agent.
- Check the information returned by the tools.
- Verify important information independently.

## 7. Conclusion

Troubleshooting helped identify the importance of correct service configuration, authentication, connectivity, and workflow design.
```

**Important:** These documents are a documentation template based on your implementation. Only retain statements describing testing or functionality that you actually completed.

---

# Step 5 – Organize your screenshots

You already have screenshot folders. Now we need to ensure the correct evidence is inside each one.

## 5.1 `01_complete_workflow`

Folder:

```text
screenshots/01_complete_workflow/
```

Add:

| Screenshot | What it should show |
|---|---|
| `01_AI_Agent_Workflow.png` | Entire AI Agent workflow. |
| `02_First_Workflow.png` | The simple Manual Trigger → Edit Fields workflow. |
| `03_AI_Agent_Execution.png` | Successful AI Agent execution, if available. |

## 5.2 `02_ollama`

Folder:

```text
screenshots/02_ollama/
```

Add:

| Screenshot | What it should show |
|---|---|
| `01_Ollama_Installation.png` | Ollama installation or terminal showing Ollama. |
| `02_Model_Availability.png` | Terminal showing installed models. |
| `03_Ollama_Connection.png` | Ollama connection configuration in n8n. |
| `04_Model_Configuration.png` | Llama model configuration in n8n. |

## 5.3 `03_memory`

Folder:

```text
screenshots/03_memory/
```

Add:

| Screenshot | What it should show |
|---|---|
| `01_Memory_Node.png` | Simple Memory configuration. |
| `02_Memory_Test.png` | Evidence of a conversation demonstrating context retention. |

## 5.4 `04_google_calendar`

Folder:

```text
screenshots/04_google_calendar/
```

Add:

| Screenshot | What it should show |
|---|---|
| `01_Calendar_Get_Events.png` | Calendar retrieval node configuration. |
| `02_Calendar_Create_Event.png` | Calendar creation node configuration. |
| `03_Calendar_Test.png` | Successful test execution. |

Avoid exposing private calendar events, personal information, or sensitive details.

## 5.5 `05_gmail`

Folder:

```text
screenshots/05_gmail/
```

Add:

| Screenshot | What it should show |
|---|---|
| `01_Gmail_Get_Many.png` | Gmail retrieval node configuration. |
| `02_Gmail_Get_Message.png` | Gmail Get Message node configuration. |
| `03_Gmail_Test.png` | Successful email retrieval execution. |

**Before uploading screenshots to GitHub, blur or crop:**

- Personal email addresses.
- Email contents that are private.
- Backup codes.
- OAuth tokens.
- Personal calendar information.

---

# Step 6 – Create a README for the screenshots folder

Inside:

```text
Method_02_n8n/screenshots/
```

Create:

```text
README.md
```

Paste this:

# Screenshots – n8n Implementation

This directory contains screenshots documenting the development, configuration, and testing of the n8n AI Agent.

## Screenshot Categories

| Directory | Description |
|---|---|
| `01_complete_workflow/` | Overall workflow designs and execution evidence. |
| `02_ollama/` | Ollama installation, model availability, and configuration. |
| `03_memory/` | Conversational memory configuration and testing. |
| `04_google_calendar/` | Google Calendar configuration and testing. |
| `05_gmail/` | Gmail configuration and testing. |

## Purpose

The screenshots provide visual evidence of the implementation and demonstrate the configuration and functionality of the different components.

Screenshots are provided for documentation and educational purposes.

Sensitive personal information has been excluded or obscured where applicable.
```

---

# Step 7 – Create a README for the documentation folder

Inside:

```text
Method_02_n8n/documentation/
```

Create:

```text
README.md
```

Paste:

# n8n Implementation Documentation

This directory contains the technical documentation for the n8n AI Agent implementation.

## Documents

| Document | Description |
|---|---|
| `01_System_Overview.md` | Describes the system architecture, components, and workflow. |
| `02_Setup_and_Installation.md` | Explains the installation and configuration process. |
| `03_Integrations.md` | Documents Google Calendar and Gmail integrations. |
| `04_Testing_and_Evidence.md` | Describes testing activities and evidence. |
| `05_Troubleshooting.md` | Records common problems and solutions. |

These documents support the reproducibility, understanding, and evaluation of the implementation.
```

---

# Step 8 – Create a README for Method 01 (Python)

At the moment, your `Method_01_Python` folder is empty or hasn't been completed.

**Don't worry. We'll prepare it as part of your comparison.**

For now, inside:

```text
Method_01_Python/
```

Create:

```text
README.md
```

Use this:

# Method 01 – AI Agent Implementation Using Python

## Overview

This directory contains the implementation of an AI agent using Python.

The objective of this implementation is to explore the development of an AI agent programmatically, understand its components, and compare it with the visual workflow-based implementation using n8n.

## Objectives

- Explore AI agent development using Python.
- Understand the programmatic approach to AI agent development.
- Investigate how an AI agent processes requests.
- Explore the integration of language models and tools.
- Compare Python-based development with visual workflow automation.

## Implementation Status

The Python-based implementation and its supporting documentation will be added to this directory.

## Planned Components

- Python-based agent logic.
- LLM integration.
- Tool integration.
- Agent execution.
- Documentation.
- Testing evidence.

## Technology Stack

The technology stack will be documented after the Python implementation is completed.

---
```

You don't need to implement Python right now. This README simply documents the planned second method.

---

# Step 9 – Create the README for `comparison`

Inside:

```text
comparison/
```

Create:

```text
README.md
```

Paste:

# AI Agent Implementation Comparison

This directory contains the comparative analysis of the two approaches explored in Lab 06.

## Approaches

### Method 01 – Python

A programmatic approach to AI agent development using Python.

### Method 02 – n8n

A visual workflow-based approach to AI agent development using n8n.

## Comparison Criteria

The comparison will consider:

- Development complexity.
- Flexibility.
- Customization.
- Workflow visualization.
- Integration capabilities.
- Debugging.
- Maintainability.
- Development time.
- Scalability.
- Learning experience.

## Comparison Document

The detailed comparison will be provided in:

`Method_Comparison.md`

---
```

Later, after completing Python, we'll create `Method_Comparison.md` based on your actual implementations, rather than making assumptions.

---

# Step 10 – Create `Final-Reflection.md`

Go to the root folder:

```text
Lab-06-AI-Agents/
```

Open:

```text
Final-Reflection.md
```

Paste:

# Lab 06 – Final Reflection

## Introduction

Lab 06 explored the development of AI agents through two different approaches: programmatic development using Python and visual workflow automation using n8n.

The lab provided an opportunity to explore AI agent architecture, Large Language Models, tool usage, conversational memory, and integration with external applications.

## Learning Outcomes

The lab aims to develop an understanding of:

- AI agent architecture.
- Large Language Models.
- Agent orchestration.
- Tool-based interactions.
- Conversational memory.
- Workflow automation.
- Application integrations.
- Different approaches to AI agent development.

## Experience with n8n

The n8n implementation provided an opportunity to explore AI agent development through a visual workflow interface.

The workflow components were connected to create an AI agent that utilized a locally hosted LLM and external application integrations.

The implementation also provided exposure to conversational memory and workflow execution.

## Challenges

Challenges encountered during implementation included configuring the local LLM connection, configuring integrations, and understanding how individual workflow nodes interact.

These challenges provided an opportunity to investigate connectivity, authentication, workflow configurations, and the execution process.

## Future Improvements

Potential improvements include:

- Expanding the number of tools.
- Improving agent instructions.
- Implementing additional memory capabilities.
- Improving error handling.
- Adding more comprehensive testing.
- Exploring alternative LLMs.
- Implementing the Python-based approach.
- Comparing the Python and n8n approaches.

## Conclusion

Lab 06 provided practical exposure to AI agent development and the use of workflow automation for integrating language models with external applications.

The experience helped develop a foundational understanding of the components involved in building AI agents and the different approaches available for their implementation.
```

**Edit the reflection later** to include your actual experiences, challenges and learning. This is a draft.

---

# Step 11 – Create the main README.md

This is the most important README because it will appear when someone opens your GitHub repository.

Inside:

```text
Lab-06-AI-Agents/
```

Open the main:

```text
README.md
```

Replace its content with the following.

# Lab 06 – AI Agents

## Overview

This repository documents the exploration and development of AI agents through two different implementation approaches: Python-based development and visual workflow automation using n8n.

The lab focuses on understanding AI agent architecture, Large Language Models, tool integration, conversational memory, and agent orchestration.

## Objectives

- Understand the fundamentals of AI agents.
- Explore Large Language Models.
- Implement an AI agent using Python.
- Implement an AI agent using n8n.
- Explore tool-based interactions.
- Investigate conversational memory.
- Integrate AI agents with external applications.
- Compare programmatic and visual development approaches.

## Implementation Approaches

### Method 01 – Python

A programmatic approach to AI agent development using Python.

[View Python Implementation](./Method_01_Python/README.md)

### Method 02 – n8n

A visual workflow-based AI agent implementation using n8n and Ollama.

The implementation includes:

- Ollama.
- Llama 3.2:3b.
- Simple Memory.
- Google Calendar.
- Gmail.

[View n8n Implementation](./Method_02_n8n/Readme.md)

## Repository Structure

```text
Lab-06-AI-Agents/
│
├── Method_01_Python/
│
├── Method_02_n8n/
│   ├── documentation/
│   ├── screenshots/
│   ├── workflow/
│   └── Readme.md
│
├── comparison/
│
├── Final-Reflection.md
│
└── README.md
```

## Documentation

Detailed documentation for the n8n implementation is available in:

`Method_02_n8n/documentation/`

## Screenshots

Visual evidence of the n8n implementation is available in:

`Method_02_n8n/screenshots/`

## Workflow Exports

The exported n8n workflows are available in:

`Method_02_n8n/workflow/`

## Comparative Analysis

The comparison of the two approaches will be documented in the `comparison/` directory.

## Final Reflection

The final learning reflection is available in:

`Final-Reflection.md`

## Technologies

| Technology | Purpose |
|---|---|
| Python | Programmatic AI agent development |
| n8n | Visual workflow automation |
| Ollama | Local LLM execution |
| Llama 3.2:3b | Language model |
| Docker | Containerized n8n environment |
| Google Calendar | Calendar integration |
| Gmail | Email integration |

## Disclaimer

This repository is intended for educational and experimental purposes.
```

---

# Step 12 – Your folder structure after completing today's steps

Your repository should now look like this:

```text
Lab-06-AI-Agents/
│
├── Method_01_Python/
│   └── README.md
│
├── Method_02_n8n/
│   │
│   ├── documentation/
│   │   ├── README.md
│   │   ├── 01_System_Overview.md
│   │   ├── 02_Setup_and_Installation.md
│   │   ├── 03_Integrations.md
│   │   ├── 04_Testing_and_Evidence.md
│   │   └── 05_Troubleshooting.md
│   │
│   ├── screenshots/
│   │   ├── README.md
│   │   ├── 01_complete_workflow/
│   │   ├── 02_ollama/
│   │   ├── 03_memory/
│   │   ├── 04_google_calendar/
│   │   └── 05_gmail/
│   │
│   ├── workflow/
│   │   ├── README.md
│   │   ├── 01_Ollama_AI_Agent.json
│   │   └── 02_First_n8n_Workflow.json
│   │
│   └── Readme.md
│
├── comparison/
│   └── README.md
│
├── Final-Reflection.md
│
└── README.md
```

---

## What I recommend you do right now

Don't try to finish everything in one sitting.

Follow this order:

| Order | Task | Status |
|---|---|---|
| 1 | Clean both workflow JSON files | ⬜ |
| 2 | Create `workflow/README.md` | ⬜ |
| 3 | Update `Method_02_n8n/Readme.md` | ⬜ |
| 4 | Create documentation files | ⬜ |
| 5 | Organize screenshots | ⬜ |
| 6 | Create screenshots README | ⬜ |
| 7 | Create documentation README | ⬜ |
| 8 | Create Python README | ⬜ |
| 9 | Create comparison README | ⬜ |
| 10 | Update Final-Reflection.md | ⬜ |
| 11 | Update main README | ⬜ |
| 12 | Review the entire repository | ⬜ |
| 13 | Upload to GitHub | ⬜ |

**I recommend starting with Tasks 1–3 and completing those first.** Then move to documentation.

Once your files are organized, I can guide you through **uploading the entire Lab 06 portfolio to GitHub step by step, including commits, repository setup, and checking that your files display properly.** 😊
