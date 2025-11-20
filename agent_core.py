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
    
    def __init__(
        self,
        name: str,
        model: str,
        system_prompt: str = "",
        settings: Optional[Dict[str, Any]] = None,
        knowledge_base=None,
        message_bus=None
    ):
        """Initialize enhanced agent."""
        self.name = name
        self.model = model
        self.system_prompt = system_prompt
        self.settings = settings or {}
        self.knowledge_base = knowledge_base
        self.message_bus = message_bus
        
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
    
    def _get_context(self) -> str:
        """Get context from knowledge base and pending messages."""
        context_parts = []
        
        # Add shared knowledge summary
        if self.knowledge_base:
            shared_knowledge = self.knowledge_base.get_shared_knowledge_summary(limit=20)
            if shared_knowledge:
                context_parts.append(f"Shared Knowledge:\n{shared_knowledge}")
        
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
        """Chat with the agent."""
        # Get context from knowledge base
        context = self._get_context()
        
        # Build prompt with context
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
                'content': user_message
            })
            self.conversation_history.append({
                'role': 'assistant',
                'content': response
            })
            
            # Store in knowledge base
            if self.knowledge_base:
                self.knowledge_base.add_interaction(
                    agent_name=self.name,
                    interaction_type='user_chat',
                    content=f"User: {user_message}\nAgent: {response}",
                    metadata={'user_message': user_message, 'agent_response': response}
                )
            
            return response
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
    
    def execute_task(self, task: str) -> str:
        """Execute a single task."""
        context = self._get_context()
        
        task_prompt = f"""Execute the following task: {task}

{context if context else ''}

Please:
1. Explain what you will do
2. Execute the task step by step
3. Provide a summary of what was accomplished
4. Note any issues or considerations

If this task requires actions that cannot be performed directly, describe what should be done instead."""

        messages = self.conversation_history + [{
            'role': 'user',
            'content': task_prompt
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
                'content': task_prompt
            })
            self.conversation_history.append({
                'role': 'assistant',
                'content': response
            })
            
            # Store in knowledge base
            if self.knowledge_base:
                self.knowledge_base.add_interaction(
                    agent_name=self.name,
                    interaction_type='task_execution',
                    content=f"Task: {task}\nResult: {response}",
                    metadata={'task': task, 'result': response}
                )
            
            return response
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
            path = Path(file_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            result = {'success': True, 'path': str(path), 'size': len(content)}
            
            # Store in knowledge base
            if self.knowledge_base:
                self.knowledge_base.add_interaction(
                    agent_name=self.name,
                    interaction_type='file_operation',
                    content=f"Write file: {file_path}\nContent length: {len(content)} bytes",
                    metadata={'operation': 'write', 'path': file_path, 'size': len(content)}
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
    
    def get_info(self) -> Dict[str, Any]:
        """Get agent information."""
        return {
            'name': self.name,
            'model': self.model,
            'system_prompt': self.system_prompt[:100] + '...' if len(self.system_prompt) > 100 else self.system_prompt,
            'conversation_length': len(self.conversation_history),
            'settings': self.settings
        }

