# Tool Access Control for Agents

## Overview

The agent system now supports granular tool access control, allowing you to specify which tools each agent can use. This enables you to create specialized agents with different capabilities - from full-access agents to read-only agents.

## Available Tools

The system currently supports the following tools:

1. **write_file**: Write content to files in the `agent_code` directory
2. **read_file**: Read file contents from the filesystem
3. **list_directory**: List contents of directories

## How It Works

### Default Behavior

If no tools are specified when creating an agent, the agent has access to **all available tools**.

### Restricting Tools

You can specify a subset of tools when creating or updating an agent. The agent will only be able to use the specified tools.

## Usage Examples

### 1. Creating an Agent via API

#### Full Access Agent (default)

```bash
curl -X POST http://localhost:5000/api/agents \
  -H "Content-Type: application/json" \
  -d '{
    "name": "full_access_agent",
    "model": "llama3.2",
    "system_prompt": "You are a helpful coding assistant."
  }'
```

#### Read-Only Agent

```bash
curl -X POST http://localhost:5000/api/agents \
  -H "Content-Type: application/json" \
  -d '{
    "name": "reader_agent",
    "model": "llama3.2",
    "system_prompt": "You are a code reviewer that can read and analyze code.",
    "tools": ["read_file", "list_directory"]
  }'
```

#### Write-Only Agent

```bash
curl -X POST http://localhost:5000/api/agents \
  -H "Content-Type: application/json" \
  -d '{
    "name": "writer_agent",
    "model": "llama3.2",
    "system_prompt": "You are a documentation generator.",
    "tools": ["write_file"]
  }'
```

### 2. Creating an Agent via Python API

```python
from src.agent_manager import AgentManager
from src.knowledge_base import KnowledgeBase
from src.message_bus import MessageBus

# Initialize components
kb = KnowledgeBase()
mb = MessageBus()
manager = AgentManager(kb, mb)

# Create a full-access agent
manager.create_agent(
    name="dev_agent",
    model="llama3.2",
    system_prompt="You are a software developer.",
    tools=None  # None means all tools
)

# Create a read-only agent
manager.create_agent(
    name="analyst_agent",
    model="llama3.2",
    system_prompt="You analyze code but don't modify it.",
    tools=["read_file", "list_directory"]
)

# Create an agent with only write access
manager.create_agent(
    name="generator_agent",
    model="llama3.2",
    system_prompt="You generate new code files.",
    tools=["write_file"]
)
```

### 3. Updating Agent Tools

You can update an agent's tool access at any time:

```bash
curl -X PUT http://localhost:5000/api/agents/reader_agent \
  -H "Content-Type: application/json" \
  -d '{
    "tools": ["read_file", "write_file", "list_directory"]
  }'
```

### 4. Getting Available Tools

To see all available tools:

```bash
curl http://localhost:5000/api/tools
```

Response:
```json
{
  "tools": [
    {
      "name": "write_file",
      "description": "Write content to a file"
    },
    {
      "name": "read_file",
      "description": "Read a file's contents"
    },
    {
      "name": "list_directory",
      "description": "List directory contents"
    }
  ]
}
```

## Use Cases

### 1. Security & Safety

**Read-Only Agent for Code Review:**
```python
manager.create_agent(
    name="security_auditor",
    model="llama3.2",
    system_prompt="You are a security auditor. Review code for vulnerabilities.",
    tools=["read_file", "list_directory"]
)
```

This agent can analyze code but cannot modify anything.

### 2. Specialized Roles

**Documentation Generator:**
```python
manager.create_agent(
    name="doc_writer",
    model="llama3.2",
    system_prompt="You write documentation files based on user instructions.",
    tools=["write_file"]
)
```

This agent can only create/write files, not read existing ones.

### 3. Progressive Access

Start with limited access and expand as needed:

```python
# Start with read-only
manager.create_agent(
    name="trainee_agent",
    model="llama3.2",
    system_prompt="You are learning the codebase.",
    tools=["read_file", "list_directory"]
)

# Later, grant write access after the agent proves capable
agent = manager.get_agent("trainee_agent")
agent.allowed_tools.append("write_file")
knowledge_base.save_agent(
    name=agent.name,
    model=agent.model,
    system_prompt=agent.system_prompt,
    settings=agent.settings,
    tools=agent.allowed_tools
)
```

## Tool Execution Behavior

### When an Agent Attempts to Use a Restricted Tool

If an agent tries to use a tool it doesn't have access to, the system will:

1. **Reject the tool call** with an error message
2. **Log the attempt** in the tool execution results
3. **Inform the agent** of available tools

Example response:
```
Error: Access denied: Tool "write_file" is not available for this agent. 
Available tools: read_file, list_directory
```

### Agent Awareness

Agents are informed of their available tools in their prompts, so they generally won't attempt to use tools they don't have access to. The tools info is dynamically generated based on the agent's allowed tools.

## Database Schema

The `agents` table includes a `tools` column:

```sql
CREATE TABLE agents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    model TEXT NOT NULL,
    system_prompt TEXT,
    settings TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    tools TEXT  -- JSON array of allowed tool names
);
```

- `NULL`: All tools available
- `["read_file", "list_directory"]`: Only read and list tools
- `[]`: No tools available

## Migration

If you have an existing database, run the migration script to add the `tools` column:

```bash
python3 scripts/db/add_tools_column.py
```

This will:
1. Add the `tools` column to the `agents` table
2. Set all existing agents to have all tools available (default behavior)

## API Reference

### Get Available Tools
- **Endpoint**: `GET /api/tools`
- **Response**: List of available tools with descriptions

### Create Agent with Tools
- **Endpoint**: `POST /api/agents`
- **Body**:
  ```json
  {
    "name": "agent_name",
    "model": "llama3.2",
    "system_prompt": "...",
    "tools": ["write_file", "read_file"]  // optional
  }
  ```

### Update Agent Tools
- **Endpoint**: `PUT /api/agents/<agent_name>`
- **Body**:
  ```json
  {
    "tools": ["read_file", "list_directory"]
  }
  ```

### Get Agent Info (includes tools)
- **Endpoint**: `GET /api/agents/<agent_name>`
- **Response**:
  ```json
  {
    "agent": {
      "name": "agent_name",
      "model": "llama3.2",
      "allowed_tools": ["read_file", "list_directory"],
      ...
    }
  }
  ```

## Configuration File Example

In `config.yaml`:

```yaml
# Tools configuration (optional)
# Specify which tools this agent can use. If not specified, all tools are available.
# Available tools: write_file, read_file, list_directory

# Full access (default if not specified):
# tools:
#   - write_file
#   - read_file
#   - list_directory

# Read-only agent:
# tools:
#   - read_file
#   - list_directory

# Write-only agent:
# tools:
#   - write_file
```

## Best Practices

1. **Principle of Least Privilege**: Only grant tools that an agent actually needs
2. **Document Tool Requirements**: Clearly document why an agent needs specific tools
3. **Start Restrictive**: Begin with minimal tools and expand as needed
4. **Audit Tool Usage**: Monitor which tools agents are using via the knowledge base
5. **Test Tool Restrictions**: Verify that agents behave correctly with limited tools

## Future Extensions

Potential future enhancements:

- Fine-grained file access control (specific directories)
- Custom tools per agent
- Tool usage quotas and rate limiting
- Temporary tool grants
- Tool usage analytics and recommendations

## Troubleshooting

### Agent Not Using Expected Tools

1. Check agent's `allowed_tools` property:
```python
agent = manager.get_agent("agent_name")
print(agent.allowed_tools)
```

2. Verify database record:
```sql
SELECT name, tools FROM agents WHERE name = 'agent_name';
```

### Tools Not Persisting After Update

Make sure to save the agent after modifying tools:
```python
knowledge_base.save_agent(
    name=agent.name,
    model=agent.model,
    system_prompt=agent.system_prompt,
    settings=agent.settings,
    tools=agent.allowed_tools
)
```

### Invalid Tool Names

The API will reject invalid tool names. Only use:
- `write_file`
- `read_file`
- `list_directory`

## Summary

Tool access control provides flexible security and specialization for agents. By controlling which tools an agent can access, you can create:

- **Safe agents** that can only read, not modify
- **Specialized agents** with focused capabilities  
- **Sandbox agents** for testing without risk
- **Progressive trust** models that grant access over time

This feature enhances the security, maintainability, and organization of your multi-agent system.

