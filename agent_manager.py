#!/usr/bin/env python3
"""
Agent Manager Module

Manages multiple agent instances, their creation, deletion, and lifecycle.
"""

from typing import Dict, Optional, List
from agent_core import EnhancedAgent
from knowledge_base import KnowledgeBase
from message_bus import MessageBus


class AgentManager:
    """Manages multiple agent instances."""
    
    def __init__(self, knowledge_base: KnowledgeBase, message_bus: MessageBus):
        """Initialize agent manager."""
        self.agents: Dict[str, EnhancedAgent] = {}
        self.knowledge_base = knowledge_base
        self.message_bus = message_bus
    
    def create_agent(
        self,
        name: str,
        model: str,
        system_prompt: str = "",
        settings: Optional[Dict] = None
    ) -> bool:
        """Create a new agent."""
        if name in self.agents:
            return False  # Agent already exists
        
        agent = EnhancedAgent(
            name=name,
            model=model,
            system_prompt=system_prompt,
            settings=settings or {},
            knowledge_base=self.knowledge_base,
            message_bus=self.message_bus
        )
        
        self.agents[name] = agent
        self.message_bus.register_agent(name, agent)
        
        # Log agent creation
        self.knowledge_base.add_interaction(
            agent_name=name,
            interaction_type='system',
            content=f"Agent '{name}' created with model '{model}'",
            metadata={'action': 'create_agent', 'model': model}
        )
        
        return True
    
    def delete_agent(self, name: str) -> bool:
        """Delete an agent."""
        if name not in self.agents:
            return False
        
        # Log agent deletion
        self.knowledge_base.add_interaction(
            agent_name=name,
            interaction_type='system',
            content=f"Agent '{name}' deleted",
            metadata={'action': 'delete_agent'}
        )
        
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

