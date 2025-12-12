#!/usr/bin/env python3
"""
Agent Manager Module

Manages multiple agent instances, their creation, deletion, and lifecycle.
"""

from typing import Dict, Optional, List
from .agent_core import EnhancedAgent
from .knowledge_base import KnowledgeBase
from .message_bus import MessageBus


class AgentManager:
    """Manages multiple agent instances."""
    
    def __init__(self, knowledge_base: KnowledgeBase, message_bus: MessageBus):
        """Initialize agent manager and load agents from database."""
        self.agents: Dict[str, EnhancedAgent] = {}
        self.knowledge_base = knowledge_base
        self.message_bus = message_bus
        
        # Load agents from database
        self._load_agents_from_db()
    
    def _load_agents_from_db(self):
        """Load all agents from the database and instantiate them."""
        try:
            agents_data = self.knowledge_base.load_agents()
            print(f"[AgentManager] Loading {len(agents_data)} agents from database...")
            
            for agent_data in agents_data:
                try:
                    # Get tools from agent data
                    tools = agent_data.get('tools', None)
                    avatar_seed = agent_data.get('avatar_seed', None)
                    
                    agent = EnhancedAgent(
                        name=agent_data['name'],
                        model=agent_data['model'],
                        system_prompt=agent_data['system_prompt'],
                        settings=agent_data['settings'],
                        knowledge_base=self.knowledge_base,
                        message_bus=self.message_bus,
                        tools=tools,
                        avatar_seed=avatar_seed
                    )
                    
                    self.agents[agent_data['name']] = agent
                    self.message_bus.register_agent(agent_data['name'], agent)
                    
                    tools_info = f" (tools: {', '.join(agent.allowed_tools)})" if agent.allowed_tools else " (no tools)"
                    print(f"[AgentManager] Loaded agent: {agent_data['name']} ({agent_data['model']}){tools_info}")
                except Exception as e:
                    print(f"[AgentManager] Error loading agent '{agent_data.get('name', 'unknown')}': {e}")
                    import traceback
                    traceback.print_exc()
            
            print(f"[AgentManager] Successfully loaded {len(self.agents)} agents")
        except Exception as e:
            print(f"[AgentManager] Error loading agents from database: {e}")
            import traceback
            traceback.print_exc()
    
    def create_agent(
        self,
        name: str,
        model: str,
        system_prompt: str = "",
        settings: Optional[Dict] = None,
        tools: Optional[List[str]] = None,
        avatar_seed: Optional[str] = None
    ) -> bool:
        """Create a new agent and save to database.
        
        Args:
            name: Agent name
            model: Ollama model name
            system_prompt: System prompt for the agent
            settings: Agent settings
            tools: List of allowed tool names. If None, all tools are allowed.
            avatar_seed: Custom seed for avatar generation. If None, uses agent name.
        
        Returns:
            True if agent was created successfully, False otherwise
        """
        if name in self.agents:
            return False  # Agent already exists
        
        # Save to database first
        success = self.knowledge_base.save_agent(
            name=name,
            model=model,
            system_prompt=system_prompt,
            settings=settings or {},
            tools=tools,
            avatar_seed=avatar_seed
        )
        
        if not success:
            return False  # Failed to save to database
        
        # Create agent instance
        agent = EnhancedAgent(
            name=name,
            model=model,
            system_prompt=system_prompt,
            settings=settings or {},
            knowledge_base=self.knowledge_base,
            message_bus=self.message_bus,
            tools=tools,
            avatar_seed=avatar_seed
        )
        
        self.agents[name] = agent
        self.message_bus.register_agent(name, agent)
        
        # Log agent creation
        tools_str = ', '.join(agent.allowed_tools) if agent.allowed_tools else 'none'
        self.knowledge_base.add_interaction(
            agent_name=name,
            interaction_type='system',
            content=f"Agent '{name}' created with model '{model}' and tools: {tools_str}",
            metadata={'action': 'create_agent', 'model': model, 'tools': agent.allowed_tools}
        )
        
        return True
    
    def delete_agent(self, name: str) -> bool:
        """Delete an agent from memory and database."""
        if name not in self.agents:
            return False
        
        # Delete from database
        success = self.knowledge_base.delete_agent(name)
        if not success:
            return False  # Failed to delete from database
        
        # Log agent deletion
        self.knowledge_base.add_interaction(
            agent_name=name,
            interaction_type='system',
            content=f"Agent '{name}' deleted",
            metadata={'action': 'delete_agent'}
        )
        
        # Remove from memory
        del self.agents[name]
        self.message_bus.unregister_agent(name)
        
        return True
    
    def get_agent(self, name: str) -> Optional[EnhancedAgent]:
        """Get an agent by name."""
        return self.agents.get(name)
    
    def list_agents(self) -> List[Dict[str, any]]:
        """List all agents with their info."""
        return [agent.get_info() for agent in self.agents.values()]
    
    def agent_exists(self, name: str) -> bool:
        """Check if an agent exists."""
        return name in self.agents
    
    def get_agent_names(self) -> List[str]:
        """Get list of all agent names."""
        return list(self.agents.keys())

