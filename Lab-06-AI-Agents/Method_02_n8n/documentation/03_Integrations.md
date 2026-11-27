---
# AI Agent Integrations

## 1. Introduction
---

The n8n AI Agent was connected to Google Calendar and Gmail to explore the use of external applications as tools within an AI agent workflow.

These integrations allow the agent to retrieve information from connected services and perform selected operations.

---

## 2. Google Calendar Integration

---

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

---

## 3. Gmail Integration
---

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

---

## 4. Authentication
---

Google Calendar and Gmail integrations require OAuth authentication.

Credentials are configured within n8n and are not included in the exported workflow files.

---

## 5. Limitations
---

- Access depends on the permissions granted during OAuth authentication.

- Google services may require additional configuration.

- The agent's ability to retrieve information depends on the available tools and their configurations.

- AI-generated responses should be verified against the actual retrieved information.
