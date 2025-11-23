#!/usr/bin/env python3
"""
Database Initialization Script

Creates the SQLite database and initializes all tables and indexes.
This script can be run to set up a fresh database or reset an existing one.
"""

import sqlite3
import os
import sys
from pathlib import Path


def init_database(db_path: str = "data/agent.db", reset: bool = False):
    """
    Initialize the SQLite database with all required tables and indexes.
    
    Args:
        db_path: Path to the SQLite database file
        reset: If True, drop existing tables before creating new ones
    """
    # Ensure data directory exists
    db_dir = os.path.dirname(db_path)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)
    
    # Connect to database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        if reset:
            print("[!] Resetting database (dropping existing tables)...")
            cursor.execute('DROP TABLE IF EXISTS knowledge_base')
            cursor.execute('DROP TABLE IF EXISTS agents')
            print("[OK] Existing tables dropped")
        
        print(f"[*] Creating database at: {db_path}")
        
        # Create knowledge_base table for interactions/messages
        print("[*] Creating knowledge_base table...")
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
        print("[OK] knowledge_base table created")
        
        # Create agents table for storing agent configurations
        print("[*] Creating agents table...")
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
        print("[OK] agents table created")
        
        # Create indexes for faster queries
        print("[*] Creating indexes...")
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_agent_name 
            ON knowledge_base(agent_name)
        ''')
        print("  [OK] Index on knowledge_base.agent_name")
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_interaction_type 
            ON knowledge_base(interaction_type)
        ''')
        print("  [OK] Index on knowledge_base.interaction_type")
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_timestamp 
            ON knowledge_base(timestamp)
        ''')
        print("  [OK] Index on knowledge_base.timestamp")
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_agents_name 
            ON agents(name)
        ''')
        print("  [OK] Index on agents.name")
        
        # Commit changes
        conn.commit()
        
        # Verify tables were created
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        print("\n[SUCCESS] Database initialized successfully!")
        print(f"   Tables created: {', '.join(tables)}")
        
        # Show table schemas
        print("\n[*] Table Schemas:")
        for table in tables:
            cursor.execute(f"PRAGMA table_info({table})")
            columns = cursor.fetchall()
            print(f"\n   {table}:")
            for col in columns:
                print(f"     - {col[1]} ({col[2]})")
        
        # Count existing records (if any)
        if not reset:
            cursor.execute("SELECT COUNT(*) FROM agents")
            agent_count = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM knowledge_base")
            interaction_count = cursor.fetchone()[0]
            
            if agent_count > 0 or interaction_count > 0:
                print(f"\n[*] Existing data:")
                print(f"   Agents: {agent_count}")
                print(f"   Interactions: {interaction_count}")
        
    except sqlite3.Error as e:
        print(f"[ERROR] Database error: {e}")
        conn.rollback()
        sys.exit(1)
    except Exception as e:
        print(f"[ERROR] Error: {e}")
        conn.rollback()
        sys.exit(1)
    finally:
        conn.close()
        print("\n[OK] Database initialization complete!")


def main():
    """Main entry point for the script."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Initialize SQLite database for Multi-Agent System',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python init_db.py                    # Create database with default path
  python init_db.py --db custom.db      # Use custom database path
  python init_db.py --reset             # Reset existing database
        """
    )
    
    parser.add_argument(
        '--db',
        type=str,
        default='data/agent.db',
        help='Path to SQLite database file (default: data/agent.db)'
    )
    
    parser.add_argument(
        '--reset',
        action='store_true',
        help='Drop existing tables before creating new ones (WARNING: This will delete all data!)'
    )
    
    args = parser.parse_args()
    
    if args.reset:
        response = input("[!] WARNING: This will delete all existing data. Continue? (yes/no): ")
        if response.lower() != 'yes':
            print("[CANCELLED] Operation cancelled")
            sys.exit(0)
    
    init_database(db_path=args.db, reset=args.reset)


if __name__ == '__main__':
    main()

