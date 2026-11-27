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
