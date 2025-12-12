#!/usr/bin/env python3
"""
Database Migration Script: Add Tools Column

Adds a 'tools' column to the agents table to store allowed tools for each agent.
"""

import sqlite3
import os
import sys
import json
from pathlib import Path


def add_tools_column(db_path: str = "data/agent.db"):
    """
    Add tools column to agents table.
    
    Args:
        db_path: Path to the SQLite database file
    """
    if not os.path.exists(db_path):
        print(f"[ERROR] Database not found at: {db_path}")
        sys.exit(1)
    
    # Connect to database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        print(f"[*] Connecting to database: {db_path}")
        
        # Check if column already exists
        cursor.execute("PRAGMA table_info(agents)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'tools' in columns:
            print("[!] Column 'tools' already exists in agents table")
            print("[OK] No migration needed")
            return
        
        # Add tools column
        print("[*] Adding 'tools' column to agents table...")
        cursor.execute('''
            ALTER TABLE agents 
            ADD COLUMN tools TEXT DEFAULT NULL
        ''')
        
        # Set default tools for existing agents (all tools enabled)
        default_tools = json.dumps(['write_file', 'read_file', 'create_folder', 'list_directory', 'web_search'])
        print("[*] Setting default tools for existing agents...")
        cursor.execute('''
            UPDATE agents 
            SET tools = ? 
            WHERE tools IS NULL
        ''', (default_tools,))
        
        affected_rows = cursor.rowcount
        
        # Commit changes
        conn.commit()
        
        print(f"[OK] Column 'tools' added successfully")
        print(f"[OK] Updated {affected_rows} existing agent(s) with default tools")
        
        # Verify the change
        cursor.execute("PRAGMA table_info(agents)")
        columns = cursor.fetchall()
        print("\n[*] Updated agents table schema:")
        for col in columns:
            print(f"     - {col[1]} ({col[2]})")
        
        print("\n[SUCCESS] Migration completed successfully!")
        
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


def main():
    """Main entry point for the script."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Add tools column to agents table',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python add_tools_column.py                    # Use default database path
  python add_tools_column.py --db custom.db     # Use custom database path
        """
    )
    
    parser.add_argument(
        '--db',
        type=str,
        default='data/agent.db',
        help='Path to SQLite database file (default: data/agent.db)'
    )
    
    args = parser.parse_args()
    
    add_tools_column(db_path=args.db)


if __name__ == '__main__':
    main()

