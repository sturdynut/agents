#!/usr/bin/env python3
"""
Knowledge Base Module

Manages a shared SQLite database that stores all agent interactions,
including user chats, agent-to-agent messages, task executions, and file operations.
"""

import sqlite3
import json
import os
import hashlib
import math
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
from functools import lru_cache

try:
    import ollama
except ImportError:
    ollama = None


class EmbeddingService:
    """Service for generating and managing embeddings using Ollama."""
    
    def __init__(
        self, 
        model: str = "nomic-embed-text",
        api_endpoint: str = "http://localhost:11434",
        cache_size: int = 1000
    ):
        """Initialize embedding service.
        
        Args:
            model: Ollama embedding model name
            api_endpoint: Ollama API endpoint
            cache_size: Size of embedding cache
        """
        self.model = model
        self.api_endpoint = api_endpoint
        self._cache = {}
        self._cache_size = cache_size
        
        # Set Ollama host if non-default
        if api_endpoint != "http://localhost:11434":
            os.environ['OLLAMA_HOST'] = api_endpoint.replace('http://', '').replace('https://', '')
    
    def _get_cache_key(self, text: str) -> str:
        """Generate cache key for text."""
        return hashlib.md5(text.encode('utf-8')).hexdigest()
    
    def generate_embedding(self, text: str) -> Optional[List[float]]:
        """Generate embedding for a single text.
        
        Args:
            text: Text to embed
            
        Returns:
            List of floats representing the embedding, or None on error
        """
        if not text or not text.strip():
            return None
        
        if ollama is None:
            print("[EmbeddingService] Ollama package not installed")
            return None
        
        # Check cache
        cache_key = self._get_cache_key(text)
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        try:
            response = ollama.embeddings(
                model=self.model,
                prompt=text
            )
            
            if response and 'embedding' in response:
                embedding = response['embedding']
                
                # Cache the result
                if len(self._cache) >= self._cache_size:
                    # Simple cache eviction: remove oldest entry
                    self._cache.pop(next(iter(self._cache)))
                self._cache[cache_key] = embedding
                
                return embedding
            else:
                print(f"[EmbeddingService] Invalid response from Ollama: {response}")
                return None
                
        except Exception as e:
            print(f"[EmbeddingService] Error generating embedding: {e}")
            return None
    
    def generate_embeddings_batch(self, texts: List[str]) -> List[Optional[List[float]]]:
        """Generate embeddings for multiple texts.
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embeddings (or None for failures)
        """
        embeddings = []
        for text in texts:
            embedding = self.generate_embedding(text)
            embeddings.append(embedding)
        return embeddings
    
    @staticmethod
    def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors.
        
        Args:
            vec1: First vector
            vec2: Second vector
            
        Returns:
            Cosine similarity score between -1 and 1
        """
        if not vec1 or not vec2 or len(vec1) != len(vec2):
            return 0.0
        
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        magnitude1 = math.sqrt(sum(a * a for a in vec1))
        magnitude2 = math.sqrt(sum(b * b for b in vec2))
        
        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0
        
        return dot_product / (magnitude1 * magnitude2)


class KnowledgeBase:
    """Manages the shared knowledge base database."""
    
    def __init__(
        self, 
        db_path: str = "data/agent.db",
        embedding_model: str = "nomic-embed-text",
        api_endpoint: str = "http://localhost:11434"
    ):
        """Initialize knowledge base with database path."""
        # Ensure data directory exists
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        self.db_path = db_path
        self.embedding_service = EmbeddingService(
            model=embedding_model,
            api_endpoint=api_endpoint
        )
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
                related_agent TEXT,
                embedding TEXT,
                session_id TEXT
            )
        ''')
        
        # Migrate existing tables - add embedding column if it doesn't exist
        try:
            cursor.execute("SELECT embedding FROM knowledge_base LIMIT 1")
        except sqlite3.OperationalError:
            # Column doesn't exist, add it
            cursor.execute("ALTER TABLE knowledge_base ADD COLUMN embedding TEXT")
            print("[KnowledgeBase] Added embedding column to existing table")
        
        # Migrate existing tables - add session_id column if it doesn't exist
        try:
            cursor.execute("SELECT session_id FROM knowledge_base LIMIT 1")
        except sqlite3.OperationalError:
            # Column doesn't exist, add it
            cursor.execute("ALTER TABLE knowledge_base ADD COLUMN session_id TEXT")
            print("[KnowledgeBase] Added session_id column to existing table")
        
        # Agents table for storing agent configurations
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS agents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                model TEXT NOT NULL,
                system_prompt TEXT,
                settings TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                avatar_seed TEXT
            )
        ''')
        
        # Migrate existing agents table - add avatar_seed column if it doesn't exist
        try:
            cursor.execute("SELECT avatar_seed FROM agents LIMIT 1")
        except sqlite3.OperationalError:
            # Column doesn't exist, add it
            cursor.execute("ALTER TABLE agents ADD COLUMN avatar_seed TEXT")
            print("[KnowledgeBase] Added avatar_seed column to agents table")
        
        # Sessions table for tracking conversation sessions
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS conversation_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT UNIQUE NOT NULL,
                objective TEXT NOT NULL,
                agent_names TEXT NOT NULL,
                conversation_mode TEXT NOT NULL,
                conversation_history TEXT,
                current_agent TEXT,
                total_turns INTEGER DEFAULT 0,
                status TEXT DEFAULT 'active',
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
            CREATE INDEX IF NOT EXISTS idx_agent_timestamp 
            ON knowledge_base(agent_name, timestamp DESC)
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_agents_name 
            ON agents(name)
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_sessions_id 
            ON conversation_sessions(session_id)
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_sessions_status 
            ON conversation_sessions(status)
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_session_id 
            ON knowledge_base(session_id)
        ''')
        
        conn.commit()
        conn.close()
    
    def add_interaction(
        self,
        agent_name: str,
        interaction_type: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        related_agent: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> int:
        """Add an interaction to the knowledge base with embedding.
        
        Args:
            agent_name: Name of the agent
            interaction_type: Type of interaction
            content: Content of the interaction
            metadata: Optional metadata dict
            related_agent: Name of related agent if any
            session_id: Optional session ID to scope knowledge to a specific session
        
        Returns:
            ID of the created interaction
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        timestamp = datetime.utcnow().isoformat()
        metadata_json = json.dumps(metadata) if metadata else None
        
        # Generate embedding for content
        embedding = self.embedding_service.generate_embedding(content)
        embedding_json = json.dumps(embedding) if embedding else None
        
        cursor.execute('''
            INSERT INTO knowledge_base 
            (timestamp, agent_name, interaction_type, content, metadata, related_agent, embedding, session_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (timestamp, agent_name, interaction_type, content, metadata_json, related_agent, embedding_json, session_id))
        
        interaction_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return interaction_id
    
    def get_interactions(
        self,
        agent_name: Optional[str] = None,
        interaction_type: Optional[str] = None,
        related_agent: Optional[str] = None,
        session_id: Optional[str] = None,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Query interactions from the knowledge base.
        
        Args:
            agent_name: Filter by agent name
            interaction_type: Filter by interaction type
            related_agent: Filter by related agent
            session_id: Filter by session ID (for session-scoped knowledge)
            limit: Maximum number of results
            offset: Offset for pagination
        
        Returns:
            List of interaction dictionaries
        """
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
        
        if session_id:
            query += " AND session_id = ?"
            params.append(session_id)
        
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
                'related_agent': row['related_agent'],
                'session_id': row['session_id'] if 'session_id' in row.keys() else None
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
    
    def semantic_search_interactions(
        self,
        query: str,
        agent_name: Optional[str] = None,
        top_k: int = 10,
        time_decay_factor: float = 0.95,
        interaction_type: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Search interactions using semantic similarity with time-weighting.
        
        Args:
            query: Search query text
            agent_name: Filter by agent name (optional)
            top_k: Number of top results to return
            time_decay_factor: Factor for time decay (0-1, higher = less decay)
            interaction_type: Filter by interaction type (optional)
            session_id: Filter by session ID for session-scoped knowledge (optional)
            
        Returns:
            List of interactions sorted by relevance score (highest first)
        """
        # Generate query embedding
        query_embedding = self.embedding_service.generate_embedding(query)
        if not query_embedding:
            print("[KnowledgeBase] Failed to generate query embedding, falling back to recent interactions")
            return self.get_interactions(
                agent_name=agent_name,
                interaction_type=interaction_type,
                session_id=session_id,
                limit=top_k
            )
        
        # Retrieve interactions with embeddings
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        query_sql = "SELECT * FROM knowledge_base WHERE embedding IS NOT NULL"
        params = []
        
        if agent_name:
            query_sql += " AND agent_name = ?"
            params.append(agent_name)
        
        if interaction_type:
            query_sql += " AND interaction_type = ?"
            params.append(interaction_type)
        
        if session_id:
            query_sql += " AND session_id = ?"
            params.append(session_id)
        
        query_sql += " ORDER BY timestamp DESC"
        
        cursor.execute(query_sql, params)
        rows = cursor.fetchall()
        conn.close()
        
        if not rows:
            return []
        
        # Calculate relevance scores
        scored_interactions = []
        current_time = datetime.utcnow()
        
        for row in rows:
            try:
                # Parse embedding
                embedding = json.loads(row['embedding']) if row['embedding'] else None
                if not embedding:
                    continue
                
                # Calculate cosine similarity
                similarity = self.embedding_service.cosine_similarity(query_embedding, embedding)
                
                # Calculate time decay
                interaction_time = datetime.fromisoformat(row['timestamp'])
                time_delta = (current_time - interaction_time).total_seconds() / 86400  # days
                time_weight = time_decay_factor ** time_delta
                
                # Combined score
                score = similarity * time_weight
                
                interaction = {
                    'id': row['id'],
                    'timestamp': row['timestamp'],
                    'agent_name': row['agent_name'],
                    'interaction_type': row['interaction_type'],
                    'content': row['content'],
                    'metadata': json.loads(row['metadata']) if row['metadata'] else None,
                    'related_agent': row['related_agent'],
                    'relevance_score': score,
                    'similarity': similarity,
                    'time_weight': time_weight
                }
                scored_interactions.append(interaction)
                
            except Exception as e:
                print(f"[KnowledgeBase] Error processing interaction {row['id']}: {e}")
                continue
        
        # Sort by score and return top-k
        scored_interactions.sort(key=lambda x: x['relevance_score'], reverse=True)
        return scored_interactions[:top_k]
    
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
    
    def backfill_embeddings(self, batch_size: int = 50) -> int:
        """Generate embeddings for interactions that don't have them.
        
        Args:
            batch_size: Number of interactions to process at a time
            
        Returns:
            Number of embeddings generated
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Find interactions without embeddings
        cursor.execute('''
            SELECT id, content FROM knowledge_base 
            WHERE embedding IS NULL 
            ORDER BY timestamp DESC
        ''')
        rows = cursor.fetchall()
        conn.close()
        
        if not rows:
            print("[KnowledgeBase] No interactions need embedding generation")
            return 0
        
        print(f"[KnowledgeBase] Generating embeddings for {len(rows)} interactions...")
        total_generated = 0
        
        # Process in batches
        for i in range(0, len(rows), batch_size):
            batch = rows[i:i + batch_size]
            
            for row in batch:
                try:
                    embedding = self.embedding_service.generate_embedding(row['content'])
                    if embedding:
                        embedding_json = json.dumps(embedding)
                        
                        # Update the interaction with embedding
                        conn = sqlite3.connect(self.db_path)
                        cursor = conn.cursor()
                        cursor.execute(
                            'UPDATE knowledge_base SET embedding = ? WHERE id = ?',
                            (embedding_json, row['id'])
                        )
                        conn.commit()
                        conn.close()
                        
                        total_generated += 1
                        
                        if total_generated % 10 == 0:
                            print(f"[KnowledgeBase] Generated {total_generated}/{len(rows)} embeddings...")
                            
                except Exception as e:
                    print(f"[KnowledgeBase] Error generating embedding for interaction {row['id']}: {e}")
                    continue
        
        print(f"[KnowledgeBase] Completed: generated {total_generated} embeddings")
        return total_generated
    
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
        settings: Optional[Dict[str, Any]] = None,
        tools: Optional[List[str]] = None,
        avatar_seed: Optional[str] = None
    ) -> bool:
        """Save an agent to the database.
        
        Args:
            name: Agent name
            model: Ollama model name
            system_prompt: System prompt for the agent
            settings: Agent settings
            tools: List of allowed tool names. If None, all tools are allowed.
            avatar_seed: Custom seed for avatar generation. If None, uses agent name.
        
        Returns:
            True if agent was saved successfully, False otherwise
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        timestamp = datetime.utcnow().isoformat()
        settings_json = json.dumps(settings) if settings else None
        tools_json = json.dumps(tools) if tools is not None else None
        
        try:
            # Check if agent exists
            cursor.execute('SELECT created_at FROM agents WHERE name = ?', (name,))
            existing = cursor.fetchone()
            
            if existing:
                # Update existing agent
                cursor.execute('''
                    UPDATE agents 
                    SET model = ?, system_prompt = ?, settings = ?, tools = ?, avatar_seed = ?, updated_at = ?
                    WHERE name = ?
                ''', (model, system_prompt, settings_json, tools_json, avatar_seed, timestamp, name))
            else:
                # Insert new agent
                cursor.execute('''
                    INSERT INTO agents 
                    (name, model, system_prompt, settings, created_at, updated_at, tools, avatar_seed)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (name, model, system_prompt, settings_json, timestamp, timestamp, tools_json, avatar_seed))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"[KnowledgeBase] Error saving agent: {e}")
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
                    # Check if tools column exists in this row
                    tools_data = None
                    try:
                        if 'tools' in row.keys():
                            tools_data = json.loads(row['tools']) if row['tools'] else None
                    except (KeyError, json.JSONDecodeError):
                        pass  # Column doesn't exist or invalid JSON, tools will be None
                    
                    # Check if avatar_seed column exists
                    avatar_seed = None
                    try:
                        if 'avatar_seed' in row.keys():
                            avatar_seed = row['avatar_seed']
                    except KeyError:
                        pass
                    
                    agent = {
                        'name': row['name'],
                        'model': row['model'],
                        'system_prompt': row['system_prompt'] or '',
                        'settings': json.loads(row['settings']) if row['settings'] else {},
                        'created_at': row['created_at'],
                        'updated_at': row['updated_at'],
                        'tools': tools_data,
                        'avatar_seed': avatar_seed
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
    
    def save_session(
        self,
        session_id: str,
        objective: str,
        agent_names: List[str],
        conversation_mode: str,
        conversation_history: List[Dict[str, Any]],
        current_agent: Optional[str] = None,
        total_turns: int = 0,
        status: str = 'active'
    ) -> bool:
        """Save or update a conversation session."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        timestamp = datetime.utcnow().isoformat()
        agent_names_json = json.dumps(agent_names)
        history_json = json.dumps(conversation_history)
        
        try:
            # Check if session exists
            cursor.execute('SELECT id FROM conversation_sessions WHERE session_id = ?', (session_id,))
            existing = cursor.fetchone()
            
            if existing:
                # Update existing session
                cursor.execute('''
                    UPDATE conversation_sessions 
                    SET objective = ?, agent_names = ?, conversation_mode = ?, 
                        conversation_history = ?, current_agent = ?, total_turns = ?, 
                        status = ?, updated_at = ?
                    WHERE session_id = ?
                ''', (objective, agent_names_json, conversation_mode, history_json, 
                      current_agent, total_turns, status, timestamp, session_id))
            else:
                # Insert new session
                cursor.execute('''
                    INSERT INTO conversation_sessions 
                    (session_id, objective, agent_names, conversation_mode, 
                     conversation_history, current_agent, total_turns, status, 
                     created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (session_id, objective, agent_names_json, conversation_mode, 
                      history_json, current_agent, total_turns, status, 
                      timestamp, timestamp))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            conn.close()
            print(f"[KnowledgeBase] Error saving session: {e}")
            return False
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get a conversation session by ID."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM conversation_sessions WHERE session_id = ?', (session_id,))
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        return {
            'session_id': row['session_id'],
            'objective': row['objective'],
            'agent_names': json.loads(row['agent_names']),
            'conversation_mode': row['conversation_mode'],
            'conversation_history': json.loads(row['conversation_history']) if row['conversation_history'] else [],
            'current_agent': row['current_agent'],
            'total_turns': row['total_turns'],
            'status': row['status'],
            'created_at': row['created_at'],
            'updated_at': row['updated_at']
        }
    
    def list_sessions(self, status: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """List conversation sessions."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        query = 'SELECT * FROM conversation_sessions'
        params = []
        
        if status:
            query += ' WHERE status = ?'
            params.append(status)
        
        query += ' ORDER BY updated_at DESC LIMIT ?'
        params.append(limit)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        sessions = []
        for row in rows:
            sessions.append({
                'session_id': row['session_id'],
                'objective': row['objective'],
                'agent_names': json.loads(row['agent_names']),
                'conversation_mode': row['conversation_mode'],
                'conversation_history': json.loads(row['conversation_history']) if row['conversation_history'] else [],
                'current_agent': row['current_agent'],
                'total_turns': row['total_turns'],
                'status': row['status'],
                'created_at': row['created_at'],
                'updated_at': row['updated_at']
            })
        
        return sessions

