# Multi-Agent System

A modern web-based multi-agent system built with Flask and Ollama. Create, manage, and interact with multiple AI agents that can communicate with each other, execute tasks, and maintain persistent memory through a SQLite knowledge base.

## Features

- **🤖 Multiple Agents**: Create and manage multiple AI agents with unique personalities and capabilities
- **💬 Web Interface**: Beautiful, modern web UI built with Tailwind CSS and shadcn-inspired components
- **📡 Agent Communication**: Agents can send messages to each other and have multi-round conversations
- **💾 Persistent Storage**: SQLite database stores agents and all message history
- **📚 Knowledge Base**: Shared knowledge base tracks all interactions, tasks, and file operations
- **🔧 File Operations**: Agents can read, write, and list files/directories
- **🎯 Task Execution**: Agents can execute complex tasks with context awareness
- **🌐 Real-time Updates**: WebSocket support for real-time communication

## Prerequisites

1. **Python 3.7+**: Ensure Python is installed on your system
2. **Ollama**: Install Ollama from [https://ollama.ai](https://ollama.ai)
3. **Local Model**: Download a model using Ollama (e.g., `ollama pull llama3.2`)

## Installation

### 1. Clone the Repository

```bash
git clone <repository-url>
cd agent
```

### 2. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 3. Install Ollama and Download a Model

```bash
# Install Ollama (if not already installed)
# Visit https://ollama.ai for installation instructions

# Download a model (e.g., llama3.2)
ollama pull llama3.2

# Verify the model is available
ollama list
```

### 4. Initialize the Database

```bash
# Create the database and tables
python init_db.py

# (Optional) Seed the database with sample agents
python seed_db.py
```

## Project Setup

### Database Initialization

The system uses SQLite to store agents and message history. Initialize the database before first use:

```bash
# Create database and tables
python init_db.py

# Options:
#   --db <path>    Custom database path (default: data/agent.db)
#   --reset        Drop existing tables and recreate (WARNING: deletes all data!)
```

### Seeding Sample Agents

Add sample agents to get started quickly:

```bash
# Add sample agents (skips existing ones)
python seed_db.py

# Options:
#   --db <path>      Custom database path
#   --overwrite      Replace all existing agents
```

The seed script creates 3 sample agents:
- **Designer**: Creative UI/UX designer with expertise in creating beautiful, functional, and user-friendly interfaces
- **Coder**: Expert software developer who writes clean, efficient code (builds files in the `agent_code/` folder)
- **Tester**: Quality assurance engineer with expertise in testing methodologies and bug identification

### Clearing the Database

Clear agents and/or interactions from the database:

```bash
# Clear all agents (default)
python clear_db.py

# Clear both agents and interactions
python clear_db.py --all

# Clear only interactions
python clear_db.py --interactions

# Skip confirmation prompt
python clear_db.py --yes

# Options:
#   --db <path>      Custom database path
#   --agents         Clear agents (default)
#   --interactions   Clear interactions/messages
#   --all            Clear both agents and interactions
#   --yes            Skip confirmation prompt
```

### Running the Application

Start the Flask web server:

```bash
python app.py
```

The application will be available at:
- **Web Interface**: http://localhost:5000
- **API**: http://localhost:5000/api

## System Architecture

### Core Components

```
┌─────────────────────────────────────────────────────────┐
│                    Web Interface (Flask)                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌─────────┐│
│  │ Dashboard│  │   Chat   │  │  Agent   │  │Knowledge ││
│  │          │  │          │  │  Comm    │  │  Base    ││
│  └──────────┘  └──────────┘  └──────────┘  └─────────┘│
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│                  Agent Manager                            │
│  ┌──────────────────────────────────────────────────┐   │
│  │  Manages agent lifecycle (create, delete, list)  │   │
│  └──────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
                          │
        ┌─────────────────┴─────────────────┐
        ▼                                   ▼
┌──────────────┐                  ┌──────────────┐
│   Agents     │                  │ Message Bus  │
│              │                  │              │
│ - Enhanced   │◄─────────────────┤ - Routes     │
│   Agent      │                  │   messages   │
│ - Ollama     │                  │ - Registers  │
│   Client     │                  │   agents     │
└──────────────┘                  └──────────────┘
        │                                   │
        └─────────────────┬─────────────────┘
                          ▼
                ┌─────────────────┐
                │ Knowledge Base  │
                │                 │
                │ - SQLite DB     │
                │ - Interactions  │
                │ - Agent Config  │
                └─────────────────┘
```

### Component Details

#### 1. **Agent Manager** (`agent_manager.py`)
- Manages agent lifecycle (create, delete, list)
- Loads agents from SQLite on startup
- Persists agents to database
- Coordinates with Knowledge Base and Message Bus

#### 2. **Enhanced Agent** (`agent_core.py`)
- Core agent implementation with Ollama integration
- Handles chat, task execution, and file operations
- Maintains conversation history
- Integrates with knowledge base for context

#### 3. **Message Bus** (`message_bus.py`)
- Routes messages between agents
- Registers agents for communication
- Stores messages in knowledge base

#### 4. **Knowledge Base** (`knowledge_base.py`)
- SQLite database management
- Stores agent configurations
- Tracks all interactions (chats, tasks, file ops)
- Provides search and filtering capabilities

#### 5. **Web Application** (`app.py`)
- Flask REST API endpoints
- WebSocket support for real-time updates
- Serves web interface templates

### Database Schema

#### Agents Table
```sql
CREATE TABLE agents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    model TEXT NOT NULL,
    system_prompt TEXT,
    settings TEXT,  -- JSON
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
```

#### Knowledge Base Table
```sql
CREATE TABLE knowledge_base (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    agent_name TEXT NOT NULL,
    interaction_type TEXT NOT NULL,  -- user_chat, agent_chat, task_execution, etc.
    content TEXT NOT NULL,
    metadata TEXT,  -- JSON
    related_agent TEXT
);
```

## Usage Guide

### Web Interface

#### Dashboard (`/`)
- View all agents
- Create new agents
- Quick access to other features
- View statistics (agent count, message count)

#### Chat (`/chat/<agent_name>`)
- Chat directly with an agent
- Execute tasks
- Perform file operations
- View conversation history

#### Agent Communication (`/agent-comm`)
- Send single messages between agents
- Start multi-round conversations
- View message history
- Monitor conversation progress

#### Knowledge Base (`/knowledge`)
- Browse all interactions
- Filter by agent or interaction type
- Search interactions
- View metadata

### Creating an Agent

1. Click "Create Agent" on the dashboard
2. Fill in the form:
   - **Name**: Unique agent identifier
   - **Model**: Ollama model name (e.g., `llama3.2`)
   - **System Prompt**: Defines agent personality/behavior
   - **Temperature**: 0.0-2.0 (creativity level)
   - **Max Tokens**: Maximum response length
3. Click "Create Agent"

The agent is saved to the database and available immediately.

### Agent-to-Agent Communication

#### Single Message
1. Go to Agent Communication page
2. Select sender and receiver agents
3. Type your message
4. Click "Send Message"

#### Multi-Round Conversation
1. Select two agents
2. Enter initial message
3. Set number of rounds
4. Click "Start Conversation"

Agents will alternate responding to each other for the specified number of rounds.

## API Endpoints

### Agents

- `GET /api/agents` - List all agents
- `POST /api/agents` - Create a new agent
- `DELETE /api/agents/<name>` - Delete an agent
- `GET /api/agents/<name>/chat` - Get chat history
- `POST /api/agents/<name>/chat` - Send chat message
- `POST /api/agents/<name>/tasks/execute` - Execute a task

### Agent Communication

- `POST /api/agents/<sender>/message/<receiver>` - Send message between agents
- `POST /api/agents/<agent1>/conversation/<agent2>` - Start multi-round conversation

### Knowledge Base

- `GET /api/knowledge` - Query interactions
  - Query params: `agent_name`, `interaction_type`, `search`, `limit`, `offset`

### Health Check

- `GET /api/health` - System health and status

## Configuration

### Agent Settings

When creating an agent, you can configure:

- **Model**: Ollama model name (must be downloaded locally)
- **System Prompt**: Defines agent behavior and personality
- **Temperature**: 0.0-2.0 (lower = more focused, higher = more creative)
- **Max Tokens**: Maximum tokens in responses (100-8192)
- **API Endpoint**: Ollama API endpoint (default: http://localhost:11434)

### Database Configuration

The database path can be configured in `knowledge_base.py`:

```python
knowledge_base = KnowledgeBase(db_path="data/agent.db")
```

## Development

### Project Structure

```
agent/
├── app.py                 # Flask web application
├── agent_core.py         # Core agent implementation
├── agent_manager.py      # Agent lifecycle management
├── knowledge_base.py     # SQLite database management
├── message_bus.py        # Agent-to-agent messaging
├── init_db.py           # Database initialization script
├── seed_db.py           # Database seeding script
├── requirements.txt     # Python dependencies
├── config.yaml          # Example configuration
├── data/                # Database directory (gitignored)
│   └── agent.db        # SQLite database
├── static/             # Static web assets
│   ├── css/
│   └── js/
└── templates/          # HTML templates
    ├── index.html
    ├── chat.html
    ├── agent_comm.html
    └── knowledge.html
```

### Running in Development Mode

```bash
# The app runs in debug mode by default
python app.py

# Or use Flask's development server
export FLASK_APP=app.py
export FLASK_ENV=development
flask run
```

### Database Management

```bash
# Initialize database
python init_db.py

# Seed with sample agents
python seed_db.py

# Reset database (WARNING: deletes all data)
python init_db.py --reset
```

## Troubleshooting

### Database Issues

**Database not found:**
```bash
python init_db.py
```

**Agents not loading:**
- Check database exists: `ls data/agent.db`
- Verify tables exist: Run `init_db.py`
- Check database permissions

### Ollama Connection Issues

**Model not found:**
```bash
# Download the model
ollama pull llama3.2

# Verify it's available
ollama list
```

**Connection refused:**
```bash
# Start Ollama (usually runs automatically)
ollama serve

# Test connection
curl http://localhost:11434/api/tags
```

### Web Interface Issues

**Port already in use:**
- Change port in `app.py`: `socketio.run(app, port=5001)`
- Or kill the process using port 5000

**Agents not appearing:**
- Refresh the page
- Check browser console for errors
- Verify database has agents: `python seed_db.py`

### Import Errors

```bash
# Reinstall dependencies
pip install -r requirements.txt

# Or use a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Available Models

You can use any model available in Ollama. Popular options:

- `llama3.2` - Meta's Llama 3.2 (recommended)
- `llama3` - Meta's Llama 3
- `mistral` - Mistral AI model
- `codellama` - Code-focused Llama variant
- `phi3` - Microsoft's Phi-3

Download models:
```bash
ollama pull <model-name>
```

## License

This project is provided as-is for local use.

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.
