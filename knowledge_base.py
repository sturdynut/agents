#!/usr/bin/env python3
"""
Knowledge Base Module

Manages a shared SQLite database that stores all agent interactions,
including user chats, agent-to-agent messages, task executions, and file operations.
"""

import sqlite3
import json
import os
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path


class KnowledgeBase:
    """Manages the shared knowledge base database."""
    
    def __init__(self, db_path: str = "data/knowledge.db"):
        """Initialize knowledge base with database path."""
        # Ensure data directory exists
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """Initialize database schema."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS knowledge_base (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                agent_name TEXT NOT NULL,
                interaction_type TEXT NOT NULL,
                content TEXT NOT NULL,
                metadata TEXT,
                related_agent TEXT
            )
        ''')
        
        # Create index for faster queries
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_agent_name 
            ON knowledge_base(agent_name)
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_interaction_type 
            ON knowledge_base(interaction_type)
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_timestamp 
            ON knowledge_base(timestamp)
        ''')
        
        conn.commit()
        conn.close()
    
    def add_interaction(
        self,
        agent_name: str,
        interaction_type: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        related_agent: Optional[str] = None
    ) -> int:
        """Add an interaction to the knowledge base."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        timestamp = datetime.utcnow().isoformat()
        metadata_json = json.dumps(metadata) if metadata else None
        
        cursor.execute('''
            INSERT INTO knowledge_base 
            (timestamp, agent_name, interaction_type, content, metadata, related_agent)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (timestamp, agent_name, interaction_type, content, metadata_json, related_agent))
        
        interaction_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return interaction_id
    
    def get_interactions(
        self,
        agent_name: Optional[str] = None,
        interaction_type: Optional[str] = None,
        related_agent: Optional[str] = None,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Query interactions from the knowledge base."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        query = "SELECT * FROM knowledge_base WHERE 1=1"
        params = []
        
        if agent_name:
            query += " AND agent_name = ?"
            params.append(agent_name)
        
        if interaction_type:
            query += " AND interaction_type = ?"
            params.append(interaction_type)
        
        if related_agent:
            query += " AND related_agent = ?"
            params.append(related_agent)
        
        query += " ORDER BY timestamp DESC"
        
        if limit:
            query += " LIMIT ? OFFSET ?"
            params.extend([limit, offset])
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        interactions = []
        for row in rows:
            interaction = {
                'id': row['id'],
                'timestamp': row['timestamp'],
                'agent_name': row['agent_name'],
                'interaction_type': row['interaction_type'],
                'content': row['content'],
                'metadata': json.loads(row['metadata']) if row['metadata'] else None,
                'related_agent': row['related_agent']
            }
            interactions.append(interaction)
        
        conn.close()
        return interactions
    
    def search_interactions(
        self,
        search_term: str,
        agent_name: Optional[str] = None,
        limit: Optional[int] = 100
    ) -> List[Dict[str, Any]]:
        """Search interactions by content."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        query = "SELECT * FROM knowledge_base WHERE content LIKE ?"
        params = [f'%{search_term}%']
        
        if agent_name:
            query += " AND agent_name = ?"
            params.append(agent_name)
        
        query += " ORDER BY timestamp DESC"
        
        if limit:
            query += " LIMIT ?"
            params.append(limit)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        interactions = []
        for row in rows:
            interaction = {
                'id': row['id'],
                'timestamp': row['timestamp'],
                'agent_name': row['agent_name'],
                'interaction_type': row['interaction_type'],
                'content': row['content'],
                'metadata': json.loads(row['metadata']) if row['metadata'] else None,
                'related_agent': row['related_agent']
            }
            interactions.append(interaction)
        
        conn.close()
        return interactions
    
    def get_agent_knowledge_summary(self, agent_name: str, limit: int = 50) -> str:
        """Get a summary of recent knowledge for an agent."""
        interactions = self.get_interactions(agent_name=agent_name, limit=limit)
        
        if not interactions:
            return "No previous interactions found."
        
        summary_parts = []
        for interaction in reversed(interactions):  # Oldest first
            timestamp = interaction['timestamp']
            interaction_type = interaction['interaction_type']
            content = interaction['content'][:200]  # Truncate long content
            
            summary_parts.append(
                f"[{timestamp}] {interaction_type}: {content}"
            )
        
        return "\n".join(summary_parts)
    
    def get_shared_knowledge_summary(self, limit: int = 100) -> str:
        """Get a summary of shared knowledge across all agents."""
        interactions = self.get_interactions(limit=limit)
        
        if not interactions:
            return "No shared knowledge found."
        
        summary_parts = []
        for interaction in reversed(interactions):  # Oldest first
            timestamp = interaction['timestamp']
            agent_name = interaction['agent_name']
            interaction_type = interaction['interaction_type']
            content = interaction['content'][:200]  # Truncate long content
            
            summary_parts.append(
                f"[{timestamp}] {agent_name} - {interaction_type}: {content}"
            )
        
        return "\n".join(summary_parts)
    
    def delete_interactions(self, agent_name: Optional[str] = None):
        """Delete interactions, optionally filtered by agent name."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if agent_name:
            cursor.execute("DELETE FROM knowledge_base WHERE agent_name = ?", (agent_name,))
        else:
            cursor.execute("DELETE FROM knowledge_base")
        
        conn.commit()
        conn.close()

