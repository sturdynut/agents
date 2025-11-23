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
    
    def __init__(self, db_path: str = "data/agent.db"):
        """Initialize knowledge base with database path."""
        # Ensure data directory exists
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """Initialize database schema."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Knowledge base table for interactions/messages
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
        
        # Agents table for storing agent configurations
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS agents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                model TEXT NOT NULL,
                system_prompt TEXT,
                settings TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        ''')
        
        # Create indexes for faster queries
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
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_agents_name 
            ON agents(name)
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
    
    def save_agent(
        self,
        name: str,
        model: str,
        system_prompt: str = "",
        settings: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Save an agent to the database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        timestamp = datetime.utcnow().isoformat()
        settings_json = json.dumps(settings) if settings else None
        
        try:
            # Check if agent exists
            cursor.execute('SELECT created_at FROM agents WHERE name = ?', (name,))
            existing = cursor.fetchone()
            
            if existing:
                # Update existing agent
                cursor.execute('''
                    UPDATE agents 
                    SET model = ?, system_prompt = ?, settings = ?, updated_at = ?
                    WHERE name = ?
                ''', (model, system_prompt, settings_json, timestamp, name))
            else:
                # Insert new agent
                cursor.execute('''
                    INSERT INTO agents 
                    (name, model, system_prompt, settings, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (name, model, system_prompt, settings_json, timestamp, timestamp))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            conn.close()
            return False
    
    def load_agents(self) -> List[Dict[str, Any]]:
        """Load all agents from the database."""
        try:
            # Check if database file exists
            if not os.path.exists(self.db_path):
                print(f"[KnowledgeBase] Database file not found: {self.db_path}")
                return []
            
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Check if agents table exists
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='agents'")
            if not cursor.fetchone():
                print(f"[KnowledgeBase] Agents table not found in database")
                conn.close()
                return []
            
            cursor.execute('SELECT * FROM agents ORDER BY name')
            rows = cursor.fetchall()
            
            agents = []
            for row in rows:
                try:
                    agent = {
                        'name': row['name'],
                        'model': row['model'],
                        'system_prompt': row['system_prompt'] or '',
                        'settings': json.loads(row['settings']) if row['settings'] else {},
                        'created_at': row['created_at'],
                        'updated_at': row['updated_at']
                    }
                    agents.append(agent)
                except Exception as e:
                    print(f"[KnowledgeBase] Error parsing agent row: {e}")
                    import traceback
                    traceback.print_exc()
            
            conn.close()
            print(f"[KnowledgeBase] Loaded {len(agents)} agents from database: {self.db_path}")
            return agents
        except sqlite3.Error as e:
            print(f"[KnowledgeBase] Database error loading agents: {e}")
            return []
        except Exception as e:
            print(f"[KnowledgeBase] Error loading agents: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def delete_agent(self, name: str) -> bool:
        """Delete an agent from the database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('DELETE FROM agents WHERE name = ?', (name,))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            conn.close()
            return False
    
    def agent_exists_in_db(self, name: str) -> bool:
        """Check if an agent exists in the database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM agents WHERE name = ?', (name,))
        count = cursor.fetchone()[0]
        conn.close()
        
        return count > 0

