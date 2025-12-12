#!/usr/bin/env python3
"""
Enhanced Agent Core Module

Refactored agent class that supports:
- Named agents
- File operations
- Knowledge base integration
- Direct messaging
- Chat interface
"""

import os
import re
import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path

# Configure logging for agent core
logger = logging.getLogger(__name__)

try:
    import ollama
except ImportError:
    ollama = None


class OllamaClient:
    """Client for interacting with Ollama API."""
    
    def __init__(self, api_endpoint: str = "http://localhost:11434"):
        """Initialize Ollama client."""
        self.api_endpoint = api_endpoint
        if api_endpoint != "http://localhost:11434":
            os.environ['OLLAMA_HOST'] = api_endpoint.replace('http://', '').replace('https://', '')
    
    def chat(self, model: str, messages: List[Dict[str, str]], 
             temperature: float = 0.7, max_tokens: int = 2048) -> str:
        """Send chat request to Ollama model."""
        if ollama is None:
            raise Exception("Ollama package not installed. Install with: pip install ollama")
        
        try:
            response = ollama.chat(
                model=model,
                messages=messages,
                options={
                    'temperature': temperature,
                    'num_predict': max_tokens
                }
            )
            
            # Validate response structure
            if not response or 'message' not in response:
                raise Exception("Invalid response from Ollama: missing 'message' field")
            
            if 'content' not in response['message']:
                raise Exception("Invalid response from Ollama: missing 'content' field")
            
            content = response['message']['content']
            if not content:
                raise Exception("Empty response from Ollama model")
            
            return content
            
        except ConnectionError as e:
            raise Exception(f"Cannot connect to Ollama. Is Ollama running? Error: {str(e)}")
        except Exception as e:
            error_msg = str(e)
            # Provide more helpful error messages
            if "model" in error_msg.lower() or "not found" in error_msg.lower():
                raise Exception(f"Model '{model}' not found. Make sure you've downloaded it with: ollama pull {model}")
            elif "connection" in error_msg.lower() or "refused" in error_msg.lower():
                raise Exception(f"Cannot connect to Ollama at {self.api_endpoint}. Is Ollama running?")
            else:
                raise Exception(f"Failed to communicate with Ollama: {error_msg}")
    
    def chat_with_tools(self, model: str, messages: List[Dict[str, Any]], 
                        tools: List[Dict[str, Any]],
                        temperature: float = 0.7, max_tokens: int = 2048) -> Dict[str, Any]:
        """Send chat request with native tool calling support.
        
        Args:
            model: Ollama model name
            messages: Chat messages
            tools: List of tool definitions in Ollama format
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            
        Returns:
            Dict with 'content' (str), 'tool_calls' (list of tool calls), 'tools_supported' (bool)
        """
        if ollama is None:
            raise Exception("Ollama package not installed. Install with: pip install ollama")
        
        try:
            response = ollama.chat(
                model=model,
                messages=messages,
                tools=tools,
                options={
                    'temperature': temperature,
                    'num_predict': max_tokens
                }
            )
            
            if not response or 'message' not in response:
                raise Exception("Invalid response from Ollama: missing 'message' field")
            
            message = response['message']
            content = message.get('content', '')
            tool_calls = message.get('tool_calls', [])
            
            return {
                'content': content,
                'tool_calls': tool_calls,
                'tools_supported': True
            }
            
        except ConnectionError as e:
            raise Exception(f"Cannot connect to Ollama. Is Ollama running? Error: {str(e)}")
        except Exception as e:
            error_msg = str(e)
            # Check if model doesn't support tools
            if "does not support tools" in error_msg.lower():
                logger.warning(f"Model '{model}' does not support native tool calling, falling back to prompt-based")
                return {
                    'content': '',
                    'tool_calls': [],
                    'tools_supported': False
                }
            if "model" in error_msg.lower() or "not found" in error_msg.lower():
                raise Exception(f"Model '{model}' not found. Make sure you've downloaded it with: ollama pull {model}")
            elif "connection" in error_msg.lower() or "refused" in error_msg.lower():
                raise Exception(f"Cannot connect to Ollama at {self.api_endpoint}. Is Ollama running?")
            else:
                raise Exception(f"Failed to communicate with Ollama: {error_msg}")
    
    def check_model(self, model: str) -> bool:
        """Check if model is available."""
        if ollama is None:
            return False
        try:
            models = ollama.list()
            if isinstance(models, dict) and 'models' in models:
                available_models = [m.get('name', '') for m in models['models']]
            elif isinstance(models, list):
                available_models = [m.get('name', '') if isinstance(m, dict) else str(m) for m in models]
            else:
                return True  # Assume available if check fails
            return model in available_models
        except Exception as e:
            return True  # Assume available if check fails


class AgentContextLoader:
    """Loads and manages agent context from the agent_context folder."""
    
    def __init__(self, context_dir: Optional[Path] = None):
        """Initialize context loader.
        
        Args:
            context_dir: Path to agent_context directory. If None, uses default location.
        """
        if context_dir is None:
            # Default to agent_context folder in the src directory
            self.context_dir = Path(__file__).parent / 'agent_context'
        else:
            self.context_dir = Path(context_dir)
        
        self.agents_md_path = self.context_dir / 'AGENTS.md'
        self._context_entries: List[Dict[str, Any]] = []
        self._loaded = False
    
    def _parse_agents_md(self) -> List[Dict[str, Any]]:
        """Parse AGENTS.md file to extract context entries.
        
        Returns:
            List of context entry dictionaries with keys:
            - name: Resource name
            - path: Path to the resource
            - description: What the resource contains
            - when_to_use: When to use this context
            - keywords: List of trigger keywords
        """
        if not self.agents_md_path.exists():
            logger.warning(f"AGENTS.md not found at {self.agents_md_path}")
            return []
        
        try:
            content = self.agents_md_path.read_text(encoding='utf-8')
        except Exception as e:
            logger.error(f"Error reading AGENTS.md: {e}")
            return []
        
        entries = []
        
        # Pattern to match context entries
        # Looking for sections that start with ### followed by resource name
        # and contain Path, Description, When to Use, Keywords fields
        entry_pattern = r'###\s+(.+?)\n(.*?)(?=\n###|\n---|\Z)'
        
        matches = re.findall(entry_pattern, content, re.DOTALL)
        
        for name, entry_content in matches:
            name = name.strip()
            
            # Skip template section
            if name.lower().startswith('[') or 'template' in name.lower():
                continue
            
            entry = {'name': name}
            
            # Extract Path
            path_match = re.search(r'\*\*Path\*\*:\s*`([^`]+)`', entry_content)
            if path_match:
                entry['path'] = path_match.group(1).strip()
            else:
                continue  # Skip entries without a path
            
            # Extract Description
            desc_match = re.search(r'\*\*Description\*\*:\s*(.+?)(?=\n-|\n\n|\Z)', entry_content, re.DOTALL)
            if desc_match:
                entry['description'] = desc_match.group(1).strip()
            
            # Extract When to Use
            when_match = re.search(r'\*\*When to Use\*\*:\s*(.+?)(?=\n-|\n\n|\Z)', entry_content, re.DOTALL)
            if when_match:
                entry['when_to_use'] = when_match.group(1).strip()
            
            # Extract Keywords
            keywords_match = re.search(r'\*\*Keywords\*\*:\s*(.+?)(?=\n-|\n\n|\Z)', entry_content, re.DOTALL)
            if keywords_match:
                keywords_str = keywords_match.group(1).strip()
                entry['keywords'] = [k.strip().lower() for k in keywords_str.split(',')]
            else:
                entry['keywords'] = []
            
            entries.append(entry)
            logger.debug(f"Parsed context entry: {name}")
        
        return entries
    
    def load_context_entries(self, force_reload: bool = False) -> List[Dict[str, Any]]:
        """Load context entries from AGENTS.md.
        
        Args:
            force_reload: If True, reload even if already loaded
            
        Returns:
            List of context entries
        """
        if not self._loaded or force_reload:
            self._context_entries = self._parse_agents_md()
            self._loaded = True
            logger.info(f"Loaded {len(self._context_entries)} context entries from AGENTS.md")
        
        return self._context_entries
    
    def get_relevant_context(self, query: str, max_entries: int = 3) -> str:
        """Get relevant context based on query keywords.
        
        Args:
            query: The user query or task to match against
            max_entries: Maximum number of context entries to include
            
        Returns:
            Formatted context string
        """
        entries = self.load_context_entries()
        if not entries:
            return ""
        
        query_lower = query.lower()
        query_words = set(re.findall(r'\b\w+\b', query_lower))
        
        # Score each entry based on keyword matches
        scored_entries = []
        for entry in entries:
            score = 0
            
            # Check keyword matches
            for keyword in entry.get('keywords', []):
                if keyword in query_lower or keyword in query_words:
                    score += 2  # Higher weight for direct keyword match
            
            # Check if query words appear in description or when_to_use
            description = entry.get('description', '').lower()
            when_to_use = entry.get('when_to_use', '').lower()
            
            for word in query_words:
                if len(word) > 3:  # Skip short common words
                    if word in description:
                        score += 1
                    if word in when_to_use:
                        score += 1
            
            if score > 0:
                scored_entries.append((score, entry))
        
        # Sort by score (descending) and take top entries
        scored_entries.sort(key=lambda x: x[0], reverse=True)
        top_entries = scored_entries[:max_entries]
        
        if not top_entries:
            return ""
        
        # Load and format the actual context content
        context_parts = []
        
        for score, entry in top_entries:
            content = self._load_entry_content(entry)
            if content:
                context_parts.append(f"=== {entry['name']} ===\n{content}")
        
        if context_parts:
            return "Agent Context:\n\n" + "\n\n".join(context_parts)
        
        return ""
    
    def _load_entry_content(self, entry: Dict[str, Any]) -> Optional[str]:
        """Load the actual content of a context entry.
        
        Args:
            entry: Context entry dictionary with 'path' key
            
        Returns:
            Content string or None if loading fails
        """
        path_str = entry.get('path', '')
        if not path_str:
            return None
        
        # Resolve path relative to context_dir
        if path_str.startswith('../'):
            # Path relative to parent of context_dir
            full_path = (self.context_dir / path_str).resolve()
        else:
            full_path = (self.context_dir / path_str).resolve()
        
        if not full_path.exists():
            logger.warning(f"Context file not found: {full_path}")
            return None
        
        try:
            if full_path.is_file():
                content = full_path.read_text(encoding='utf-8')
                # Truncate if too long
                if len(content) > 4000:
                    content = content[:4000] + "\n\n[... truncated for brevity ...]"
                return content
            elif full_path.is_dir():
                # List directory contents
                items = [f"- {item.name}" for item in full_path.iterdir()]
                return f"Directory contents:\n" + "\n".join(items)
        except Exception as e:
            logger.error(f"Error loading context from {full_path}: {e}")
            return None
        
        return None
    
    def get_available_context_summary(self) -> str:
        """Get a summary of all available context entries.
        
        Returns:
            Formatted summary string
        """
        entries = self.load_context_entries()
        if not entries:
            return "No context resources available."
        
        lines = ["Available Context Resources:"]
        for entry in entries:
            name = entry.get('name', 'Unknown')
            desc = entry.get('description', 'No description')
            lines.append(f"- {name}: {desc}")
        
        return "\n".join(lines)


class EnhancedAgent:
    """Enhanced agent with file operations, knowledge base, and messaging."""
    
    # Define all available tools
    AVAILABLE_TOOLS = {
        'write_file': 'Write content to a file',
        'read_file': 'Read a file\'s contents',
        'create_folder': 'Create a new folder/directory',
        'list_directory': 'List directory contents',
        'web_search': 'Search the web for information'
    }
    
    # Shared context loader instance (class-level)
    _context_loader: Optional[AgentContextLoader] = None
    
    @classmethod
    def get_context_loader(cls) -> AgentContextLoader:
        """Get or create the shared context loader instance."""
        if cls._context_loader is None:
            cls._context_loader = AgentContextLoader()
        return cls._context_loader
    
    def __init__(
        self,
        name: str,
        model: str,
        system_prompt: str = "",
        settings: Optional[Dict[str, Any]] = None,
        knowledge_base=None,
        message_bus=None,
        tools: Optional[List[str]] = None,
        avatar_seed: Optional[str] = None,
        session_id: Optional[str] = None
    ):
        """Initialize enhanced agent.
        
        Args:
            name: Agent name
            model: Ollama model name
            system_prompt: System prompt for the agent
            settings: Agent settings
            knowledge_base: Knowledge base instance
            message_bus: Message bus instance
            tools: List of allowed tool names. If None, all tools are allowed.
            avatar_seed: Custom seed for avatar generation. If None, uses agent name.
            session_id: Session ID for scoping knowledge to a specific conversation session.
        """
        self.name = name
        self.model = model
        self.system_prompt = system_prompt
        self.settings = settings or {}
        self.knowledge_base = knowledge_base
        self.message_bus = message_bus
        self.avatar_seed = avatar_seed or name  # Default to agent name
        self.session_id = session_id  # Session scoping for knowledge
        
        # Set allowed tools (if None, allow all tools)
        if tools is None:
            self.allowed_tools = list(self.AVAILABLE_TOOLS.keys())
        else:
            # Validate and filter tools
            self.allowed_tools = [
                tool for tool in tools 
                if tool in self.AVAILABLE_TOOLS
            ]
        
        # Initialize Ollama client
        api_endpoint = self.settings.get('api_endpoint', 'http://localhost:11434')
        self.client = OllamaClient(api_endpoint)
        
        # Initialize context loader (shared across all agents)
        self.context_loader = self.get_context_loader()
        
        # Conversation history
        self.conversation_history: List[Dict[str, str]] = []
        if self.system_prompt:
            self.conversation_history.append({
                'role': 'system',
                'content': self.system_prompt
            })
        
        # Pending messages from other agents
        self.pending_messages: List[Dict[str, str]] = []
    
    def set_session_id(self, session_id: str):
        """Set the session ID for scoping knowledge.
        
        Args:
            session_id: The session ID to scope knowledge to
        """
        self.session_id = session_id
        logger.info(f"[Agent {self.name}] Session ID set to: {session_id}")
    
    def receive_message(self, sender_name: str, message_content: str):
        """Receive a message from another agent."""
        self.pending_messages.append({
            'sender': sender_name,
            'content': message_content,
            'timestamp': datetime.utcnow().isoformat()
        })
    
    def _get_ollama_tools(self) -> List[Dict[str, Any]]:
        """Generate Ollama-format tool definitions for native tool calling.
        
        Returns:
            List of tool definitions in Ollama format
        """
        tool_definitions = {
            'write_file': {
                'type': 'function',
                'function': {
                    'name': 'write_file',
                    'description': 'Write content to a file. Creates or overwrites the file. Files are saved to the agent_code/ folder.',
                    'parameters': {
                        'type': 'object',
                        'properties': {
                            'path': {
                                'type': 'string',
                                'description': 'The filename or path to write to (e.g., "game.py", "src/utils.js")'
                            },
                            'content': {
                                'type': 'string',
                                'description': 'The content to write to the file'
                            }
                        },
                        'required': ['path', 'content']
                    }
                }
            },
            'read_file': {
                'type': 'function',
                'function': {
                    'name': 'read_file',
                    'description': 'Read the contents of a file.',
                    'parameters': {
                        'type': 'object',
                        'properties': {
                            'path': {
                                'type': 'string',
                                'description': 'The filename or path to read from'
                            }
                        },
                        'required': ['path']
                    }
                }
            },
            'create_folder': {
                'type': 'function',
                'function': {
                    'name': 'create_folder',
                    'description': 'Create a new folder/directory.',
                    'parameters': {
                        'type': 'object',
                        'properties': {
                            'path': {
                                'type': 'string',
                                'description': 'The folder path to create (e.g., "my_project", "src/components")'
                            }
                        },
                        'required': ['path']
                    }
                }
            },
            'list_directory': {
                'type': 'function',
                'function': {
                    'name': 'list_directory',
                    'description': 'List the contents of a directory.',
                    'parameters': {
                        'type': 'object',
                        'properties': {
                            'path': {
                                'type': 'string',
                                'description': 'The directory path to list (use "." for current directory)'
                            }
                        },
                        'required': ['path']
                    }
                }
            },
            'web_search': {
                'type': 'function',
                'function': {
                    'name': 'web_search',
                    'description': 'Search the web for information.',
                    'parameters': {
                        'type': 'object',
                        'properties': {
                            'query': {
                                'type': 'string',
                                'description': 'The search query'
                            },
                            'max_results': {
                                'type': 'integer',
                                'description': 'Maximum number of results to return (default: 5)'
                            }
                        },
                        'required': ['query']
                    }
                }
            }
        }
        
        return [tool_definitions[tool] for tool in self.allowed_tools if tool in tool_definitions]
    
    def _execute_tool_call(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a single tool call.
        
        Args:
            tool_name: Name of the tool to execute
            arguments: Tool arguments
            
        Returns:
            Tool execution result
        """
        if tool_name not in self.allowed_tools:
            logger.warning(f"[Agent {self.name}] Tool '{tool_name}' access DENIED. Allowed: {self.allowed_tools}")
            return {
                'success': False, 
                'error': f'Access denied: Tool "{tool_name}" is not available for this agent.'
            }
        
        if tool_name == 'write_file':
            logger.info(f"[Agent {self.name}] Executing write_file(path='{arguments.get('path', '')}')")
            content = arguments.get('content')
            if content is None:
                return {'success': False, 'error': 'No content provided for write_file. The "content" parameter is required.'}
            return self.write_file(arguments.get('path', ''), content)
        elif tool_name == 'read_file':
            logger.info(f"[Agent {self.name}] Executing read_file(path='{arguments.get('path', '')}')")
            return self.read_file(arguments.get('path', ''))
        elif tool_name == 'create_folder':
            logger.info(f"[Agent {self.name}] Executing create_folder(path='{arguments.get('path', '')}')")
            return self.create_folder(arguments.get('path', ''))
        elif tool_name == 'list_directory':
            logger.info(f"[Agent {self.name}] Executing list_directory(path='{arguments.get('path', '.')}')")
            return self.list_directory(arguments.get('path', '.'))
        elif tool_name == 'web_search':
            logger.info(f"[Agent {self.name}] Executing web_search(query='{arguments.get('query', '')}')")
            return self.web_search(arguments.get('query', ''), arguments.get('max_results', 5))
        else:
            logger.warning(f"[Agent {self.name}] Unknown tool: {tool_name}")
            return {'success': False, 'error': f'Unknown tool: {tool_name}'}
    
    def _get_tools_info(self) -> str:
        """Generate tools information based on allowed tools.
        
        Returns:
            Formatted string describing available tools
        """
        if not self.allowed_tools:
            return "Note: No tools are available for this agent."
        
        tools_lines = ["=== TOOLS ==="]
        tools_lines.append("To EXECUTE an action, you MUST use the exact TOOL_CALL format below.")
        tools_lines.append("Just showing code in your response does NOT execute it - you MUST wrap it in TOOL_CALL tags.")
        tools_lines.append("")
        
        if 'write_file' in self.allowed_tools:
            tools_lines.append('WRITE FILE (creates or overwrites a file):')
            tools_lines.append('<TOOL_CALL tool="write_file">{"path": "filename.py", "content": "YOUR ACTUAL CODE HERE"}</TOOL_CALL>')
            tools_lines.append('')
        
        if 'read_file' in self.allowed_tools:
            tools_lines.append('READ FILE:')
            tools_lines.append('<TOOL_CALL tool="read_file">{"path": "filename.py"}</TOOL_CALL>')
            tools_lines.append('')
        
        if 'create_folder' in self.allowed_tools:
            tools_lines.append('CREATE FOLDER (creates a new directory):')
            tools_lines.append('<TOOL_CALL tool="create_folder">{"path": "folder_name"}</TOOL_CALL>')
            tools_lines.append('')
        
        if 'list_directory' in self.allowed_tools:
            tools_lines.append('LIST DIRECTORY:')
            tools_lines.append('<TOOL_CALL tool="list_directory">{"path": "."}</TOOL_CALL>')
            tools_lines.append('')
        
        if 'web_search' in self.allowed_tools:
            tools_lines.append('WEB SEARCH:')
            tools_lines.append('<TOOL_CALL tool="web_search">{"query": "search terms", "max_results": 5}</TOOL_CALL>')
            tools_lines.append('')
        
        tools_lines.append("CRITICAL RULES:")
        tools_lines.append("1. JSON must be valid - escape special characters properly")
        tools_lines.append("2. JSON ESCAPING IS REQUIRED:")
        tools_lines.append("   - Newlines: use \\n (not actual newlines)")
        tools_lines.append("   - Double quotes: use \\\" (EVERY quote inside content must be escaped)")
        tools_lines.append("   - Backslashes: use \\\\ (double them)")
        tools_lines.append("3. Always close with </TOOL_CALL>")
        
        if 'write_file' in self.allowed_tools:
            tools_lines.append("4. Files are saved to agent_code/ folder automatically")
            tools_lines.append("5. Use file extensions (.py, .js, etc) - do NOT create files without extensions")
            tools_lines.append("")
            tools_lines.append("EXAMPLE - Writing a Python file with proper escaping:")
            tools_lines.append('<TOOL_CALL tool="write_file">{"path": "game.py", "content": "class Game:\\n    def __init__(self):\\n        self.score = 0\\n\\n    def play(self):\\n        print(\\"Playing!\\")\\n\\nif __name__ == \\"__main__\\":\\n    game = Game()\\n    game.play()"}</TOOL_CALL>')
            tools_lines.append("")
            tools_lines.append("WRONG (causes errors):")
            tools_lines.append('  {"content": "if __name__ == "__main__":"}  <- Unescaped quotes!')
            tools_lines.append("CORRECT:")
            tools_lines.append('  {"content": "if __name__ == \\"__main__\\":"}  <- Quotes escaped with \\"')
        
        return "\n".join(tools_lines)
    
    def _get_context(self, query: str = "") -> str:
        """Get context from knowledge base and agent_context folder using semantic search.
        
        Args:
            query: Current user message or task for semantic retrieval
            
        Returns:
            Formatted context string
        """
        context_parts = []
        
        # Add relevant context from agent_context folder based on query keywords
        if query and self.context_loader:
            try:
                agent_context = self.context_loader.get_relevant_context(query, max_entries=2)
                if agent_context:
                    context_parts.append(agent_context)
                    logger.debug(f"[Agent {self.name}] Added agent context for query: {query[:50]}...")
            except Exception as e:
                logger.warning(f"[Agent {self.name}] Error loading agent context: {e}")
        
        # Add semantically relevant interactions if query provided
        # Filter by session_id if set to scope knowledge to current session
        if self.knowledge_base and query:
            try:
                relevant_interactions = self.knowledge_base.semantic_search_interactions(
                    query=query,
                    agent_name=self.name,
                    top_k=10,
                    time_decay_factor=0.95,
                    session_id=self.session_id  # Scope to current session
                )
                
                if relevant_interactions:
                    interactions_text = []
                    for interaction in relevant_interactions:
                        timestamp = interaction['timestamp']
                        interaction_type = interaction['interaction_type']
                        content = interaction['content'][:200]  # Truncate long content
                        score = interaction.get('relevance_score', 0)
                        
                        interactions_text.append(
                            f"[{timestamp}] {interaction_type} (relevance: {score:.2f}): {content}"
                        )
                    
                    context_parts.append(f"Relevant Previous Interactions:\n" + "\n".join(interactions_text))
            except Exception as e:
                print(f"[Agent {self.name}] Error in semantic search, falling back: {e}")
                # Fallback to recent interactions (still scoped to session)
                recent_interactions = self.knowledge_base.get_interactions(
                    agent_name=self.name,
                    session_id=self.session_id,
                    limit=10
                )
                if recent_interactions:
                    interactions_text = []
                    for interaction in recent_interactions:
                        timestamp = interaction['timestamp']
                        interaction_type = interaction['interaction_type']
                        content = interaction['content'][:200]
                        interactions_text.append(f"[{timestamp}] {interaction_type}: {content}")
                    context_parts.append(f"Recent Interactions:\n" + "\n".join(interactions_text))
        
        # Add pending messages
        if self.pending_messages:
            messages_text = "\n".join([
                f"Message from {msg['sender']}: {msg['content']}"
                for msg in self.pending_messages
            ])
            context_parts.append(f"Pending Messages:\n{messages_text}")
            self.pending_messages.clear()
        
        return "\n\n".join(context_parts) if context_parts else ""
    
    def chat(self, user_message: str) -> str:
        """Chat with the agent with native Ollama tool calling support."""
        logger.info(f"[Agent {self.name}] chat() called with message: '{user_message[:100]}...'")
        logger.debug(f"[Agent {self.name}] Allowed tools: {self.allowed_tools}")
        
        # Get context from knowledge base using semantic search
        context = self._get_context(query=user_message)
        
        # Build prompt with context (no XML tool info needed with native tool calling)
        if context:
            full_prompt = f"{context}\n\nUser: {user_message}"
        else:
            full_prompt = user_message
        
        messages = self.conversation_history + [{
            'role': 'user',
            'content': full_prompt
        }]
        
        temperature = self.settings.get('temperature', 0.7)
        max_tokens = self.settings.get('max_tokens', 2048)
        
        # Get Ollama tool definitions
        ollama_tools = self._get_ollama_tools()
        
        logger.debug(f"[Agent {self.name}] Calling Ollama model '{self.model}' with {len(messages)} messages and {len(ollama_tools)} tools")
        
        try:
            tool_results = []
            final_response = ""
            use_xml_fallback = False
            
            if ollama_tools:
                # Try native tool calling first
                response_data = self.client.chat_with_tools(
                    self.model,
                    messages,
                    tools=ollama_tools,
                    temperature=temperature,
                    max_tokens=max_tokens
                )
                
                # Check if model supports native tools
                if not response_data.get('tools_supported', True):
                    # Model doesn't support native tools - use XML-based prompt
                    logger.info(f"[Agent {self.name}] Model doesn't support native tools, using XML-based approach")
                    use_xml_fallback = True
                else:
                    content = response_data.get('content', '')
                    tool_calls = response_data.get('tool_calls', [])
                    
                    logger.info(f"[Agent {self.name}] Got response: content={len(content)} chars, tool_calls={len(tool_calls)}")
                    
                    if tool_calls:
                        logger.info(f"[Agent {self.name}] Processing {len(tool_calls)} native tool call(s)")
                        
                        for tool_call in tool_calls:
                            func = tool_call.get('function', {})
                            tool_name = func.get('name', '')
                            arguments = func.get('arguments', {})
                            
                            logger.info(f"[Agent {self.name}] Executing tool: {tool_name} with args: {arguments}")
                            
                            result = self._execute_tool_call(tool_name, arguments)
                            
                            if result.get('success'):
                                logger.info(f"[Agent {self.name}] Tool '{tool_name}' SUCCESS")
                            else:
                                logger.error(f"[Agent {self.name}] Tool '{tool_name}' FAILED: {result.get('error')}")
                            
                            tool_results.append({
                                'tool': tool_name,
                                'params': arguments,
                                'result': result
                            })
                    
                    final_response = content
            else:
                use_xml_fallback = True
            
            # Use XML-based approach if native tools aren't supported or no tools defined
            if use_xml_fallback:
                # Add XML tool instructions to prompt
                tools_info = self._get_tools_info()
                if context:
                    xml_prompt = f"{context}\n\n{tools_info}\n\nUser: {user_message}"
                else:
                    xml_prompt = f"{tools_info}\n\nUser: {user_message}"
                
                xml_messages = self.conversation_history + [{
                    'role': 'user',
                    'content': xml_prompt
                }]
                
                response = self.client.chat(
                    self.model,
                    xml_messages,
                    temperature=temperature,
                    max_tokens=max_tokens
                )
                final_response = response
            
            # Also try XML-based tool parsing as fallback (for backwards compatibility)
            if not tool_results and final_response:
                xml_response, xml_tool_results = self._parse_and_execute_tools(final_response)
                if xml_tool_results:
                    logger.info(f"[Agent {self.name}] Found {len(xml_tool_results)} tool(s) via XML parsing fallback")
                    tool_results = xml_tool_results
                    final_response = xml_response
            
            logger.info(f"[Agent {self.name}] Tool execution complete. {len(tool_results)} tool(s) executed")
            
            # If tools were executed, append results
            if tool_results:
                tool_feedback = "\n\n[Tool Execution Results]\n"
                for tool_result in tool_results:
                    tool_feedback += f"• {tool_result['tool']}: "
                    if tool_result['result'].get('success'):
                        tool_feedback += "✓ Success"
                        if 'path' in tool_result['result']:
                            tool_feedback += f" - {tool_result['result']['path']}"
                    else:
                        tool_feedback += f"✗ Error: {tool_result['result'].get('error', 'Unknown')}"
                    tool_feedback += "\n"
                final_response += tool_feedback
            
            # Update conversation history
            self.conversation_history.append({
                'role': 'user',
                'content': user_message
            })
            self.conversation_history.append({
                'role': 'assistant',
                'content': final_response
            })
            
            # Store in knowledge base
            if self.knowledge_base:
                self.knowledge_base.add_interaction(
                    agent_name=self.name,
                    interaction_type='user_chat',
                    content=f"User: {user_message}\nAgent: {final_response}",
                    metadata={'user_message': user_message, 'agent_response': final_response, 'tools_used': len(tool_results) > 0},
                    session_id=self.session_id
                )
            
            return final_response
        except Exception as e:
            error_msg = f"Error: {str(e)}"
            if self.knowledge_base:
                self.knowledge_base.add_interaction(
                    agent_name=self.name,
                    interaction_type='user_chat',
                    content=f"User: {user_message}\nError: {error_msg}",
                    metadata={'error': str(e)},
                    session_id=self.session_id
                )
            return error_msg
    
    def _repair_json_string(self, json_str: str) -> str:
        """Attempt to repair common JSON errors from LLM output.
        
        Common issues:
        - Unescaped quotes inside string values
        - Unescaped newlines
        - Missing escapes for backslashes
        
        Args:
            json_str: Potentially malformed JSON string
            
        Returns:
            Repaired JSON string
        """
        import re
        
        # First, try to parse as-is
        try:
            json.loads(json_str)
            return json_str  # Already valid
        except json.JSONDecodeError:
            pass
        
        # Strategy: Find the "content" field and properly escape its value
        # Pattern to find content field with value
        content_pattern = r'"content"\s*:\s*"'
        content_match = re.search(content_pattern, json_str)
        
        if not content_match:
            return json_str  # Can't find content field, return as-is
        
        # Find where the content value starts
        content_start = content_match.end()
        
        # Find the end of the content value by looking for unescaped quote followed by } or ,
        # This is tricky because we need to handle nested quotes
        
        # Count backwards from the end to find the closing pattern
        # Look for "} or ", at the end
        json_str_stripped = json_str.rstrip()
        
        if json_str_stripped.endswith('"}'):
            # Find the last "} pattern
            content_end = json_str_stripped.rfind('"}')
        elif json_str_stripped.endswith('"}}}'):
            # Handle extra braces from malformed closing
            content_end = json_str_stripped.rfind('"}')
        elif json_str_stripped.endswith('"}}'):
            # Handle single extra brace from malformed closing
            content_end = json_str_stripped.rfind('"}')
        else:
            return json_str  # Can't determine end
        
        if content_end <= content_start:
            return json_str
        
        # Extract the content value
        content_value = json_str[content_start:content_end]
        
        # Escape unescaped quotes within the content
        # But don't double-escape already escaped quotes
        repaired_content = ""
        i = 0
        while i < len(content_value):
            char = content_value[i]
            if char == '\\' and i + 1 < len(content_value):
                # Already escaped sequence, keep as-is
                repaired_content += char + content_value[i + 1]
                i += 2
            elif char == '"':
                # Unescaped quote - escape it
                repaired_content += '\\"'
                i += 1
            elif char == '\n':
                # Literal newline - escape it
                repaired_content += '\\n'
                i += 1
            elif char == '\r':
                # Literal carriage return - escape it
                repaired_content += '\\r'
                i += 1
            elif char == '\t':
                # Literal tab - escape it
                repaired_content += '\\t'
                i += 1
            else:
                repaired_content += char
                i += 1
        
        # Reconstruct JSON
        repaired_json = json_str[:content_start] + repaired_content + json_str[content_end:]
        
        # Validate the repair
        try:
            json.loads(repaired_json)
            logger.info(f"[Agent {self.name}] Successfully repaired JSON")
            return repaired_json
        except json.JSONDecodeError as e:
            logger.warning(f"[Agent {self.name}] JSON repair failed: {e}")
            # Try a more aggressive repair - escape ALL quotes in content
            try:
                aggressive_content = content_value.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n').replace('\r', '\\r').replace('\t', '\\t')
                aggressive_json = json_str[:content_start] + aggressive_content + json_str[content_end:]
                json.loads(aggressive_json)
                logger.info(f"[Agent {self.name}] Aggressive JSON repair succeeded")
                return aggressive_json
            except:
                pass
            
            return json_str  # Return original if repair failed
    
    def _extract_balanced_json(self, text: str) -> Optional[str]:
        """Extract a JSON object from text by counting balanced braces.
        
        Args:
            text: Text that starts at or before a JSON object
            
        Returns:
            The extracted JSON string, or None if not found
        """
        # Skip whitespace to find the opening brace
        text = text.lstrip()
        if not text.startswith('{'):
            return None
        
        brace_count = 0
        in_string = False
        escape_next = False
        json_end = -1
        
        for i, char in enumerate(text):
            if escape_next:
                escape_next = False
                continue
            
            if char == '\\' and in_string:
                escape_next = True
                continue
            
            if char == '"' and not escape_next:
                in_string = not in_string
                continue
            
            if not in_string:
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        json_end = i + 1
                        break
        
        if json_end > 0:
            return text[:json_end]
        return None
    
    def _parse_and_execute_tools(self, response: str) -> tuple[str, List[Dict[str, Any]]]:
        """Parse tool calls from agent response and execute them.
        
        Returns:
            Tuple of (modified_response, tool_results)
        """
        import re
        
        tool_results = []
        modified_response = response
        
        # Pattern to match tool calls: <TOOL_CALL tool="name">params</TOOL_CALL>
        # Use a more robust approach that handles nested braces
        tool_pattern = r'<TOOL_CALL tool="([^"]+)">\s*(\{[\s\S]*?\})\s*</TOOL_CALL>'
        matches = re.findall(tool_pattern, response, re.DOTALL)
        
        # If no matches, try alternative pattern for malformed closing tags
        if not matches:
            alt_pattern = r'<TOOL_CALL tool="([^"]+)">\s*(\{[\s\S]*?\})\s*(?:\}+|$)'
            matches = re.findall(alt_pattern, response, re.DOTALL)
        
        # Try format: <TOOL_CALL>{"tool": "name", "params": {...}}</TOOL_CALL>
        if not matches:
            json_tool_pattern = r'<TOOL_CALL>\s*(\{[\s\S]*?\})\s*</TOOL_CALL>'
            json_matches = re.findall(json_tool_pattern, response, re.DOTALL)
            for json_str in json_matches:
                try:
                    data = json.loads(json_str)
                    tool_name = data.get('tool', '')
                    params = data.get('params', {})
                    if tool_name and params:
                        # Convert to the expected format (tool_name, params_json_str)
                        matches.append((tool_name, json.dumps(params)))
                        logger.info(f"[Agent {self.name}] Parsed JSON-format tool call: {tool_name}")
                except json.JSONDecodeError:
                    logger.warning(f"[Agent {self.name}] Failed to parse JSON tool call: {json_str[:100]}")
        
        # If still no matches but we see TOOL_CALL tags, try to extract JSON more carefully
        if not matches and '<TOOL_CALL' in response:
            # Find all TOOL_CALL occurrences and extract JSON with balanced braces
            tool_start_pattern = r'<TOOL_CALL tool="([^"]+)">'
            for match in re.finditer(tool_start_pattern, response):
                tool_name = match.group(1)
                start_pos = match.end()
                
                # Find the JSON object by counting braces
                json_str = self._extract_balanced_json(response[start_pos:])
                if json_str:
                    matches.append((tool_name, json_str))
        
        logger.info(f"[Agent {self.name}] Parsing response for tool calls, found {len(matches)} tool call(s)")
        if matches:
            logger.debug(f"[Agent {self.name}] Raw response excerpt: {response[:500]}...")
        
        for tool_name, params_str in matches:
            logger.info(f"[Agent {self.name}] Executing tool: {tool_name}")
            logger.debug(f"[Agent {self.name}] Tool params (raw): {params_str}")
            
            try:
                # Clean up the params string - remove trailing extra braces
                cleaned_params = params_str.strip()
                
                # Use balanced brace extraction to get clean JSON
                # This handles cases where LLM outputs extra } at the end
                extracted_json = self._extract_balanced_json(cleaned_params)
                if extracted_json:
                    cleaned_params = extracted_json
                    logger.debug(f"[Agent {self.name}] Extracted balanced JSON: {cleaned_params[:200]}...")
                
                # Try to repair JSON before parsing (handles LLM escaping errors)
                repaired_params_str = self._repair_json_string(cleaned_params)
                
                # Final cleanup: strip any trailing extra braces that might remain
                # This handles the common LLM error of outputting "}} instead of "}
                while repaired_params_str.rstrip().endswith('}}'):
                    # Try to parse as-is first
                    try:
                        json.loads(repaired_params_str)
                        break  # Valid JSON, don't strip
                    except json.JSONDecodeError:
                        # Invalid, try removing trailing brace
                        repaired_params_str = repaired_params_str.rstrip()[:-1]
                        logger.debug(f"[Agent {self.name}] Stripped trailing brace, now: ...{repaired_params_str[-50:]}")
                
                # Parse parameters (expect JSON format)
                params = json.loads(repaired_params_str)
                logger.info(f"[Agent {self.name}] Tool '{tool_name}' parsed params: {params}")
                
                # Check if tool is allowed
                if tool_name not in self.allowed_tools:
                    logger.warning(f"[Agent {self.name}] Tool '{tool_name}' access DENIED. Allowed: {self.allowed_tools}")
                    result = {
                        'success': False, 
                        'error': f'Access denied: Tool "{tool_name}" is not available for this agent. Available tools: {", ".join(self.allowed_tools)}'
                    }
                # Execute tool
                elif tool_name == 'write_file':
                    logger.info(f"[Agent {self.name}] Calling write_file(path='{params.get('path', '')}', content_len={len(params.get('content', ''))})")
                    result = self.write_file(
                        params.get('path', ''),
                        params.get('content', '')
                    )
                elif tool_name == 'read_file':
                    logger.info(f"[Agent {self.name}] Calling read_file(path='{params.get('path', '')}')")
                    result = self.read_file(params.get('path', ''))
                elif tool_name == 'create_folder':
                    logger.info(f"[Agent {self.name}] Calling create_folder(path='{params.get('path', '')}')")
                    result = self.create_folder(params.get('path', ''))
                elif tool_name == 'list_directory':
                    logger.info(f"[Agent {self.name}] Calling list_directory(path='{params.get('path', '.')}')")
                    result = self.list_directory(params.get('path', '.'))
                elif tool_name == 'web_search':
                    logger.info(f"[Agent {self.name}] Calling web_search(query='{params.get('query', '')}', max_results={params.get('max_results', 5)})")
                    result = self.web_search(
                        params.get('query', ''),
                        params.get('max_results', 5)
                    )
                else:
                    logger.warning(f"[Agent {self.name}] Unknown tool requested: {tool_name}")
                    result = {'success': False, 'error': f'Unknown tool: {tool_name}'}
                
                # Log the result
                if result.get('success'):
                    logger.info(f"[Agent {self.name}] Tool '{tool_name}' SUCCESS: {result}")
                else:
                    logger.error(f"[Agent {self.name}] Tool '{tool_name}' FAILED: {result.get('error', 'Unknown error')}")
                
                tool_results.append({
                    'tool': tool_name,
                    'params': params,
                    'result': result
                })
                
                # Replace tool call in response with result summary
                # Be flexible with the closing syntax
                original_patterns = [
                    f'<TOOL_CALL tool="{tool_name}">{params_str}</TOOL_CALL>',
                    f'<TOOL_CALL tool="{tool_name}">{params_str}}}',
                    f'<TOOL_CALL tool="{tool_name}"> {params_str} </TOOL_CALL>',
                    f'<TOOL_CALL tool="{tool_name}"> {params_str}}}',
                ]
                
                if result.get('success'):
                    replacement = f"[Executed: {tool_name} - Success]"
                else:
                    replacement = f"[Executed: {tool_name} - Error: {result.get('error', 'Unknown error')}]"
                
                for pattern in original_patterns:
                    if pattern in modified_response:
                        modified_response = modified_response.replace(pattern, replacement)
                        break
                
            except json.JSONDecodeError as e:
                logger.error(f"[Agent {self.name}] Tool '{tool_name}' JSON parse error: {str(e)}")
                logger.debug(f"[Agent {self.name}] Invalid JSON was: {params_str}")
                tool_results.append({
                    'tool': tool_name,
                    'params': params_str,
                    'result': {'success': False, 'error': f'Invalid JSON parameters: {str(e)}'}
                })
            except Exception as e:
                logger.exception(f"[Agent {self.name}] Tool '{tool_name}' unexpected error: {str(e)}")
                tool_results.append({
                    'tool': tool_name,
                    'params': params_str,
                    'result': {'success': False, 'error': str(e)}
                })
        
        return modified_response, tool_results
    
    def execute_task(self, task: str) -> str:
        """Execute a single task with native Ollama tool calling support."""
        # Get semantically relevant context
        context = self._get_context(query=task)
        
        # Build task prompt (simplified - no XML tool instructions needed)
        task_prompt = f"""Execute: {task}

{context if context else ''}

INSTRUCTIONS:
1. Take CONCRETE ACTION using the tools available to you
2. If this task involves creating folders, use the create_folder tool
3. If this task involves writing code, use the write_file tool to ACTUALLY create the file
4. Don't just describe what you would do - DO IT using tool calls
5. Summarize what you accomplished after executing tools"""

        max_iterations = 3  # Allow agent to use tools iteratively
        iteration = 0
        accumulated_response = ""
        
        # Get Ollama tool definitions
        ollama_tools = self._get_ollama_tools()
        
        while iteration < max_iterations:
            messages = self.conversation_history + [{
                'role': 'user',
                'content': task_prompt if iteration == 0 else f"Continue with task: {task}\n\nPrevious actions: {accumulated_response}"
            }]
            
            temperature = self.settings.get('temperature', 0.7)
            max_tokens = self.settings.get('max_tokens', 2048)
            
            try:
                tool_results = []
                response_content = ""
                
                use_xml_fallback = False
                
                if ollama_tools:
                    # Try native tool calling first
                    response_data = self.client.chat_with_tools(
                        self.model,
                        messages,
                        tools=ollama_tools,
                        temperature=temperature,
                        max_tokens=max_tokens
                    )
                    
                    # Check if model supports native tools
                    if not response_data.get('tools_supported', True):
                        logger.info(f"[Agent {self.name}] Model doesn't support native tools, using XML-based approach")
                        use_xml_fallback = True
                    else:
                        response_content = response_data.get('content', '')
                        tool_calls = response_data.get('tool_calls', [])
                        
                        logger.info(f"[Agent {self.name}] Task response: content={len(response_content)} chars, tool_calls={len(tool_calls)}")
                        
                        if tool_calls:
                            for tool_call in tool_calls:
                                func = tool_call.get('function', {})
                                tool_name = func.get('name', '')
                                arguments = func.get('arguments', {})
                                
                                logger.info(f"[Agent {self.name}] Task executing tool: {tool_name}")
                                
                                result = self._execute_tool_call(tool_name, arguments)
                                tool_results.append({
                                    'tool': tool_name,
                                    'params': arguments,
                                    'result': result
                                })
                else:
                    use_xml_fallback = True
                
                # Use XML-based approach if native tools aren't supported
                if use_xml_fallback:
                    tools_info = self._get_tools_info()
                    xml_task_prompt = f"""Execute: {task}

{context if context else ''}

{tools_info}

INSTRUCTIONS:
1. Take CONCRETE ACTION using the tools above
2. If this task involves creating folders, use create_folder
3. If this task involves writing code, use write_file to ACTUALLY create the file
4. Don't just describe what you would do - DO IT using tool calls
5. Summarize what you accomplished after executing tools"""
                    
                    xml_messages = self.conversation_history + [{
                        'role': 'user',
                        'content': xml_task_prompt if iteration == 0 else f"Continue with task: {task}\n\nPrevious actions: {accumulated_response}"
                    }]
                    
                    response_content = self.client.chat(
                        self.model,
                        xml_messages,
                        temperature=temperature,
                        max_tokens=max_tokens
                    )
                
                # Also try XML-based tool parsing as fallback
                if not tool_results and response_content:
                    xml_response, xml_tool_results = self._parse_and_execute_tools(response_content)
                    if xml_tool_results:
                        logger.info(f"[Agent {self.name}] Task found {len(xml_tool_results)} tool(s) via XML fallback")
                        tool_results = xml_tool_results
                        response_content = xml_response
                
                # If no tools were called, we're done
                if not tool_results:
                    accumulated_response += response_content
                    break
                
                # Build feedback for agent about tool execution
                tool_feedback = "\n\nTool Execution Results:\n"
                for tool_result in tool_results:
                    tool_feedback += f"- {tool_result['tool']}: "
                    if tool_result['result'].get('success'):
                        tool_feedback += "✓ Success"
                        if 'path' in tool_result['result']:
                            tool_feedback += f" (path: {tool_result['result']['path']})"
                        if 'content' in tool_result['result']:
                            content_preview = tool_result['result']['content'][:100]
                            tool_feedback += f"\n  Content preview: {content_preview}..."
                    else:
                        tool_feedback += f"✗ Error: {tool_result['result'].get('error', 'Unknown')}"
                    tool_feedback += "\n"
                
                accumulated_response += response_content + tool_feedback
                task_prompt = tool_feedback  # Feed results back for next iteration
                
                iteration += 1
                
            except Exception as e:
                error_msg = f"Error executing task: {str(e)}"
                if self.knowledge_base:
                    self.knowledge_base.add_interaction(
                        agent_name=self.name,
                        interaction_type='task_execution',
                        content=f"Task: {task}\nError: {error_msg}",
                        metadata={'error': str(e)},
                        session_id=self.session_id
                    )
                return error_msg
        
        # Update conversation history
        self.conversation_history.append({
            'role': 'user',
            'content': f"Execute: {task}"
        })
        self.conversation_history.append({
            'role': 'assistant',
            'content': accumulated_response
        })
        
        # Store in knowledge base
        if self.knowledge_base:
            self.knowledge_base.add_interaction(
                agent_name=self.name,
                interaction_type='task_execution',
                content=f"Task: {task}\nResult: {accumulated_response}",
                metadata={'task': task, 'result': accumulated_response},
                session_id=self.session_id
            )
        
        return accumulated_response
    
    def read_file(self, file_path: str) -> Dict[str, Any]:
        """Read a file."""
        logger.info(f"[Agent {self.name}] read_file called with path='{file_path}'")
        try:
            path = Path(file_path)
            logger.debug(f"[Agent {self.name}] read_file: Checking path: {path}, exists: {path.exists()}")
            
            if not path.exists():
                logger.warning(f"[Agent {self.name}] read_file: File not found: {path}")
                return {'success': False, 'error': 'File not found'}
            
            if path.is_dir():
                # List directory contents
                items = [item.name for item in path.iterdir()]
                content = f"Directory contents:\n" + "\n".join(items)
                logger.info(f"[Agent {self.name}] read_file: Listed directory with {len(items)} items")
            else:
                # Read file
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()
                logger.info(f"[Agent {self.name}] read_file: Read {len(content)} bytes from {path}")
            
            result = {'success': True, 'content': content, 'path': str(path)}
            
            # Store in knowledge base
            if self.knowledge_base:
                self.knowledge_base.add_interaction(
                    agent_name=self.name,
                    interaction_type='file_operation',
                    content=f"Read file: {file_path}\nContent: {content[:500]}...",
                    metadata={'operation': 'read', 'path': file_path},
                    session_id=self.session_id
                )
            
            return result
        except Exception as e:
            error_msg = f"Error reading file: {str(e)}"
            if self.knowledge_base:
                self.knowledge_base.add_interaction(
                    agent_name=self.name,
                    interaction_type='file_operation',
                    content=f"Read file: {file_path}\nError: {error_msg}",
                    metadata={'error': str(e)},
                    session_id=self.session_id
                )
            return {'success': False, 'error': error_msg}
    
    def write_file(self, file_path: str, content: str) -> Dict[str, Any]:
        """Write to a file."""
        if content is None:
            return {'success': False, 'error': 'No content provided for write_file. The "content" parameter is required.'}
        logger.info(f"[Agent {self.name}] write_file called with path='{file_path}', content_length={len(content)}")
        try:
            # Convert to Path object
            path = Path(file_path)
            logger.debug(f"[Agent {self.name}] write_file: Original path: {path}, is_absolute: {path.is_absolute()}")
            
            # If path is relative and starts with agent_code, make it absolute
            if not path.is_absolute():
                # Get the workspace root (where the app.py file is located)
                workspace_root = Path(__file__).parent
                logger.debug(f"[Agent {self.name}] write_file: workspace_root={workspace_root}")
                
                # If path doesn't start with agent_code, prepend it
                if not str(path).startswith('agent_code'):
                    path = workspace_root / 'agent_code' / path
                    logger.debug(f"[Agent {self.name}] write_file: Prepended agent_code, new path={path}")
                else:
                    path = workspace_root / path
                    logger.debug(f"[Agent {self.name}] write_file: Path already has agent_code, new path={path}")
            
            # Check for file/directory conflicts
            if path.exists() and path.is_dir():
                error_msg = f"Cannot write file: '{path}' already exists as a directory. Use a different filename or add a file extension (e.g., '{path}.py')"
                logger.error(f"[Agent {self.name}] write_file: {error_msg}")
                return {'success': False, 'error': error_msg}
            
            # Check if any parent path component is a file (not a directory)
            for parent in path.parents:
                if parent.exists() and parent.is_file():
                    error_msg = f"Cannot create file: parent path '{parent}' is a file, not a directory. Remove the conflicting file or use a different path."
                    logger.error(f"[Agent {self.name}] write_file: {error_msg}")
                    return {'success': False, 'error': error_msg}
            
            # Ensure parent directory exists
            logger.debug(f"[Agent {self.name}] write_file: Creating parent directory: {path.parent}")
            path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write the file
            logger.info(f"[Agent {self.name}] write_file: Writing {len(content)} bytes to {path}")
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # Verify file was written
            if path.exists():
                actual_size = path.stat().st_size
                logger.info(f"[Agent {self.name}] write_file: SUCCESS - File written to {path} ({actual_size} bytes)")
            else:
                logger.error(f"[Agent {self.name}] write_file: File does not exist after write attempt: {path}")
            
            result = {'success': True, 'path': str(path), 'size': len(content)}
            
            # Store in knowledge base
            if self.knowledge_base:
                self.knowledge_base.add_interaction(
                    agent_name=self.name,
                    interaction_type='file_operation',
                    content=f"Write file: {file_path}\nActual path: {path}\nContent length: {len(content)} bytes",
                    metadata={'operation': 'write', 'path': file_path, 'actual_path': str(path), 'size': len(content)},
                    session_id=self.session_id
                )
            
            return result
        except Exception as e:
            error_msg = f"Error writing file: {str(e)}"
            logger.exception(f"[Agent {self.name}] write_file EXCEPTION: {error_msg}")
            if self.knowledge_base:
                self.knowledge_base.add_interaction(
                    agent_name=self.name,
                    interaction_type='file_operation',
                    content=f"Write file: {file_path}\nError: {error_msg}",
                    metadata={'error': str(e)},
                    session_id=self.session_id
                )
            return {'success': False, 'error': error_msg}
    
    def create_folder(self, folder_path: str) -> Dict[str, Any]:
        """Create a new folder/directory."""
        logger.info(f"[Agent {self.name}] create_folder called with path='{folder_path}'")
        try:
            if not folder_path:
                return {'success': False, 'error': 'Folder path cannot be empty'}
            
            path = Path(folder_path)
            logger.debug(f"[Agent {self.name}] create_folder: Original path: {path}, is_absolute: {path.is_absolute()}")
            
            # If path is relative, make it absolute within agent_code
            if not path.is_absolute():
                workspace_root = Path(__file__).parent
                logger.debug(f"[Agent {self.name}] create_folder: workspace_root={workspace_root}")
                
                if not str(path).startswith('agent_code'):
                    path = workspace_root / 'agent_code' / path
                    logger.debug(f"[Agent {self.name}] create_folder: Prepended agent_code, new path={path}")
                else:
                    path = workspace_root / path
                    logger.debug(f"[Agent {self.name}] create_folder: Path already has agent_code, new path={path}")
            
            # Check if path already exists as a file
            if path.exists() and path.is_file():
                error_msg = f"Cannot create folder: '{path}' already exists as a file"
                logger.error(f"[Agent {self.name}] create_folder: {error_msg}")
                return {'success': False, 'error': error_msg}
            
            # Check if any parent path component is a file
            for parent in path.parents:
                if parent.exists() and parent.is_file():
                    error_msg = f"Cannot create folder: parent path '{parent}' is a file, not a directory"
                    logger.error(f"[Agent {self.name}] create_folder: {error_msg}")
                    return {'success': False, 'error': error_msg}
            
            # Create the directory (and any parent directories)
            logger.info(f"[Agent {self.name}] create_folder: Creating directory: {path}")
            path.mkdir(parents=True, exist_ok=True)
            
            # Verify directory was created
            if path.exists() and path.is_dir():
                logger.info(f"[Agent {self.name}] create_folder: SUCCESS - Folder created at {path}")
            else:
                logger.error(f"[Agent {self.name}] create_folder: Folder does not exist after creation attempt: {path}")
            
            result = {'success': True, 'path': str(path)}
            
            # Store in knowledge base
            if self.knowledge_base:
                self.knowledge_base.add_interaction(
                    agent_name=self.name,
                    interaction_type='file_operation',
                    content=f"Create folder: {folder_path}\nActual path: {path}",
                    metadata={'operation': 'create_folder', 'path': folder_path, 'actual_path': str(path)},
                    session_id=self.session_id
                )
            
            return result
        except Exception as e:
            error_msg = f"Error creating folder: {str(e)}"
            logger.exception(f"[Agent {self.name}] create_folder EXCEPTION: {error_msg}")
            if self.knowledge_base:
                self.knowledge_base.add_interaction(
                    agent_name=self.name,
                    interaction_type='file_operation',
                    content=f"Create folder: {folder_path}\nError: {error_msg}",
                    metadata={'error': str(e)},
                    session_id=self.session_id
                )
            return {'success': False, 'error': error_msg}
    
    def list_directory(self, dir_path: str = ".") -> Dict[str, Any]:
        """List directory contents."""
        logger.info(f"[Agent {self.name}] list_directory called with path='{dir_path}'")
        try:
            path = Path(dir_path)
            logger.debug(f"[Agent {self.name}] list_directory: Checking path: {path}")
            
            if not path.exists():
                logger.warning(f"[Agent {self.name}] list_directory: Directory not found: {path}")
                return {'success': False, 'error': 'Directory not found'}
            
            if not path.is_dir():
                logger.warning(f"[Agent {self.name}] list_directory: Path is not a directory: {path}")
                return {'success': False, 'error': 'Path is not a directory'}
            
            items = []
            for item in path.iterdir():
                items.append({
                    'name': item.name,
                    'type': 'directory' if item.is_dir() else 'file',
                    'size': item.stat().st_size if item.is_file() else None
                })
            
            logger.info(f"[Agent {self.name}] list_directory: Found {len(items)} items in {path}")
            result = {'success': True, 'items': items, 'path': str(path)}
            
            # Store in knowledge base
            if self.knowledge_base:
                self.knowledge_base.add_interaction(
                    agent_name=self.name,
                    interaction_type='file_operation',
                    content=f"List directory: {dir_path}\nItems: {len(items)}",
                    metadata={'operation': 'list', 'path': dir_path, 'count': len(items)},
                    session_id=self.session_id
                )
            
            return result
        except Exception as e:
            error_msg = f"Error listing directory: {str(e)}"
            if self.knowledge_base:
                self.knowledge_base.add_interaction(
                    agent_name=self.name,
                    interaction_type='file_operation',
                    content=f"List directory: {dir_path}\nError: {error_msg}",
                    metadata={'error': str(e)},
                    session_id=self.session_id
                )
            return {'success': False, 'error': error_msg}
    
    def web_search(self, query: str, max_results: int = 5) -> Dict[str, Any]:
        """Search the web for information using DuckDuckGo.
        
        Args:
            query: Search query string
            max_results: Maximum number of results to return (default 5)
            
        Returns:
            Dict with success status and search results
        """
        import time
        import random
        
        logger.info(f"[Agent {self.name}] web_search called with query='{query}', max_results={max_results}")
        
        if not query or not query.strip():
            return {'success': False, 'error': 'Search query cannot be empty'}
        
        try:
            from duckduckgo_search import DDGS
            from duckduckgo_search.exceptions import RatelimitException
        except ImportError:
            error_msg = "DuckDuckGo search package not installed. Install with: pip install duckduckgo-search"
            logger.error(f"[Agent {self.name}] web_search: {error_msg}")
            return {'success': False, 'error': error_msg}
        
        # Retry logic with exponential backoff for rate limiting
        max_retries = 3
        base_delay = 2.0
        
        for attempt in range(max_retries):
            try:
                # Add a small random delay before each request to help avoid rate limits
                if attempt > 0:
                    delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                    logger.info(f"[Agent {self.name}] web_search: Retry {attempt + 1}/{max_retries}, waiting {delay:.1f}s")
                    time.sleep(delay)
                
                results = []
                with DDGS() as ddgs:
                    search_results = list(ddgs.text(query, max_results=max_results))
                    
                    for item in search_results:
                        results.append({
                            'title': item.get('title', ''),
                            'url': item.get('href', ''),
                            'snippet': item.get('body', '')
                        })
                
                logger.info(f"[Agent {self.name}] web_search: Found {len(results)} results for '{query}'")
                
                result = {
                    'success': True,
                    'query': query,
                    'results': results,
                    'count': len(results)
                }
                
                # Store in knowledge base
                if self.knowledge_base:
                    self.knowledge_base.add_interaction(
                        agent_name=self.name,
                        interaction_type='web_search',
                        content=f"Web search: {query}\nResults: {len(results)} found",
                        metadata={'query': query, 'result_count': len(results)},
                        session_id=self.session_id
                    )
                
                return result
                
            except RatelimitException as e:
                logger.warning(f"[Agent {self.name}] web_search: Rate limited (attempt {attempt + 1}/{max_retries})")
                if attempt == max_retries - 1:
                    error_msg = "DuckDuckGo rate limit exceeded. Please wait a few minutes before trying again."
                    logger.error(f"[Agent {self.name}] web_search: {error_msg}")
                    if self.knowledge_base:
                        self.knowledge_base.add_interaction(
                            agent_name=self.name,
                            interaction_type='web_search',
                            content=f"Web search: {query}\nError: Rate limited",
                            metadata={'error': 'rate_limit'},
                            session_id=self.session_id
                        )
                    return {'success': False, 'error': error_msg}
                # Continue to next retry attempt
                
            except Exception as e:
                error_str = str(e)
                # Check if this is a rate limit error that wasn't caught by RatelimitException
                if 'Ratelimit' in error_str or '202' in error_str:
                    logger.warning(f"[Agent {self.name}] web_search: Rate limited (attempt {attempt + 1}/{max_retries})")
                    if attempt == max_retries - 1:
                        error_msg = "DuckDuckGo rate limit exceeded. Please wait a few minutes before trying again."
                        logger.error(f"[Agent {self.name}] web_search: {error_msg}")
                        if self.knowledge_base:
                            self.knowledge_base.add_interaction(
                                agent_name=self.name,
                                interaction_type='web_search',
                                content=f"Web search: {query}\nError: Rate limited",
                                metadata={'error': 'rate_limit'},
                                session_id=self.session_id
                            )
                        return {'success': False, 'error': error_msg}
                    # Continue to next retry attempt
                else:
                    # Non-rate-limit error, don't retry
                    error_msg = f"Error performing web search: {error_str}"
                    logger.exception(f"[Agent {self.name}] web_search EXCEPTION: {error_msg}")
                    if self.knowledge_base:
                        self.knowledge_base.add_interaction(
                            agent_name=self.name,
                            interaction_type='web_search',
                            content=f"Web search: {query}\nError: {error_msg}",
                            metadata={'error': str(e)},
                            session_id=self.session_id
                        )
                    return {'success': False, 'error': error_msg}
        
        # Should not reach here, but just in case
        return {'success': False, 'error': 'Search failed after all retries'}
    
    def send_message_to_agent(self, receiver_name: str, message: str) -> bool:
        """Send a message to another agent."""
        if not self.message_bus:
            return False
        
        return self.message_bus.send_message(
            sender_name=self.name,
            receiver_name=receiver_name,
            message_content=message
        )
    
    def respond_to_agent_message(self, sender_name: str, message_content: str, objective: str = None) -> str:
        """Respond to a message from another agent."""
        # Build context-aware prompt with semantic search
        context = self._get_context(query=message_content)
        
        # Create a prompt that includes the message from the other agent
        if objective:
            agent_message_prompt = f"""Collaborating with '{sender_name}' on: {objective}

Message from {sender_name}: {message_content}

Take ACTION to advance the objective:
- If {sender_name} proposed code, use write_file to implement it
- If there's a bug, use write_file to fix it
- Build on their work with concrete file operations

Don't just discuss - execute tools to make real progress."""
        else:
            agent_message_prompt = f"""Message from '{sender_name}': {message_content}

Respond helpfully and take action using your tools if appropriate."""
        
        if context:
            full_prompt = f"{context}\n\n{agent_message_prompt}"
        else:
            full_prompt = agent_message_prompt
        
        messages = self.conversation_history + [{
            'role': 'user',
            'content': full_prompt
        }]
        
        temperature = self.settings.get('temperature', 0.7)
        max_tokens = self.settings.get('max_tokens', 2048)
        
        try:
            response = self.client.chat(
                self.model,
                messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            # Update conversation history
            self.conversation_history.append({
                'role': 'user',
                'content': f"Message from {sender_name}: {message_content}"
            })
            self.conversation_history.append({
                'role': 'assistant',
                'content': response
            })
            
            # Store in knowledge base
            if self.knowledge_base:
                self.knowledge_base.add_interaction(
                    agent_name=self.name,
                    interaction_type='agent_chat',
                    content=f"Received from {sender_name}: {message_content}\nResponse: {response}",
                    metadata={'sender': sender_name, 'response': response},
                    related_agent=sender_name,
                    session_id=self.session_id
                )
            
            return response
        except Exception as e:
            error_msg = f"Error responding to message: {str(e)}"
            if self.knowledge_base:
                self.knowledge_base.add_interaction(
                    agent_name=self.name,
                    interaction_type='agent_chat',
                    content=f"Error responding to {sender_name}: {error_msg}",
                    metadata={'error': str(e), 'sender': sender_name},
                    session_id=self.session_id
                )
            return error_msg
    
    def get_info(self) -> Dict[str, Any]:
        """Get agent information."""
        return {
            'name': self.name,
            'model': self.model,
            'system_prompt': self.system_prompt,
            'conversation_length': len(self.conversation_history),
            'settings': self.settings,
            'allowed_tools': self.allowed_tools,
            'avatar_seed': self.avatar_seed,
            'session_id': self.session_id
        }

