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
import json
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path

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


class EnhancedAgent:
    """Enhanced agent with file operations, knowledge base, and messaging."""
    
    # Define all available tools
    AVAILABLE_TOOLS = {
        'write_file': 'Write content to a file',
        'read_file': 'Read a file\'s contents',
        'list_directory': 'List directory contents'
    }
    
    def __init__(
        self,
        name: str,
        model: str,
        system_prompt: str = "",
        settings: Optional[Dict[str, Any]] = None,
        knowledge_base=None,
        message_bus=None,
        tools: Optional[List[str]] = None
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
        """
        self.name = name
        self.model = model
        self.system_prompt = system_prompt
        self.settings = settings or {}
        self.knowledge_base = knowledge_base
        self.message_bus = message_bus
        
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
        
        if 'write_file' in self.allowed_tools:
            tools_lines.append("\nIMPORTANT: When writing files, just use the filename (e.g., \"script.py\"). The system will automatically save it to the agent_code folder.")
            tools_lines.append("If you need to organize files in subdirectories, use paths like \"utils/helper.py\" and they will be created in agent_code/utils/.")
        
        return "\n".join(tools_lines)
    
    def _get_context(self, query: str = "") -> str:
        """Get context from knowledge base using semantic search.
        
        Args:
            query: Current user message or task for semantic retrieval
            
        Returns:
            Formatted context string
        """
        context_parts = []
        
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
        
        try:
            response = self.client.chat(
                self.model,
                messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            # Parse and execute tool calls
            modified_response, tool_results = self._parse_and_execute_tools(response)
            
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
        
        for tool_name, params_str in matches:
            try:
                # Parse parameters (expect JSON format)
                params = json.loads(params_str.strip())
                
                # Check if tool is allowed
                if tool_name not in self.allowed_tools:
                    result = {
                        'success': False, 
                        'error': f'Access denied: Tool "{tool_name}" is not available for this agent. Available tools: {", ".join(self.allowed_tools)}'
                    }
                # Execute tool
                elif tool_name == 'write_file':
                    result = self.write_file(
                        params.get('path', ''),
                        params.get('content', '')
                    )
                elif tool_name == 'read_file':
                    result = self.read_file(params.get('path', ''))
                elif tool_name == 'list_directory':
                    result = self.list_directory(params.get('path', '.'))
                else:
                    result = {'success': False, 'error': f'Unknown tool: {tool_name}'}
                
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
                tool_results.append({
                    'tool': tool_name,
                    'params': params_str,
                    'result': {'success': False, 'error': f'Invalid JSON parameters: {str(e)}'}
                })
            except Exception as e:
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
        try:
            path = Path(file_path)
            if not path.exists():
                return {'success': False, 'error': 'File not found'}
            
            if path.is_dir():
                # List directory contents
                items = [item.name for item in path.iterdir()]
                content = f"Directory contents:\n" + "\n".join(items)
            else:
                # Read file
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()
            
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
        try:
            # Convert to Path object
            path = Path(file_path)
            
            # If path is relative and starts with agent_code, make it absolute
            if not path.is_absolute():
                # Get the workspace root (where the app.py file is located)
                workspace_root = Path(__file__).parent
                
                # If path doesn't start with agent_code, prepend it
                if not str(path).startswith('agent_code'):
                    path = workspace_root / 'agent_code' / path
                else:
                    path = workspace_root / path
            
            # Ensure parent directory exists
            path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write the file
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
            
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
        try:
            path = Path(dir_path)
            if not path.exists():
                return {'success': False, 'error': 'Directory not found'}
            
            if not path.is_dir():
                return {'success': False, 'error': 'Path is not a directory'}
            
            items = []
            for item in path.iterdir():
                items.append({
                    'name': item.name,
                    'type': 'directory' if item.is_dir() else 'file',
                    'size': item.stat().st_size if item.is_file() else None
                })
            
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
            'allowed_tools': self.allowed_tools
        }

