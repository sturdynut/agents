# Agent File Writing Guide

## What Was Fixed

The agent file writing system has been enhanced to ensure files are always written to the `agent_code` folder correctly.

### Changes Made:

1. **Enhanced `write_file` method in `agent_core.py`**:
   - Automatically resolves relative paths to the `agent_code` folder
   - Handles both simple filenames and subdirectory paths
   - Uses absolute paths internally to avoid any path resolution issues

2. **Updated tool instructions**:
   - Simplified the syntax for agents
   - Made it clear that agents just need to provide the filename
   - System automatically saves to `agent_code/`

3. **Updated Coder agent prompt in `seed_db.py`**:
   - Clearer instructions on how to use the write_file tool
   - Simpler examples that are easier to follow

## How to Test

### Via Web Interface

1. Open http://localhost:5001 in your browser
2. Click on the "Coder" agent to open chat
3. Ask the agent to write a file, for example:
   - "Write a Python script that calculates fibonacci numbers"
   - "Create a hello world script"
   - "Write a utility function for string manipulation"

### Via API

```bash
curl -X POST http://localhost:5001/api/agents/Coder/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Write a Python script that prints hello world"}'
```

### Expected Behavior

When you ask the Coder agent to write a file, it should:
1. Use the tool call format: `<TOOL_CALL tool="write_file">{"path": "filename.py", "content": "..."}</TOOL_CALL>`
2. The file will be saved to `agent_code/filename.py`
3. You'll see a success message in the response
4. You can verify by checking `ls agent_code/`

## File Writing Examples

### Simple file:
```
Agent command: <TOOL_CALL tool="write_file">{"path": "hello.py", "content": "print('Hello')"}</TOOL_CALL>
Result: File saved to agent_code/hello.py
```

### File in subdirectory:
```
Agent command: <TOOL_CALL tool="write_file">{"path": "utils/helper.py", "content": "def help(): pass"}</TOOL_CALL>
Result: File saved to agent_code/utils/helper.py
```

## Troubleshooting

If files are not being created:

1. **Check permissions**: Ensure `agent_code/` directory is writable
   ```bash
   ls -la agent_code/
   ```

2. **Check agent response**: Look for tool execution results in the agent's response
   - Success: `[Executed: write_file - Success]`
   - Failure: `[Executed: write_file - Error: ...]`

3. **Check server logs**: The Flask app logs tool execution
   ```bash
   # Look in terminal where app.py is running
   ```

4. **Verify agent prompt**: Make sure the Coder agent has the updated prompt
   ```bash
   python3 seed_db.py --overwrite --yes
   ```

## Testing the System

A test script is available to verify the file writing functionality:

```python
from agent_core import EnhancedAgent
from knowledge_base import KnowledgeBase

kb = KnowledgeBase()
agent = EnhancedAgent("TestAgent", "llama3.2", "", {}, kb)

# Write a test file
result = agent.write_file("test.py", "print('test')")
print(result)  # Should show success: True
```

## Notes

- The embedding service error (`nomic-embed-text not found`) is non-critical and can be ignored
- Files are always saved with absolute paths to avoid any working directory issues
- The system automatically creates subdirectories as needed

