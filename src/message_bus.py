#!/usr/bin/env python3
"""
Message Bus Module

Handles direct messaging between agents, routing messages,
and storing message history in the knowledge base.
"""

from typing import Dict, List, Optional
from datetime import datetime
from .knowledge_base import KnowledgeBase


class MessageBus:
    """Manages agent-to-agent messaging."""
    
    def __init__(self, knowledge_base: KnowledgeBase):
        """Initialize message bus with knowledge base."""
        self.knowledge_base = knowledge_base
        self.agent_registry: Dict[str, any] = {}  # Will store agent references
    
    def register_agent(self, agent_name: str, agent_instance: any):
        """Register an agent to receive messages."""
        self.agent_registry[agent_name] = agent_instance
    
    def unregister_agent(self, agent_name: str):
        """Unregister an agent."""
        if agent_name in self.agent_registry:
            del self.agent_registry[agent_name]
    
    def send_message(
        self,
        sender_name: str,
        receiver_name: str,
        message_content: str,
        metadata: Optional[Dict] = None
    ) -> bool:
        """Send a message from one agent to another."""
        # Check if receiver exists
        if receiver_name not in self.agent_registry:
            return False
        
        # Store message in knowledge base
        self.knowledge_base.add_interaction(
            agent_name=sender_name,
            interaction_type='agent_chat',
            content=message_content,
            metadata=metadata or {},
            related_agent=receiver_name
        )
        
        # Also store as received message for receiver
        self.knowledge_base.add_interaction(
            agent_name=receiver_name,
            interaction_type='agent_chat',
            content=f"Message from {sender_name}: {message_content}",
            metadata={'sender': sender_name, **metadata} if metadata else {'sender': sender_name},
            related_agent=sender_name
        )
        
        # Notify receiver agent (if it has a method to handle messages)
        receiver = self.agent_registry[receiver_name]
        if hasattr(receiver, 'receive_message'):
            receiver.receive_message(sender_name, message_content)
        
        return True
    
    def get_messages(
        self,
        agent_name: str,
        from_agent: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Dict]:
        """Get messages for an agent."""
        return self.knowledge_base.get_interactions(
            agent_name=agent_name,
            interaction_type='agent_chat',
            related_agent=from_agent,
            limit=limit
        )
    
    def broadcast_message(
        self,
        sender_name: str,
        message_content: str,
        exclude_agents: Optional[List[str]] = None
    ) -> int:
        """Broadcast a message to all registered agents except sender and excluded ones."""
        exclude_agents = exclude_agents or []
        exclude_agents.append(sender_name)
        
        sent_count = 0
        for agent_name in self.agent_registry:
            if agent_name not in exclude_agents:
                if self.send_message(sender_name, agent_name, message_content):
                    sent_count += 1
        
        return sent_count
    
    def list_agents(self) -> List[str]:
        """List all registered agent names."""
        return list(self.agent_registry.keys())

