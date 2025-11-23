# Chat Troubleshooting Guide

## Issues Fixed

I've fixed several issues that were preventing agents from responding:

### 1. **Frontend Error Handling** ✅
- **Problem**: Frontend didn't check for HTTP errors before parsing JSON
- **Fix**: Added proper error checking and user-friendly error messages
- **File**: `static/js/chat.js`

### 2. **Backend Error Handling** ✅
- **Problem**: Errors were being swallowed silently
- **Fix**: Added comprehensive error handling with logging
- **File**: `app.py`, `agent_core.py`

### 3. **User Feedback** ✅
- **Problem**: No indication that a message was being processed
- **Fix**: Added loading state ("Thinking...") and disabled button during processing
- **File**: `static/js/chat.js`

### 4. **Better Error Messages** ✅
- **Problem**: Generic error messages didn't help diagnose issues
- **Fix**: Added specific error messages for common problems:
  - Ollama not running
  - Model not found
  - Connection errors
- **File**: `agent_core.py`

### 5. **Health Check Endpoint** ✅
- **Problem**: No way to check system status
- **Fix**: Added `/api/health` endpoint for diagnostics
- **File**: `app.py`

## How to Diagnose Issues

### Step 1: Run the Diagnostic Script

```bash
python diagnose_chat.py
```

This will check:
- ✅ Ollama package installation
- ✅ Ollama service status
- ✅ Available models
- ✅ Agent system files
- ✅ Database status
- ✅ Agent creation

### Step 2: Check the Health Endpoint

Open your browser or use curl:
```bash
curl http://localhost:5000/api/health
```

This will show:
- System status
- Number of agents
- Ollama availability
- Available models
- Agent list

### Step 3: Check Browser Console

1. Open your browser's Developer Tools (F12)
2. Go to the Console tab
3. Try sending a chat message
4. Look for any error messages

### Step 4: Check Server Logs

When running the Flask app, check the terminal/console for error messages. The improved error handling will now log detailed information.

## Common Issues and Solutions

### Issue: "Cannot connect to Ollama"

**Symptoms:**
- Error message: "Cannot connect to Ollama. Is Ollama running?"

**Solutions:**
1. Check if Ollama is running:
   ```bash
   # On Windows/Mac, Ollama should start automatically
   # On Linux, check service:
   systemctl status ollama
   # Or start it:
   ollama serve
   ```

2. Verify Ollama is accessible:
   ```bash
   curl http://localhost:11434/api/tags
   ```

3. Check if port 11434 is available:
   ```bash
   # Windows
   netstat -an | findstr 11434
   
   # Linux/Mac
   lsof -i :11434
   ```

### Issue: "Model not found"

**Symptoms:**
- Error message: "Model 'llama3.2' not found"

**Solutions:**
1. List available models:
   ```bash
   ollama list
   ```

2. Download the model:
   ```bash
   ollama pull llama3.2
   ```

3. Update agent configuration to use an available model

### Issue: "Empty response from Ollama"

**Symptoms:**
- Chat appears to work but returns empty responses

**Solutions:**
1. Check if the model is fully downloaded
2. Try a different model
3. Check Ollama logs for errors

### Issue: "Agent not found"

**Symptoms:**
- Error message: "Agent not found"

**Solutions:**
1. Check available agents:
   ```bash
   curl http://localhost:5000/api/agents
   ```

2. Create an agent if none exist (the app should create a default one)

3. Make sure you're using the correct agent name in the URL

### Issue: No response at all

**Symptoms:**
- Clicking send does nothing
- No error messages

**Solutions:**
1. Check browser console for JavaScript errors
2. Verify the Flask app is running
3. Check network tab in browser DevTools for failed requests
4. Make sure you're on the correct URL: `http://localhost:5000/chat/<agent_name>`

## Testing the Fix

### Test 1: Basic Chat
1. Start the Flask app: `python app.py`
2. Open browser: `http://localhost:5000`
3. Create or select an agent
4. Go to chat interface
5. Send a message
6. You should see:
   - "Thinking..." message appears
   - Agent response appears
   - No errors in console

### Test 2: Error Handling
1. Stop Ollama service
2. Try to send a chat message
3. You should see a clear error message explaining the issue

### Test 3: Health Check
1. Visit: `http://localhost:5000/api/health`
2. Check the JSON response for system status

## What Changed

### Files Modified:

1. **`static/js/chat.js`**
   - Added HTTP error checking
   - Added loading state
   - Improved error messages
   - Better user feedback

2. **`app.py`**
   - Added comprehensive error handling
   - Added logging
   - Added health check endpoint
   - Better error responses

3. **`agent_core.py`**
   - Improved Ollama error handling
   - Better error messages
   - Response validation

### New Files:

1. **`diagnose_chat.py`**
   - Diagnostic tool to check system status

2. **`CHAT_TROUBLESHOOTING.md`**
   - This guide

## Next Steps

If agents still don't respond after these fixes:

1. Run `python diagnose_chat.py` and share the output
2. Check browser console for errors
3. Check Flask app logs
4. Verify Ollama is running and has models
5. Test the health endpoint: `curl http://localhost:5000/api/health`

## Additional Debugging

### Enable Verbose Logging

In `app.py`, the logging is already configured. To see more details, you can change:
```python
logging.basicConfig(level=logging.DEBUG)  # Change from INFO to DEBUG
```

### Test Ollama Directly

```python
import ollama
response = ollama.chat(model='llama3.2', messages=[
    {'role': 'user', 'content': 'Hello'}
])
print(response)
```

### Test Agent Directly

```python
from agent_core import EnhancedAgent
from knowledge_base import KnowledgeBase

kb = KnowledgeBase()
agent = EnhancedAgent(
    name='Test',
    model='llama3.2',
    system_prompt='You are helpful',
    knowledge_base=kb
)
response = agent.chat("Hello")
print(response)
```

