# UI Tool Access Control

## Overview

The web UI now provides a visual interface for managing tool access control for agents. Users can see which tools each agent has access to and control tool permissions through checkboxes when creating or editing agents.

## UI Features

### 1. Agent List Display

Each agent card in the dashboard now displays a badge showing their tool access level:

- **🟢 All tools** - Green badge when agent has access to all 3 tools
- **🟡 [N] tools** - Amber badge showing the number of tools (1-2 tools)
- **⚪ No tools** - Gray badge when agent has no tool access

Hovering over the badge (for partial access) shows the specific tools the agent has.

### 2. Create Agent Modal

When creating a new agent, the modal includes a "Tool Access" section with:

- **Checkbox for each tool**:
  - ✅ write_file - Write content to files
  - ✅ read_file - Read file contents
  - ✅ list_directory - List directory contents

- **Default behavior**: All tools are checked by default
- **Flexibility**: Uncheck specific tools to restrict access
- **Visual clarity**: Tools section has a light background for easy identification

### 3. Edit Agent Modal

When editing an existing agent, the modal:

- **Pre-populates** checkboxes based on agent's current tool access
- **Shows current state** - Checked boxes indicate available tools
- **Allows modification** - Check/uncheck to grant/revoke tool access
- **Updates immediately** - Changes are saved when you click "Update Agent"

## Using the UI

### Creating a Read-Only Agent

1. Click "Create Agent"
2. Fill in agent details (name, model, system prompt)
3. In the "Tool Access" section:
   - **Uncheck** "write_file"
   - **Keep checked**: "read_file" and "list_directory"
4. Click "Create Agent"

Result: Agent can read files and list directories but cannot write files.

### Creating a Write-Only Agent

1. Click "Create Agent"
2. Fill in agent details
3. In the "Tool Access" section:
   - **Keep checked**: "write_file"
   - **Uncheck**: "read_file" and "list_directory"
4. Click "Create Agent"

Result: Agent can write files but cannot read existing files or list directories.

### Creating a No-Tools Agent

1. Click "Create Agent"
2. Fill in agent details
3. In the "Tool Access" section:
   - **Uncheck all tools**
4. Click "Create Agent"

Result: Agent has no tool access (conversation-only agent).

### Modifying Agent Tool Access

1. Find the agent in the dashboard
2. Click the **Edit** button (pencil icon)
3. Scroll to "Tool Access" section
4. Check/uncheck tools as needed
5. Click "Update Agent"

The agent's tool access is immediately updated and reflected in the dashboard.

## Visual Indicators

### Tool Access Badges

The dashboard displays color-coded badges to quickly identify agent capabilities:

**Green Badge (All tools)**
```
✓ All tools
```
- Agent has full access to all tools
- Most permissive configuration

**Amber Badge (Partial access)**
```
⚙ 2 tools
```
- Agent has access to some but not all tools
- Hover to see which specific tools
- Useful for specialized agents

**Gray Badge (No tools)**
```
✗ No tools
```
- Agent has no tool access
- Conversation-only agent
- Safest configuration

### Badge Layout

Each agent card shows:
```
┌─────────────────────────────────────┐
│ Agent Name                          │
│ ┌────────┐ ┌────────┐ ┌────────┐  │
│ │ Model  │ │Messages│ │ Temp   │  │
│ └────────┘ └────────┘ └────────┘  │
│ ┌────────┐                         │
│ │ Tools  │ ← Tool access badge     │
│ └────────┘                         │
└─────────────────────────────────────┘
```

## Use Cases

### Security Analyst Agent
**Configuration**: Read-only access
- ✅ read_file
- ✅ list_directory
- ❌ write_file

**Use case**: Review code for security issues without modification risk

### Documentation Agent
**Configuration**: Write-only access
- ✅ write_file
- ❌ read_file
- ❌ list_directory

**Use case**: Generate documentation from user instructions

### Development Agent
**Configuration**: Full access
- ✅ write_file
- ✅ read_file
- ✅ list_directory

**Use case**: Full-featured coding assistant

### Advisor Agent
**Configuration**: No tools
- ❌ write_file
- ❌ read_file
- ❌ list_directory

**Use case**: Provide advice and guidance without file system access

## Technical Implementation

### Form Data Collection

When creating an agent:
```javascript
// Collect checked tool values
const selectedTools = [];
const toolCheckboxes = form.querySelectorAll('input[name="tools"]:checked');
toolCheckboxes.forEach(checkbox => {
    selectedTools.push(checkbox.value);
});

// Include in agent data
agentData.tools = selectedTools;
```

### Tool Display

For each agent:
```javascript
const allowedTools = agent.allowed_tools || [];

if (allowedTools.length === 0) {
    // Show "No tools" badge
} else if (allowedTools.length === 3) {
    // Show "All tools" badge
} else {
    // Show "[N] tools" badge with hover tooltip
}
```

### Edit Form Population

When editing:
```javascript
// Pre-populate checkboxes based on current tools
const allowedTools = agent.allowed_tools || [];
document.getElementById('edit_tool_write_file').checked = 
    allowedTools.includes('write_file');
document.getElementById('edit_tool_read_file').checked = 
    allowedTools.includes('read_file');
document.getElementById('edit_tool_list_directory').checked = 
    allowedTools.includes('list_directory');
```

## API Integration

The UI seamlessly integrates with the tool access control API:

### Create Agent
```javascript
POST /api/agents
{
    "name": "agent_name",
    "model": "llama3.2",
    "tools": ["read_file", "list_directory"]  // Optional
}
```

### Update Agent
```javascript
PUT /api/agents/agent_name
{
    "tools": ["write_file", "read_file"]  // Update tool access
}
```

### Get Agent Info
```javascript
GET /api/agents/agent_name
Response:
{
    "agent": {
        "name": "agent_name",
        "model": "llama3.2",
        "allowed_tools": ["read_file", "list_directory"]
    }
}
```

## Responsive Design

The tool access controls are fully responsive:

- **Desktop**: Full layout with all checkboxes visible
- **Tablet**: Stacked layout, checkboxes remain accessible
- **Mobile**: Vertical layout, touch-friendly checkboxes

## Accessibility

- **Keyboard navigation**: Tab through checkboxes
- **Screen readers**: Labels clearly describe each tool
- **Visual indicators**: Checkboxes have clear on/off states
- **Color contrast**: Badges meet WCAG AA standards

## Benefits

1. **Visual Management**: See tool access at a glance
2. **Easy Control**: Point-and-click tool management
3. **Clear Feedback**: Color-coded badges show access levels
4. **Intuitive UI**: Checkboxes make permissions obvious
5. **No Code Required**: Manage tools without API calls
6. **Real-time Updates**: Changes reflected immediately

## Future Enhancements

Potential UI improvements:

- Tool usage statistics per agent
- Visual indicator showing when agent attempts restricted tool
- Preset configurations (read-only, write-only templates)
- Bulk tool management for multiple agents
- Tool access history/audit log
- Recommended tool configurations based on system prompt

## Screenshots

### Create Agent with Tool Selection
```
┌─────────────────────────────────────┐
│ Create New Agent                    │
├─────────────────────────────────────┤
│ Agent Name: [code_reviewer         ]│
│ Model: [llama3.2                   ]│
│ System Prompt: [You review code... ]│
│                                     │
│ Tool Access:                        │
│ ┌─────────────────────────────────┐│
│ │ □ write_file - Write files      ││
│ │ ☑ read_file - Read files        ││
│ │ ☑ list_directory - List dirs    ││
│ └─────────────────────────────────┘│
│                                     │
│ [Create Agent]                      │
└─────────────────────────────────────┘
```

### Agent List with Tool Badges
```
┌─────────────────────────────────────┐
│ Code Reviewer                       │
│ [llama3.2] [15 messages] [0.7 temp] │
│ [🟡 2 tools]                        │
│ [Chat] [Edit] [Delete]              │
├─────────────────────────────────────┤
│ Developer                           │
│ [llama3.2] [42 messages] [0.8 temp] │
│ [🟢 All tools]                      │
│ [Chat] [Edit] [Delete]              │
└─────────────────────────────────────┘
```

## Summary

The UI tool access control feature provides a user-friendly interface for managing agent permissions. With visual indicators, intuitive checkboxes, and clear feedback, users can easily control which tools each agent can access without needing to use the API directly.

This feature makes the multi-agent system more accessible to non-technical users while providing the same powerful tool access control capabilities available through the API.

