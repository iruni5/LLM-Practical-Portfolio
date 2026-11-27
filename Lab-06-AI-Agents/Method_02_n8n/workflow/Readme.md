Method 02 – AI Agent Implementation Using n8n

Overview

This implementation explores the development of an AI-powered agent using n8n, a visual workflow automation platform.

The AI agent was developed using Ollama as the local Large Language Model (LLM) provider and integrated with Google Calendar and Gmail to explore how AI agents can interact with external services and perform tasks using tools.

A separate simple workflow was also developed to understand the fundamental workflow creation and execution process in n8n.

Objectives

Understand visual workflow automation using n8n.

Develop an AI agent using a locally hosted LLM.

Connect an AI agent with external applications.

Implement conversational memory.

Explore tool-based interactions with Google Calendar and Gmail.

Export workflows for documentation and reuse.

Technology Stack

Technology

Purpose

n8n

Workflow automation and AI agent orchestration

Ollama

Local LLM execution

Llama 3.2:3b

Language model used by the agent

Simple Memory

Maintaining conversational context

Google Calendar API

Calendar event retrieval and creation

Gmail API

Email retrieval

Docker

Running n8n in a containerized environment

Project Structure

Method_02_n8n/
│
├── documentation/
│
├── screenshots/
│
├── workflow/
│
└── Readme.md

Implementations

1. Basic n8n Workflow

A simple workflow was created using a Manual Trigger and Edit Fields node.

This implementation demonstrates:

Manual workflow execution.

Node-based workflow design.

Data assignment.

Workflow execution and output inspection.

2. Ollama AI Agent

An AI agent was created using n8n and Ollama.

The workflow incorporates:

Chat Trigger.

AI Agent.

Ollama Chat Model.

Simple Memory.

Google Calendar tools.

Gmail tools.

The agent was designed to interact with connected services through tools while maintaining conversational context.

Documentation

Detailed implementation information, configuration instructions, testing evidence, and troubleshooting information are available in the documentation/ directory.

Workflow Files

The exported workflows are available in the workflow/ directory.

Screenshots

Screenshots demonstrating the setup, workflow configuration, integrations, and testing are available in the screenshots/ directory.

Notes

Ollama must be installed and configured separately.

The required Ollama model must be available locally.

Google Calendar and Gmail require appropriate OAuth credentials.

Imported workflows may require reconfiguration of credentials.

The workflow exports do not contain actual authentication secrets.
