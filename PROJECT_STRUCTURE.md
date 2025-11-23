# Project Structure

This document describes the organization of the multi-agent system codebase.

## Directory Layout

```
agent/
├── README.md                   # Main project documentation
├── PROJECT_STRUCTURE.md        # This file
├── requirements.txt            # Python dependencies
├── config.yaml                 # Application configuration
├── app.py                      # Main Flask application entry point
│
├── src/                        # Core application code
│   ├── __init__.py            # Package initialization
│   ├── agent_core.py          # Enhanced agent implementation
│   ├── agent_manager.py       # Agent lifecycle management
│   ├── agent.py               # Legacy agent implementation
│   ├── conversation_orchestrator.py  # Multi-agent conversation coordination
│   ├── knowledge_base.py      # Semantic knowledge base with embeddings
│   └── message_bus.py         # Inter-agent messaging system
│
├── scripts/                    # Utility and management scripts
│   ├── db/                    # Database management scripts
│   │   ├── init_db.py         # Initialize databases
│   │   ├── seed_db.py         # Seed with sample agents
│   │   ├── clear_db.py        # Clear database contents
│   │   ├── migrate_db.py      # Database migrations
│   │   └── migrate_embeddings.py  # Backfill embeddings
│   └── test/                  # Test and diagnostic scripts
│       ├── check_models.py    # Check available Ollama models
│       ├── diagnose_chat.py   # Diagnose chat functionality
│       ├── test_semantic_search.py  # Test semantic search
│       └── test_agent_file_write.py # Test file writing
│
├── docs/                       # Documentation
│   ├── README.md              # Main documentation (copy at root)
│   ├── QUICK_REFERENCE.md     # Quick reference guide
│   ├── IMPLEMENTATION_SUMMARY.md  # Implementation details
│   ├── AGENTIC_SYSTEM_REVIEW.md   # System architecture review
│   ├── SEMANTIC_KNOWLEDGE_BASE.md # Knowledge base documentation
│   ├── QUICKSTART_SEMANTIC_KB.md  # Quick start guide
│   └── AGENT_FILE_WRITING_GUIDE.md # File writing guide
│
├── static/                     # Web assets (CSS, JavaScript)
│   ├── css/
│   │   └── style.css
│   └── js/
│       ├── app.js             # Main dashboard JavaScript
│       ├── chat.js            # Chat interface JavaScript
│       ├── agent_comm.js      # Agent communication JavaScript
│       └── knowledge.js       # Knowledge base viewer JavaScript
│
├── templates/                  # HTML templates
│   ├── index.html             # Main dashboard
│   ├── chat.html              # Agent chat interface
│   ├── agent_comm.html        # Agent communication interface
│   └── knowledge.html         # Knowledge base viewer
│
├── data/                       # Application data
│   ├── agent.db               # Main agent database
│   └── knowledge.db           # Knowledge base (deprecated, now in agent.db)
│
└── agent_code/                 # Agent-generated code files
    └── README.md              # Documentation for agent_code folder
```

## Key Components

### Core Application (`src/`)

**agent_core.py**: The heart of the agent system
- `EnhancedAgent`: Main agent class with tool calling, knowledge base integration
- `OllamaClient`: Interface to Ollama API
- File operations: read_file, write_file, list_directory
- Semantic search integration for context retrieval

**knowledge_base.py**: Semantic knowledge base
- Vector embeddings using Ollama (nomic-embed-text)
- Semantic search with time decay
- Interaction storage and retrieval
- Agent knowledge summaries

**agent_manager.py**: Agent lifecycle management
- Create, update, delete agents
- Load agents from database
- Manage agent registry

**conversation_orchestrator.py**: Multi-agent coordination
- Dynamic agent collaboration
- Task decomposition
- Round-robin and relevance-based orchestration

**message_bus.py**: Inter-agent messaging
- Send messages between agents
- Deliver pending messages
- Message persistence

### Database Scripts (`scripts/db/`)

**init_db.py**: Initialize the database schema
```bash
python scripts/db/init_db.py
```

**seed_db.py**: Populate database with sample agents
```bash
python scripts/db/seed_db.py
python scripts/db/seed_db.py --overwrite  # Replace existing
```

**clear_db.py**: Clear database contents
```bash
python scripts/db/clear_db.py
```

### Test Scripts (`scripts/test/`)

**test_semantic_search.py**: Test knowledge base semantic search
```bash
python scripts/test/test_semantic_search.py
```

**test_agent_file_write.py**: Test agent file writing capabilities
```bash
python scripts/test/test_agent_file_write.py
```

## Running the Application

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Initialize database** (first time only):
   ```bash
   python scripts/db/init_db.py
   python scripts/db/seed_db.py
   ```

3. **Start the application**:
   ```bash
   python app.py
   ```

4. **Access the web interface**:
   - Dashboard: http://localhost:5001
   - Chat with agent: http://localhost:5001/chat/Coder
   - Agent communication: http://localhost:5001/agent-comm
   - Knowledge base: http://localhost:5001/knowledge

## Import Conventions

### From Main Application (`app.py`)
```python
from src.knowledge_base import KnowledgeBase
from src.agent_manager import AgentManager
```

### Within `src/` Package
```python
from .agent_core import EnhancedAgent
from .knowledge_base import KnowledgeBase
```

### From Scripts
```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.knowledge_base import KnowledgeBase
```

## Development Workflow

1. **Make changes** to source files in `src/`
2. **Test changes** using scripts in `scripts/test/`
3. **Update documentation** in `docs/`
4. **Run the application** to verify everything works
5. **Commit changes** to version control

## Notes

- Flask app auto-reloads when source files change (development mode)
- Database files are stored in `data/`
- Agent-generated code goes to `agent_code/`
- Static web assets are served from `static/`
- All documentation is centralized in `docs/`

