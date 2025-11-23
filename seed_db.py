#!/usr/bin/env python3
"""
Database Seeding Script

Adds sample agents to the database for testing and development.
This script can be run to populate the database with example agents.
"""

import sqlite3
import json
import os
import sys
from datetime import datetime
from pathlib import Path


def seed_database(db_path: str = "data/agent.db", overwrite: bool = False):
    """
    Seed the database with sample agents.
    
    Args:
        db_path: Path to the SQLite database file
        overwrite: If True, delete existing agents before adding new ones
    """
    # Check if database exists
    if not os.path.exists(db_path):
        print(f"[ERROR] Database not found at: {db_path}")
        print(f"[INFO] Run 'python init_db.py' first to create the database")
        sys.exit(1)
    
    # Connect to database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check if agents table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='agents'")
        if not cursor.fetchone():
            print(f"[ERROR] Agents table not found in database")
            print(f"[INFO] Run 'python init_db.py' first to create the tables")
            sys.exit(1)
        
        if overwrite:
            print("[!] Deleting existing agents...")
            cursor.execute("DELETE FROM agents")
            print("[OK] Existing agents deleted")
        
        # Check for existing agents
        cursor.execute("SELECT COUNT(*) FROM agents")
        existing_count = cursor.fetchone()[0]
        
        if existing_count > 0 and not overwrite:
            print(f"[!] Found {existing_count} existing agent(s) in database")
            response = input("Continue adding seed agents? (yes/no): ")
            if response.lower() != 'yes':
                print("[CANCELLED] Operation cancelled")
                sys.exit(0)
        
        print("[*] Adding sample agents to database...")
        
        timestamp = datetime.utcnow().isoformat()
        
        # Define sample agents
        sample_agents = [
            {
                'name': 'Designer',
                'model': 'llama3.2',
                'system_prompt': '''You are a creative UI/UX designer with expertise in creating beautiful, 
functional, and user-friendly interfaces. You understand design principles, color theory, typography, 
and user experience best practices. When designing, you consider usability, accessibility, and aesthetic 
appeal. You can create mockups, wireframes, design specifications, and provide detailed design guidance. 
You stay current with modern design trends while maintaining timeless design principles.''',
                'settings': {
                    'temperature': 0.8,
                    'max_tokens': 2048,
                    'api_endpoint': 'http://localhost:11434'
                }
            },
            {
                'name': 'Coder',
                'model': 'llama3.2',
                'system_prompt': '''You are an expert software developer who writes clean, efficient, and 
well-documented code. You follow best practices, design patterns, and write maintainable software. 

IMPORTANT: When creating, writing, or building code files, you MUST save them in the "agent_code" folder 
within the project directory. This folder is specifically designated for code created by agents. Always 
use relative paths like "agent_code/filename.py" or "agent_code/subfolder/file.js" when creating files.

You can work with multiple programming languages and frameworks. You write code that is:
- Well-structured and organized
- Properly commented and documented
- Follows language-specific conventions
- Includes error handling where appropriate
- Is production-ready when possible

When asked to build something, create the necessary files in the agent_code directory, ensuring the 
directory structure is logical and maintainable.''',
                'settings': {
                    'temperature': 0.3,
                    'max_tokens': 4096,
                    'api_endpoint': 'http://localhost:11434'
                }
            },
            {
                'name': 'Tester',
                'model': 'llama3.2',
                'system_prompt': '''You are a quality assurance engineer and software tester with expertise 
in testing methodologies, test case design, and bug identification. You understand unit testing, 
integration testing, end-to-end testing, and performance testing. You write comprehensive test cases, 
identify edge cases, and ensure software quality. You can review code for potential issues, create test 
plans, write test scripts, and document bugs clearly. You help ensure that software is reliable, 
functional, and meets requirements before deployment.''',
                'settings': {
                    'temperature': 0.5,
                    'max_tokens': 2048,
                    'api_endpoint': 'http://localhost:11434'
                }
            }
        ]
        
        added_count = 0
        skipped_count = 0
        
        for agent in sample_agents:
            # Check if agent already exists
            cursor.execute("SELECT COUNT(*) FROM agents WHERE name = ?", (agent['name'],))
            exists = cursor.fetchone()[0] > 0
            
            if exists and not overwrite:
                print(f"  [-] Skipping '{agent['name']}' (already exists)")
                skipped_count += 1
                continue
            
            # Insert or update agent
            if exists and overwrite:
                cursor.execute('''
                    UPDATE agents 
                    SET model = ?, system_prompt = ?, settings = ?, updated_at = ?
                    WHERE name = ?
                ''', (
                    agent['model'],
                    agent['system_prompt'],
                    json.dumps(agent['settings']),
                    timestamp,
                    agent['name']
                ))
                print(f"  [OK] Updated agent: {agent['name']}")
            else:
                cursor.execute('''
                    INSERT INTO agents 
                    (name, model, system_prompt, settings, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    agent['name'],
                    agent['model'],
                    agent['system_prompt'],
                    json.dumps(agent['settings']),
                    timestamp,
                    timestamp
                ))
                print(f"  [OK] Added agent: {agent['name']} ({agent['model']})")
            
            added_count += 1
        
        # Commit changes
        conn.commit()
        
        # Show summary
        cursor.execute("SELECT COUNT(*) FROM agents")
        total_count = cursor.fetchone()[0]
        
        print(f"\n[SUCCESS] Database seeding complete!")
        print(f"   Agents added/updated: {added_count}")
        if skipped_count > 0:
            print(f"   Agents skipped: {skipped_count}")
        print(f"   Total agents in database: {total_count}")
        
        # List all agents
        print(f"\n[*] Agents in database:")
        cursor.execute("SELECT name, model, created_at FROM agents ORDER BY name")
        agents = cursor.fetchall()
        for name, model, created_at in agents:
            print(f"   - {name} ({model}) - Created: {created_at}")
        
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
        print("\n[OK] Seeding complete!")


def main():
    """Main entry point for the script."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Seed SQLite database with sample agents',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python seed_db.py                    # Add sample agents (skip existing)
  python seed_db.py --db custom.db     # Use custom database path
  python seed_db.py --overwrite         # Replace all existing agents
        """
    )
    
    parser.add_argument(
        '--db',
        type=str,
        default='data/agent.db',
        help='Path to SQLite database file (default: data/agent.db)'
    )
    
    parser.add_argument(
        '--overwrite',
        action='store_true',
        help='Delete existing agents before adding new ones (WARNING: This will delete all existing agents!)'
    )
    
    args = parser.parse_args()
    
    if args.overwrite:
        response = input("[!] WARNING: This will delete all existing agents. Continue? (yes/no): ")
        if response.lower() != 'yes':
            print("[CANCELLED] Operation cancelled")
            sys.exit(0)
    
    seed_database(db_path=args.db, overwrite=args.overwrite)


if __name__ == '__main__':
    main()

