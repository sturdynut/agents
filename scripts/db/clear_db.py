#!/usr/bin/env python3
"""
Database Clearing Script

Clears all agents and/or interactions from the database.
"""

import sqlite3
import os
import sys
from pathlib import Path


def clear_database(db_path: str = "data/agent.db", clear_agents: bool = True, clear_interactions: bool = False):
    """
    Clear the database.
    
    Args:
        db_path: Path to the SQLite database file
        clear_agents: If True, delete all agents
        clear_interactions: If True, delete all interactions/messages
    """
    # Check if database exists
    if not os.path.exists(db_path):
        print(f"[ERROR] Database not found at: {db_path}")
        sys.exit(1)
    
    # Connect to database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check if tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        if 'agents' not in tables and 'knowledge_base' not in tables:
            print(f"[ERROR] Database tables not found")
            sys.exit(1)
        
        deleted_agents = 0
        deleted_interactions = 0
        
        if clear_agents:
            if 'agents' in tables:
                cursor.execute("SELECT COUNT(*) FROM agents")
                count = cursor.fetchone()[0]
                if count > 0:
                    cursor.execute("DELETE FROM agents")
                    deleted_agents = count
                    print(f"[OK] Deleted {deleted_agents} agents")
                else:
                    print("[OK] No agents to delete")
            else:
                print("[!] Agents table not found")
        
        if clear_interactions:
            if 'knowledge_base' in tables:
                cursor.execute("SELECT COUNT(*) FROM knowledge_base")
                count = cursor.fetchone()[0]
                if count > 0:
                    cursor.execute("DELETE FROM knowledge_base")
                    deleted_interactions = count
                    print(f"[OK] Deleted {deleted_interactions} interactions")
                else:
                    print("[OK] No interactions to delete")
            else:
                print("[!] Knowledge base table not found")
        
        # Commit changes
        conn.commit()
        
        print(f"\n[SUCCESS] Database cleared!")
        if clear_agents:
            print(f"   Agents deleted: {deleted_agents}")
        if clear_interactions:
            print(f"   Interactions deleted: {deleted_interactions}")
        
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
        print("\n[OK] Database clearing complete!")


def main():
    """Main entry point for the script."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Clear SQLite database (agents and/or interactions)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python clear_db.py                    # Clear all agents (default)
  python clear_db.py --all              # Clear agents and interactions
  python clear_db.py --interactions     # Clear only interactions
  python clear_db.py --db custom.db     # Use custom database path
        """
    )
    
    parser.add_argument(
        '--db',
        type=str,
        default='data/agent.db',
        help='Path to SQLite database file (default: data/agent.db)'
    )
    
    parser.add_argument(
        '--agents',
        action='store_true',
        default=True,
        help='Clear agents (default: True)'
    )
    
    parser.add_argument(
        '--no-agents',
        action='store_false',
        dest='agents',
        help='Do not clear agents'
    )
    
    parser.add_argument(
        '--interactions',
        action='store_true',
        help='Clear interactions/messages'
    )
    
    parser.add_argument(
        '--all',
        action='store_true',
        help='Clear both agents and interactions'
    )
    
    parser.add_argument(
        '--yes',
        action='store_true',
        help='Skip confirmation prompt'
    )
    
    args = parser.parse_args()
    
    # Determine what to clear
    clear_agents = args.agents
    clear_interactions = args.interactions or args.all
    
    if args.all:
        clear_agents = True
        clear_interactions = True
    
    if not clear_agents and not clear_interactions:
        print("[ERROR] Nothing to clear. Use --agents, --interactions, or --all")
        sys.exit(1)
    
    # Confirmation
    if not args.yes:
        what = []
        if clear_agents:
            what.append("agents")
        if clear_interactions:
            what.append("interactions")
        
        response = input(f"[!] WARNING: This will delete all {', '.join(what)}. Continue? (yes/no): ")
        if response.lower() != 'yes':
            print("[CANCELLED] Operation cancelled")
            sys.exit(0)
    
    clear_database(
        db_path=args.db,
        clear_agents=clear_agents,
        clear_interactions=clear_interactions
    )


if __name__ == '__main__':
    main()

