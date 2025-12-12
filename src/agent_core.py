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
        avatar_seed: Optional[str] = None
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
        """
        self.name = name
        self.model = model
        self.system_prompt = system_prompt
        self.settings = settings or {}
        self.knowledge_base = knowledge_base
        self.message_bus = message_bus
        self.avatar_seed = avatar_seed or name  # Default to agent name
        
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
    
    def receive_message(self, sender_name: str, message_content: str):
        """Receive a message from another agent."""
        self.pending_messages.append({
            'sender': sender_name,
            'content': message_content,
            'timestamp': datetime.utcnow().isoformat()
        })
    
    def _get_tools_info(self) -> str:
        """Generate tools information based on allowed tools.
        
        Returns:
            Formatted string describing available tools
        """
        if not self.allowed_tools:
            return "Note: No tools are available for this agent."
        
        tools_lines = ["Available Tools (use when needed):"]
        
        if 'write_file' in self.allowed_tools:
            tools_lines.append('- write_file: <TOOL_CALL tool="write_file">{"path": "filename.ext", "content": "file content"}</TOOL_CALL>')
        
        if 'read_file' in self.allowed_tools:
            tools_lines.append('- read_file: <TOOL_CALL tool="read_file">{"path": "agent_code/filename.ext"}</TOOL_CALL>')
        
        if 'list_directory' in self.allowed_tools:
            tools_lines.append('- list_directory: <TOOL_CALL tool="list_directory">{"path": "agent_code"}</TOOL_CALL>')
        
        if 'web_search' in self.allowed_tools:
            tools_lines.append('- web_search: <TOOL_CALL tool="web_search">{"query": "search terms", "max_results": 5}</TOOL_CALL>')
        
        if 'write_file' in self.allowed_tools:
            tools_lines.append("\nIMPORTANT: When writing files, just use the filename (e.g., \"script.py\"). The system will automatically save it to the agent_code folder.")
            tools_lines.append("If you need to organize files in subdirectories, use paths like \"utils/helper.py\" and they will be created in agent_code/utils/.")
        
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
        if self.knowledge_base and query:
            try:
                relevant_interactions = self.knowledge_base.semantic_search_interactions(
                    query=query,
                    agent_name=self.name,
                    top_k=10,
                    time_decay_factor=0.95
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
                # Fallback to recent interactions
                agent_knowledge = self.knowledge_base.get_agent_knowledge_summary(agent_name=self.name, limit=10)
                if agent_knowledge:
                    context_parts.append(f"Recent Interactions:\n{agent_knowledge}")
        
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
        """Chat with the agent with tool calling support."""
        logger.info(f"[Agent {self.name}] chat() called with message: '{user_message[:100]}...'")
        logger.debug(f"[Agent {self.name}] Allowed tools: {self.allowed_tools}")
        
        # Get context from knowledge base using semantic search
        context = self._get_context(query=user_message)
        
        # Build tools information based on allowed tools
        tools_info = self._get_tools_info()
        
        # Build prompt with context
        if context:
            full_prompt = f"{context}\n\n{tools_info}\n\nUser: {user_message}"
        else:
            full_prompt = f"{tools_info}\n\nUser: {user_message}"
        
        messages = self.conversation_history + [{
            'role': 'user',
            'content': full_prompt
        }]
        
        temperature = self.settings.get('temperature', 0.7)
        max_tokens = self.settings.get('max_tokens', 2048)
        
        logger.debug(f"[Agent {self.name}] Calling Ollama model '{self.model}' with {len(messages)} messages")
        
        try:
            response = self.client.chat(
                self.model,
                messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            logger.info(f"[Agent {self.name}] Got response from LLM, length={len(response)} chars")
            logger.debug(f"[Agent {self.name}] LLM response preview: {response[:200]}...")
            
            # Parse and execute tool calls
            modified_response, tool_results = self._parse_and_execute_tools(response)
            
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
                modified_response += tool_feedback
            
            # Update conversation history
            self.conversation_history.append({
                'role': 'user',
                'content': user_message
            })
            self.conversation_history.append({
                'role': 'assistant',
                'content': modified_response
            })
            
            # Store in knowledge base
            if self.knowledge_base:
                self.knowledge_base.add_interaction(
                    agent_name=self.name,
                    interaction_type='user_chat',
                    content=f"User: {user_message}\nAgent: {modified_response}",
                    metadata={'user_message': user_message, 'agent_response': modified_response, 'tools_used': len(tool_results) > 0}
                )
            
            return modified_response
        except Exception as e:
            error_msg = f"Error: {str(e)}"
            if self.knowledge_base:
                self.knowledge_base.add_interaction(
                    agent_name=self.name,
                    interaction_type='user_chat',
                    content=f"User: {user_message}\nError: {error_msg}",
                    metadata={'error': str(e)}
                )
            return error_msg
    
    def _parse_and_execute_tools(self, response: str) -> tuple[str, List[Dict[str, Any]]]:
        """Parse tool calls from agent response and execute them.
        
        Returns:
            Tuple of (modified_response, tool_results)
        """
        import re
        
        tool_results = []
        modified_response = response
        
        # Pattern to match tool calls: <TOOL_CALL tool="name">params</TOOL_CALL>
        # Also handle common variations with extra braces
        tool_pattern = r'<TOOL_CALL tool="([^"]+)">\s*(\{.*?\})\s*(?:</TOOL_CALL>|\}+)'
        matches = re.findall(tool_pattern, response, re.DOTALL)
        
        logger.info(f"[Agent {self.name}] Parsing response for tool calls, found {len(matches)} tool call(s)")
        if matches:
            logger.debug(f"[Agent {self.name}] Raw response excerpt: {response[:500]}...")
        
        for tool_name, params_str in matches:
            logger.info(f"[Agent {self.name}] Executing tool: {tool_name}")
            logger.debug(f"[Agent {self.name}] Tool params (raw): {params_str}")
            
            try:
                # Parse parameters (expect JSON format)
                params = json.loads(params_str.strip())
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
        """Execute a single task with tool calling support."""
        # Get semantically relevant context
        context = self._get_context(query=task)
        
        # Build task prompt with tool calling instructions based on allowed tools
        tools_info = self._get_tools_info()
        
        task_prompt = f"""Execute: {task}

{context if context else ''}

{tools_info}

Be concise. State your approach, execute using available tools if needed, and summarize results. Note issues only if critical."""

        max_iterations = 3  # Allow agent to use tools iteratively
        iteration = 0
        accumulated_response = ""
        
        while iteration < max_iterations:
            messages = self.conversation_history + [{
                'role': 'user',
                'content': task_prompt if iteration == 0 else f"Continue with task: {task}\n\nPrevious actions: {accumulated_response}"
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
                
                # Parse and execute tool calls
                modified_response, tool_results = self._parse_and_execute_tools(response)
                
                # If no tools were called, we're done
                if not tool_results:
                    accumulated_response += modified_response
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
                
                accumulated_response += modified_response + tool_feedback
                task_prompt = tool_feedback  # Feed results back for next iteration
                
                iteration += 1
                
            except Exception as e:
                error_msg = f"Error executing task: {str(e)}"
                if self.knowledge_base:
                    self.knowledge_base.add_interaction(
                        agent_name=self.name,
                        interaction_type='task_execution',
                        content=f"Task: {task}\nError: {error_msg}",
                        metadata={'error': str(e)}
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
                metadata={'task': task, 'result': accumulated_response}
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
                    metadata={'operation': 'read', 'path': file_path}
                )
            
            return result
        except Exception as e:
            error_msg = f"Error reading file: {str(e)}"
            if self.knowledge_base:
                self.knowledge_base.add_interaction(
                    agent_name=self.name,
                    interaction_type='file_operation',
                    content=f"Read file: {file_path}\nError: {error_msg}",
                    metadata={'error': str(e)}
                )
            return {'success': False, 'error': error_msg}
    
    def write_file(self, file_path: str, content: str) -> Dict[str, Any]:
        """Write to a file."""
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
                    metadata={'operation': 'write', 'path': file_path, 'actual_path': str(path), 'size': len(content)}
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
                    metadata={'error': str(e)}
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
                    metadata={'operation': 'list', 'path': dir_path, 'count': len(items)}
                )
            
            return result
        except Exception as e:
            error_msg = f"Error listing directory: {str(e)}"
            if self.knowledge_base:
                self.knowledge_base.add_interaction(
                    agent_name=self.name,
                    interaction_type='file_operation',
                    content=f"List directory: {dir_path}\nError: {error_msg}",
                    metadata={'error': str(e)}
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
        logger.info(f"[Agent {self.name}] web_search called with query='{query}', max_results={max_results}")
        
        if not query or not query.strip():
            return {'success': False, 'error': 'Search query cannot be empty'}
        
        try:
            from duckduckgo_search import DDGS
            
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
                    metadata={'query': query, 'result_count': len(results)}
                )
            
            return result
            
        except ImportError:
            error_msg = "DuckDuckGo search package not installed. Install with: pip install duckduckgo-search"
            logger.error(f"[Agent {self.name}] web_search: {error_msg}")
            return {'success': False, 'error': error_msg}
        except Exception as e:
            error_msg = f"Error performing web search: {str(e)}"
            logger.exception(f"[Agent {self.name}] web_search EXCEPTION: {error_msg}")
            if self.knowledge_base:
                self.knowledge_base.add_interaction(
                    agent_name=self.name,
                    interaction_type='web_search',
                    content=f"Web search: {query}\nError: {error_msg}",
                    metadata={'error': str(e)}
                )
            return {'success': False, 'error': error_msg}
    
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

Respond concisely, building on progress toward the objective."""
        else:
            agent_message_prompt = f"""Message from '{sender_name}': {message_content}

Respond concisely and helpfully."""
        
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
                    related_agent=sender_name
                )
            
            return response
        except Exception as e:
            error_msg = f"Error responding to message: {str(e)}"
            if self.knowledge_base:
                self.knowledge_base.add_interaction(
                    agent_name=self.name,
                    interaction_type='agent_chat',
                    content=f"Error responding to {sender_name}: {error_msg}",
                    metadata={'error': str(e), 'sender': sender_name}
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
            'avatar_seed': self.avatar_seed
        }

