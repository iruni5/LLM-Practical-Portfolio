---

# Troubleshooting

## 1. Introduction
---

This document records common configuration and execution issues encountered during the development of the n8n AI Agent.

## 2. n8n and Ollama Connection
---

### Issue

The n8n container may be unable to communicate with Ollama when Ollama is running on the host machine.

### Solution

When n8n is running inside Docker on Windows, the following address can be used to access the Ollama service on the host:

http://host.docker.internal:11434

The Ollama service must be running before the connection is tested.

## 3. Ollama Model Availability
---

### Issue

The selected model may not be available locally.

### Solution

Verify that the model has been downloaded and is available through Ollama.

## 4. Google Authentication
---

### Issue

Google Calendar or Gmail operations may fail if authentication is missing or invalid.

### Solution

- Verify OAuth configuration.

- Reconnect the Google account if necessary.

- Check the permissions granted to the integration.

## 5. Workflow Import
---

### Issue

Imported workflows may not execute immediately.

### Solution

- Verify that the required nodes are installed or available.

- Configure the required credentials.

- Verify the Ollama connection.

- Check node configuration.

- Execute the workflow and inspect the execution logs.

## 6. AI Agent Responses
---

### Issue

The AI agent may not select the expected tool or may generate an incorrect response.

### Solution

- Review the AI Agent instructions.

- Verify tool configurations.

- Ensure the relevant tools are connected to the AI Agent.

- Check the information returned by the tools.

- Verify important information independently.

## 7. Conclusion
---

Troubleshooting helped identify the importance of correct service configuration, authentication, connectivity, and workflow design.


