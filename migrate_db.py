#!/usr/bin/env python3
"""
Database Migration Script

Migrates agents from knowledge.db to agent.db
"""

import sqlite3
import os
import shutil
from pathlib import Path


def migrate_database(old_db: str = "data/knowledge.db", new_db: str = "data/agent.db"):
    """Migrate agents from old database to new database."""
    
    if not os.path.exists(old_db):
        print(f"[ERROR] Source database not found: {old_db}")
        return False
    
    print(f"[*] Migrating from {old_db} to {new_db}")
    
    # Ensure data directory exists
    os.makedirs(os.path.dirname(new_db), exist_ok=True)
    
    # Connect to both databases
    old_conn = sqlite3.connect(old_db)
    old_cursor = old_conn.cursor()
    
    # Check if old database has agents table
    old_cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='agents'")
    if not old_cursor.fetchone():
        print(f"[ERROR] Agents table not found in {old_db}")
        old_conn.close()
        return False
    
    # Count agents in old database
    old_cursor.execute("SELECT COUNT(*) FROM agents")
    agent_count = old_cursor.fetchone()[0]
    print(f"[*] Found {agent_count} agents in {old_db}")
    
    if agent_count == 0:
        print("[!] No agents to migrate")
        old_conn.close()
        return True
    
    # Initialize new database if it doesn't exist
    if not os.path.exists(new_db):
        print(f"[*] Creating new database: {new_db}")
        # Import init function
        from init_db import init_database
        init_database(new_db, reset=False)
    
    new_conn = sqlite3.connect(new_db)
    new_cursor = new_conn.cursor()
    
    # Check if new database has agents table
    new_cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='agents'")
    if not new_cursor.fetchone():
        print(f"[ERROR] Agents table not found in {new_db}")
        print(f"[INFO] Run 'python init_db.py' first")
        old_conn.close()
        new_conn.close()
        return False
    
    # Count existing agents in new database
    new_cursor.execute("SELECT COUNT(*) FROM agents")
    existing_count = new_cursor.fetchone()[0]
    
    if existing_count > 0:
        print(f"[!] {new_db} already has {existing_count} agents. Will skip existing agents.")
    
    try:
        # Get all agents from old database
        old_cursor.execute("SELECT * FROM agents")
        agents = old_cursor.fetchall()
        
        # Get column names
        columns = [description[0] for description in old_cursor.description]
        
        migrated = 0
        skipped = 0
        
        for agent_row in agents:
            agent_dict = dict(zip(columns, agent_row))
            name = agent_dict['name']
            
            # Check if agent already exists in new database
            new_cursor.execute("SELECT COUNT(*) FROM agents WHERE name = ?", (name,))
            exists = new_cursor.fetchone()[0] > 0
            
            if exists:
                print(f"  [-] Skipping '{name}' (already exists in new database)")
                skipped += 1
                continue
            
            # Insert into new database
            new_cursor.execute('''
                INSERT INTO agents 
                (name, model, system_prompt, settings, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                agent_dict['name'],
                agent_dict['model'],
                agent_dict['system_prompt'],
                agent_dict['settings'],
                agent_dict['created_at'],
                agent_dict['updated_at']
            ))
            print(f"  [OK] Migrated agent: {name}")
            migrated += 1
        
        new_conn.commit()
        
        print(f"\n[SUCCESS] Migration complete!")
        print(f"   Agents migrated: {migrated}")
        if skipped > 0:
            print(f"   Agents skipped: {skipped}")
        
        # Show agents in new database
        new_cursor.execute("SELECT COUNT(*) FROM agents")
        total = new_cursor.fetchone()[0]
        print(f"   Total agents in {new_db}: {total}")
        
        old_conn.close()
        new_conn.close()
        return True
        
    except Exception as e:
        print(f"[ERROR] Migration error: {e}")
        import traceback
        traceback.print_exc()
        old_conn.rollback()
        new_conn.rollback()
        old_conn.close()
        new_conn.close()
        return False


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Migrate agents from knowledge.db to agent.db',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        '--old-db',
        type=str,
        default='data/knowledge.db',
        help='Source database path (default: data/knowledge.db)'
    )
    
    parser.add_argument(
        '--new-db',
        type=str,
        default='data/agent.db',
        help='Destination database path (default: data/agent.db)'
    )
    
    args = parser.parse_args()
    
    migrate_database(args.old_db, args.new_db)


if __name__ == '__main__':
    main()

