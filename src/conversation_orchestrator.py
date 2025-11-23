#!/usr/bin/env python3
"""
Conversation Orchestrator Module

Intelligently routes conversations between agents by:
1. Analyzing initial instructions to select the best starting agent
2. Analyzing responses to determine the next agent to route to
3. Managing conversation flow and context
"""

import json
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
from .agent_core import EnhancedAgent, OllamaClient
from .knowledge_base import KnowledgeBase
from .message_bus import MessageBus


class ConversationOrchestrator:
    """Orchestrates conversations between multiple agents."""
    
    def __init__(
        self,
        agent_manager,
        knowledge_base: KnowledgeBase,
        message_bus: MessageBus,
        orchestrator_model: str = "llama3.2",
        orchestrator_settings: Optional[Dict[str, Any]] = None
    ):
        """Initialize the conversation orchestrator."""
        self.agent_manager = agent_manager
        self.knowledge_base = knowledge_base
        self.message_bus = message_bus
        self.orchestrator_model = orchestrator_model
        self.orchestrator_settings = orchestrator_settings or {}
        
        # Initialize orchestrator's LLM client
        api_endpoint = self.orchestrator_settings.get('api_endpoint', 'http://localhost:11434')
        self.client = OllamaClient(api_endpoint)
        
        # Conversation state
        self.active_conversations: Dict[str, Dict[str, Any]] = {}
    
    def _get_agent_descriptions(self) -> str:
        """Get descriptions of all available agents."""
        agents = self.agent_manager.list_agents()
        descriptions = []
        for agent in agents:
            desc = f"- {agent['name']}: {agent.get('system_prompt', 'No description')[:200]}"
            if agent.get('model'):
                desc += f" (Model: {agent['model']})"
            descriptions.append(desc)
        return "\n".join(descriptions)
    
    def _select_initial_agent(self, objective: str, available_agents: List[str]) -> str:
        """Select the best agent to start the conversation based on the objective."""
        agent_descriptions = self._get_agent_descriptions()
        
        prompt = f"""Select the best agent to start this objective.

Available agents:
{agent_descriptions}

Objective: {objective}

Respond with ONLY the agent name. Default: {available_agents[0] if available_agents else 'None'}"""
        
        try:
            messages = [{'role': 'user', 'content': prompt}]
            response = self.client.chat(
                self.orchestrator_model,
                messages,
                temperature=0.3,  # Lower temperature for more deterministic routing
                max_tokens=100
            )
            
            # Extract agent name from response
            response = response.strip()
            # Remove any quotes or extra text
            response = response.replace('"', '').replace("'", '').strip()
            
            # Check if response is a valid agent name
            for agent_name in available_agents:
                if agent_name.lower() == response.lower() or response.lower() in agent_name.lower():
                    return agent_name
            
            # Fallback to first agent if no match
            return available_agents[0] if available_agents else None
            
        except Exception as e:
            print(f"[Orchestrator] Error selecting initial agent: {e}")
            # Fallback to first agent
            return available_agents[0] if available_agents else None
    
    def _select_next_agent(
        self,
        objective: str,
        conversation_history: List[Dict[str, str]],
        current_agent: str,
        current_response: str,
        available_agents: List[str]
    ) -> Optional[str]:
        """Select the next agent to route the conversation to based on the response."""
        if len(available_agents) < 2:
            return None  # No other agents to route to
        
        agent_descriptions = self._get_agent_descriptions()
        
        # Build conversation summary
        conversation_summary = "\n".join([
            f"{msg['sender']}: {msg['message'][:300]}..."
            for msg in conversation_history[-5:]  # Last 5 messages
        ])
        
        prompt = f"""Select next agent or END if complete.

Available agents:
{agent_descriptions}

Objective: {objective}

Recent conversation:
{conversation_summary}

{current_agent} just responded:
{current_response[:500]}

Respond with agent name, "{current_agent}" to continue, or "END"."""
        
        try:
            messages = [{'role': 'user', 'content': prompt}]
            response = self.client.chat(
                self.orchestrator_model,
                messages,
                temperature=0.3,  # Lower temperature for more deterministic routing
                max_tokens=100
            )
            
            response = response.strip().replace('"', '').replace("'", '').strip()
            
            # Check for END
            if "end" in response.lower():
                return None
            
            # Check if response matches an available agent
            for agent_name in available_agents:
                if agent_name.lower() == response.lower() or response.lower() in agent_name.lower():
                    return agent_name
            
            # If current agent should continue
            if current_agent.lower() in response.lower():
                return current_agent
            
            # Fallback: route to a different agent (round-robin style)
            current_idx = available_agents.index(current_agent) if current_agent in available_agents else 0
            next_idx = (current_idx + 1) % len(available_agents)
            return available_agents[next_idx]
            
        except Exception as e:
            print(f"[Orchestrator] Error selecting next agent: {e}")
            # Fallback: round-robin
            current_idx = available_agents.index(current_agent) if current_agent in available_agents else 0
            next_idx = (current_idx + 1) % len(available_agents)
            return available_agents[next_idx]
    
    def start_orchestrated_conversation(
        self,
        objective: str,
        max_turns: int = 20,
        conversation_id: Optional[str] = None,
        progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
        agent_names: Optional[List[str]] = None,
        resume_session_id: Optional[str] = None,
        conversation_mode: str = 'intelligent'  # 'intelligent' or 'round_robin'
    ) -> Dict[str, Any]:
        """Start an orchestrated conversation with intelligent routing."""
        # If resuming, load existing session
        if resume_session_id:
            session = self.knowledge_base.get_session(resume_session_id)
            if not session:
                raise ValueError(f"Session {resume_session_id} not found")
            
            conversation_id = resume_session_id
            objective = session['objective']
            agent_names = session['agent_names']
            conversation_history = session['conversation_history']
            current_agent_name = session['current_agent'] or session['agent_names'][0]
            
            # Extract routing mode from stored conversation_mode (e.g., 'orchestrated_round_robin')
            stored_mode = session.get('conversation_mode', 'orchestrated_intelligent')
            if '_' in stored_mode:
                conversation_mode = stored_mode.split('_', 1)[1]  # Get 'round_robin' or 'intelligent'
            
            print(f"[Orchestrator] Resuming session '{conversation_id}' with {len(conversation_history)} existing messages")
        else:
            # Get selected agents or all agents if none specified
            if agent_names:
                # Validate that all requested agents exist
                all_agents = self.agent_manager.list_agents()
                all_agent_names = [agent['name'] for agent in all_agents]
                valid_agent_names = [name for name in agent_names if name in all_agent_names]
                
                if len(valid_agent_names) != len(agent_names):
                    invalid_names = set(agent_names) - set(valid_agent_names)
                    raise ValueError(f"Invalid agent names: {', '.join(invalid_names)}")
                
                agent_names = valid_agent_names
            else:
                # Get all available agents if none specified
                all_agents = self.agent_manager.list_agents()
                if len(all_agents) < 1:
                    raise ValueError("At least 1 agent is required for orchestrated conversation")
                agent_names = [agent['name'] for agent in all_agents]
            
            # Generate conversation ID if not provided
            if not conversation_id:
                conversation_id = f"conv_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
            
            # Select initial agent
            current_agent_name = self._select_initial_agent(objective, agent_names)
            if not current_agent_name:
                raise ValueError("Could not select initial agent")
            
            conversation_history = []
            print(f"[Orchestrator] Starting conversation '{conversation_id}' with objective: {objective}")
            print(f"[Orchestrator] Selected initial agent: {current_agent_name}")
        
        # Initialize conversation state
        conversation_state = {
            'conversation_id': conversation_id,
            'objective': objective,
            'history': conversation_history,
            'current_agent': current_agent_name,
            'turn': len(conversation_history),
            'max_turns': max_turns,
            'agents_used': set([current_agent_name] + [msg.get('sender') for msg in conversation_history]),
            'started_at': datetime.utcnow().isoformat()
        }
        
        self.active_conversations[conversation_id] = conversation_state
        
        # Get agent instances
        agents = {}
        for agent_name in agent_names:
            agent = self.agent_manager.get_agent(agent_name)
            if agent:
                agents[agent_name] = agent
        
        conversation_log = []
        
        try:
            turn = len(conversation_history)
            initial_turn = turn
            
            # Emit initial agent thinking event for the first agent (before starting the loop)
            if progress_callback:
                try:
                    print(f"[Orchestrator] Calling initial progress callback for agent: {current_agent_name}")
                    progress_callback({
                        'type': 'agent_thinking',
                        'agent': current_agent_name,
                        'turn': turn + 1
                    })
                    print(f"[Orchestrator] Initial progress callback completed")
                except Exception as e:
                    print(f"[Orchestrator] Error in initial progress callback: {e}")
                    import traceback
                    traceback.print_exc()
            
            while turn < initial_turn + max_turns:
                turn += 1
                current_agent = agents[current_agent_name]
                
                print(f"[Orchestrator] Turn {turn}/{max_turns}: {current_agent_name} responding")
                
                # Build prompt for current agent
                if turn == 1:
                    # First turn
                    prompt = f"""Objective: {objective}

Begin working toward this objective. Be specific and actionable."""
                else:
                    # Subsequent turns - include conversation context
                    context_summary = "\n\nRecent conversation:\n"
                    for msg in conversation_state['history'][-5:]:  # Last 5 messages
                        context_summary += f"- {msg['sender']}: {msg['message'][:200]}...\n"
                    
                    prompt = f"""Objective: {objective}{context_summary}

Contribute concisely toward this objective. Build on what's been discussed."""
                
                # Get response from current agent
                try:
                    response = current_agent.chat(prompt)
                    
                    if not response:
                        print(f"[Orchestrator] Empty response from {current_agent_name}, ending conversation")
                        break
                    
                    # Store the response
                    message_entry = {
                        'turn': turn,
                        'sender': current_agent_name,
                        'message': response,
                        'timestamp': datetime.utcnow().isoformat()
                    }
                    
                    conversation_log.append(message_entry)
                    conversation_state['history'].append(message_entry)
                    
                    # Store in knowledge base
                    self.knowledge_base.add_interaction(
                        agent_name=current_agent_name,
                        interaction_type='agent_chat',
                        content=f"Orchestrated conversation contribution: {response}",
                        metadata={
                            'conversation_id': conversation_id,
                            'objective': objective,
                            'turn': turn,
                            'orchestrated': True
                        }
                    )
                    
                    # Select next agent based on conversation mode
                    if conversation_mode == 'round_robin':
                        # Strict round-robin: always rotate to next agent
                        current_idx = agent_names.index(current_agent_name) if current_agent_name in agent_names else 0
                        next_idx = (current_idx + 1) % len(agent_names)
                        next_agent = agent_names[next_idx]
                        print(f"[Orchestrator] Round-robin mode: rotating from {current_agent_name} to {next_agent}")
                    else:
                        # Intelligent mode: let LLM decide
                        next_agent = self._select_next_agent(
                            objective=objective,
                            conversation_history=conversation_state['history'],
                            current_agent=current_agent_name,
                            current_response=response,
                            available_agents=agent_names
                        )
                        
                        if next_agent is None:
                            print(f"[Orchestrator] Orchestrator determined conversation should end")
                            break
                        
                        if next_agent == current_agent_name and turn >= initial_turn + max_turns - 1:
                            # Same agent but we're near the end, let's try a different one
                            current_idx = agent_names.index(current_agent_name)
                            next_idx = (current_idx + 1) % len(agent_names)
                            next_agent = agent_names[next_idx]
                    
                    conversation_state['agents_used'].add(next_agent)
                    
                    # Save session after each message
                    self.knowledge_base.save_session(
                        session_id=conversation_id,
                        objective=objective,
                        agent_names=agent_names,
                        conversation_mode=f'orchestrated_{conversation_mode}',
                        conversation_history=conversation_state['history'],
                        current_agent=next_agent,
                        total_turns=turn,
                        status='active'
                    )
                    
                    # Determine which agent/message this is responding to
                    responding_to = None
                    responding_to_message = None
                    if len(conversation_state['history']) > 1:
                        # Get the previous message
                        prev_message = conversation_state['history'][-2]
                        responding_to = prev_message['sender']
                        responding_to_message = prev_message['message'][:200]  # First 200 chars
                    
                    # Emit progress update if callback provided
                    if progress_callback:
                        try:
                            print(f"[Orchestrator] Calling progress callback for turn {turn}, sender: {current_agent_name}")
                            progress_callback({
                                'turn': turn,
                                'sender': current_agent_name,
                                'message': response,
                                'timestamp': message_entry['timestamp'],
                                'next_agent': next_agent,
                                'responding_to': responding_to,
                                'responding_to_message': responding_to_message
                            })
                            print(f"[Orchestrator] Progress callback completed for turn {turn}")
                        except Exception as e:
                            print(f"[Orchestrator] Error in progress callback: {e}")
                            import traceback
                            traceback.print_exc()
                    
                    current_agent_name = next_agent
                    conversation_state['current_agent'] = next_agent
                    
                    print(f"[Orchestrator] Next agent selected: {next_agent}")
                    
                except Exception as e:
                    error_msg = f"Error getting response from {current_agent_name}: {str(e)}"
                    print(f"[Orchestrator] {error_msg}")
                    conversation_log.append({
                        'turn': turn,
                        'sender': current_agent_name,
                        'message': f"Error: {error_msg}",
                        'timestamp': datetime.utcnow().isoformat(),
                        'error': True
                    })
                    break
            
            conversation_state['completed_at'] = datetime.utcnow().isoformat()
            conversation_state['total_turns'] = turn
            
            # Save session to database
            self.knowledge_base.save_session(
                session_id=conversation_id,
                objective=objective,
                agent_names=agent_names,
                conversation_mode=f'orchestrated_{conversation_mode}',
                conversation_history=conversation_state['history'],
                current_agent=conversation_state['current_agent'],
                total_turns=turn,
                status='completed' if turn >= initial_turn + max_turns else 'active'
            )
            
            print(f"[Orchestrator] Conversation '{conversation_id}' completed: {turn} turns, {len(conversation_log)} messages")
            
            return {
                'success': True,
                'conversation_id': conversation_id,
                'conversation': conversation_log,
                'total_turns': turn,
                'agents_used': list(conversation_state['agents_used']),
                'objective': objective,
                'started_at': conversation_state['started_at'],
                'completed_at': conversation_state.get('completed_at')
            }
            
        except Exception as e:
            error_msg = f"Error during orchestrated conversation: {str(e)}"
            print(f"[Orchestrator] {error_msg}")
            
            conversation_state['error'] = error_msg
            conversation_state['completed_at'] = datetime.utcnow().isoformat()
            
            return {
                'success': False,
                'error': error_msg,
                'conversation_id': conversation_id,
                'conversation': conversation_log,
                'total_turns': len(conversation_log),
                'objective': objective
            }
        
        finally:
            # Clean up conversation state after a delay (keep for potential retrieval)
            # In production, you might want to persist this or clean it up differently
            pass
    
    def get_conversation_state(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """Get the state of an active conversation."""
        return self.active_conversations.get(conversation_id)

