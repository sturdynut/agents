#!/usr/bin/env python3
"""
Local Ollama Agent System

An agent that uses Ollama to run locally downloaded models,
accepts a system prompt and task list from a config file,
and can both plan and execute tasks sequentially.
"""

import argparse
import json
import os
import sys
from typing import Dict, List, Any, Optional
import yaml

try:
    import ollama
except ImportError:
    print("Error: ollama package not found. Install it with: pip install ollama")
    sys.exit(1)


class ConfigLoader:
    """Loads configuration from YAML or JSON files."""
    
    @staticmethod
    def load(config_path: str) -> Dict[str, Any]:
        """Load configuration from YAML or JSON file."""
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Config file not found: {config_path}")
        
        with open(config_path, 'r', encoding='utf-8') as f:
            if config_path.endswith('.yaml') or config_path.endswith('.yml'):
                return yaml.safe_load(f)
            elif config_path.endswith('.json'):
                return json.load(f)
            else:
                # Try to detect format
                content = f.read()
                f.seek(0)
                try:
                    return yaml.safe_load(f)
                except:
                    return json.loads(content)


class OllamaClient:
    """Client for interacting with Ollama API."""
    
    def __init__(self, api_endpoint: str = "http://localhost:11434"):
        """Initialize Ollama client."""
        self.api_endpoint = api_endpoint
        # Set the base URL for ollama client if needed
        if api_endpoint != "http://localhost:11434":
            # ollama library uses environment variable or default endpoint
            os.environ['OLLAMA_HOST'] = api_endpoint.replace('http://', '').replace('https://', '')
    
    def chat(self, model: str, messages: List[Dict[str, str]], 
             temperature: float = 0.7, max_tokens: int = 2048) -> str:
        """Send chat request to Ollama model."""
        try:
            response = ollama.chat(
                model=model,
                messages=messages,
                options={
                    'temperature': temperature,
                    'num_predict': max_tokens
                }
            )
            return response['message']['content']
        except Exception as e:
            raise Exception(f"Failed to communicate with Ollama: {str(e)}")
    
    def check_model(self, model: str) -> bool:
        """Check if model is available."""
        try:
            models = ollama.list()
            available_models = [m['name'] for m in models.get('models', [])]
            return model in available_models
        except Exception as e:
            print(f"Warning: Could not check model availability: {str(e)}")
            return True  # Assume available if check fails


class TaskAgent:
    """Agent that plans and executes tasks using Ollama."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize agent with configuration."""
        self.config = config
        self.model = config.get('model', 'llama3.2')
        self.system_prompt = config.get('system_prompt', '')
        self.tasks = config.get('tasks', [])
        self.settings = config.get('settings', {})
        
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
    
    def plan_tasks(self) -> Dict[str, Any]:
        """Plan the execution of tasks."""
        print("\n" + "="*60)
        print("PLANNING PHASE")
        print("="*60)
        
        # Handle empty tasks
        if not self.tasks:
            print("\nNo tasks to plan. Task list is empty.")
            return {
                'plan': 'No tasks to plan.',
                'tasks': []
            }
        
        planning_prompt = f"""You are a task planning assistant. Analyze the following list of tasks and create an execution plan.

Tasks to plan:
{chr(10).join(f"{i+1}. {task}" for i, task in enumerate(self.tasks))}

Please provide:
1. A breakdown of each task into subtasks or steps
2. Any dependencies between tasks
3. An optimal execution order
4. Potential challenges or considerations

Format your response clearly with numbered steps and explanations."""

        messages = self.conversation_history + [{
            'role': 'user',
            'content': planning_prompt
        }]
        
        print(f"\nAnalyzing {len(self.tasks)} task(s)...")
        print(f"Tasks: {', '.join(self.tasks[:3])}{'...' if len(self.tasks) > 3 else ''}\n")
        
        temperature = self.settings.get('temperature', 0.7)
        max_tokens = self.settings.get('max_tokens', 2048)
        
        plan_response = self.client.chat(
            self.model,
            messages,
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        print("Plan generated:")
        print("-" * 60)
        print(plan_response)
        print("-" * 60)
        
        # Store planning in history
        self.conversation_history.append({
            'role': 'user',
            'content': planning_prompt
        })
        self.conversation_history.append({
            'role': 'assistant',
            'content': plan_response
        })
        
        return {
            'plan': plan_response,
            'tasks': self.tasks
        }
    
    def execute_tasks(self, plan: Optional[Dict[str, Any]] = None):
        """Execute tasks sequentially."""
        print("\n" + "="*60)
        print("EXECUTION PHASE")
        print("="*60)
        
        # Handle empty tasks
        if not self.tasks:
            print("\nNo tasks to execute. Task list is empty.")
            print(f"{'='*60}\n")
            return
        
        execution_context = ""
        if plan:
            execution_context = f"\n\nExecution Plan:\n{plan.get('plan', '')}"
        
        for i, task in enumerate(self.tasks, 1):
            print(f"\n{'='*60}")
            print(f"TASK {i}/{len(self.tasks)}: {task}")
            print(f"{'='*60}")
            
            execution_prompt = f"""Execute the following task: {task}

{execution_context}

Previous tasks completed: {i-1}/{len(self.tasks)}

Please:
1. Explain what you will do for this task
2. Execute the task step by step
3. Provide a summary of what was accomplished
4. Note any issues or considerations

If this task requires actions that cannot be performed (like file operations, API calls, etc.), describe what should be done instead."""

            messages = self.conversation_history + [{
                'role': 'user',
                'content': execution_prompt
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
                
                print("\nExecution Result:")
                print("-" * 60)
                print(response)
                print("-" * 60)
                
                # Update conversation history
                self.conversation_history.append({
                    'role': 'user',
                    'content': execution_prompt
                })
                self.conversation_history.append({
                    'role': 'assistant',
                    'content': response
                })
                
                # Update execution context for next task
                execution_context += f"\n\nTask {i} ({task}) completed:\n{response}"
                
            except Exception as e:
                print(f"\nError executing task: {str(e)}")
                print("Continuing with next task...")
        
        print(f"\n{'='*60}")
        print("ALL TASKS COMPLETED")
        print(f"{'='*60}\n")
    
    def run(self):
        """Run the full agent workflow: plan then execute."""
        # Check if model is available
        print(f"Checking model availability: {self.model}")
        if not self.client.check_model(self.model):
            print(f"Warning: Model '{self.model}' may not be available.")
            print(f"Make sure you have downloaded it with: ollama pull {self.model}")
            response = input("Continue anyway? (y/n): ")
            if response.lower() != 'y':
                print("Exiting.")
                return
        
        # Plan tasks
        plan = self.plan_tasks()
        
        # Execute tasks
        self.execute_tasks(plan)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Local Ollama Agent - Plan and execute tasks using local LLM models'
    )
    parser.add_argument(
        'config',
        nargs='?',
        default='config.yaml',
        help='Path to configuration file (YAML or JSON). Default: config.yaml'
    )
    
    args = parser.parse_args()
    
    try:
        # Load configuration
        print(f"Loading configuration from: {args.config}")
        config = ConfigLoader.load(args.config)
        
        # Validate required fields
        if 'model' not in config:
            raise ValueError("Configuration must include 'model' field")
        if 'tasks' not in config:
            raise ValueError("Configuration must include 'tasks' field")
        
        # Warn if tasks list is empty
        tasks = config.get('tasks', [])
        if not tasks:
            print("Warning: Task list is empty. Agent will skip planning and execution.")
        
        # Create and run agent
        agent = TaskAgent(config)
        agent.run()
        
    except FileNotFoundError as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"Configuration Error: {str(e)}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\nInterrupted by user. Exiting.")
        sys.exit(0)
    except Exception as e:
        print(f"Unexpected error: {str(e)}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()

