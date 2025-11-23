"""
Multi-Agent System - Core Module

This package contains the core components of the multi-agent system.
"""

__version__ = "1.0.0"

from .agent_core import EnhancedAgent, OllamaClient
from .agent_manager import AgentManager
from .knowledge_base import KnowledgeBase
from .message_bus import MessageBus
from .conversation_orchestrator import ConversationOrchestrator

__all__ = [
    'EnhancedAgent',
    'OllamaClient',
    'AgentManager',
    'KnowledgeBase',
    'MessageBus',
    'ConversationOrchestrator',
]

