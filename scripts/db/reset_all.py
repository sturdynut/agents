#!/usr/bin/env python3
"""
Full Database Reset Script

Completely resets the application by:
1. Deleting agent.db and knowledge.db
2. Re-initializing the database schema
3. Seeding with default agents

This gives you a clean slate to start fresh.
"""

import os
import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from scripts.db.init_db import init_database
from scripts.db.seed_db import seed_database


def reset_all(data_dir: str = "data", skip_confirm: bool = False):
    """
    Completely reset all databases and re-seed with default agents.
    
    Args:
        data_dir: Directory containing the database files
        skip_confirm: Skip confirmation prompt if True
    """
    agent_db = os.path.join(data_dir, "agent.db")
    knowledge_db = os.path.join(data_dir, "knowledge.db")
    
    print("=" * 60)
    print("FULL DATABASE RESET")
    print("=" * 60)
    print()
    print("This will:")
    print(f"  1. Delete {agent_db}")
    print(f"  2. Delete {knowledge_db}")
    print("  3. Re-create database schema")
    print("  4. Seed with default agents (Coder, Designer, PM, Tester)")
    print()
    
    if not skip_confirm:
        response = input("Are you sure you want to proceed? (yes/no): ")
        if response.lower() != 'yes':
            print("\n[CANCELLED] Operation cancelled")
            sys.exit(0)
    
    print()
    
    # Step 1: Delete existing databases
    print("[1/4] Removing existing databases...")
    
    if os.path.exists(agent_db):
        os.remove(agent_db)
        print(f"  ✓ Deleted {agent_db}")
    else:
        print(f"  - {agent_db} does not exist (skipping)")
    
    if os.path.exists(knowledge_db):
        os.remove(knowledge_db)
        print(f"  ✓ Deleted {knowledge_db}")
    else:
        print(f"  - {knowledge_db} does not exist (skipping)")
    
    print()
    
    # Step 2: Ensure data directory exists
    print("[2/4] Ensuring data directory exists...")
    os.makedirs(data_dir, exist_ok=True)
    print(f"  ✓ Data directory ready: {data_dir}")
    print()
    
    # Step 3: Initialize database schema
    print("[3/4] Initializing database schema...")
    print("-" * 40)
    init_database(db_path=agent_db, reset=False)
    print("-" * 40)
    print()
    
    # Step 4: Seed with default agents
    print("[4/4] Seeding database with default agents...")
    print("-" * 40)
    # Temporarily patch input to auto-confirm
    import builtins
    original_input = builtins.input
    builtins.input = lambda *args: 'yes'
    try:
        seed_database(db_path=agent_db, overwrite=False)
    finally:
        builtins.input = original_input
    print("-" * 40)
    print()
    
    # Summary
    print("=" * 60)
    print("✓ RESET COMPLETE!")
    print("=" * 60)
    print()
    print("Your application is now reset to a fresh state with:")
    print("  • Clean agent.db with default agents")
    print("  • Empty knowledge.db (will be created on first use)")
    print()
    print("Default agents created:")
    print("  • Coder (deepseek-coder) - Full stack engineer")
    print("  • Designer (deepseek-coder) - UI/UX designer")
    print("  • Product Manager (deepseek-coder) - PM")
    print("  • Tester (deepseek-coder) - QA engineer")
    print()
    print("All agents have these tools enabled:")
    print("  • write_file, read_file, create_folder, list_directory, web_search")
    print()
    print("Start the app with: python app.py")


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Completely reset the application databases',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python reset_all.py              # Reset with confirmation prompt
  python reset_all.py --yes        # Reset without confirmation
  python reset_all.py --data /path # Use custom data directory
        """
    )
    
    parser.add_argument(
        '--data',
        type=str,
        default='data',
        help='Path to data directory (default: data)'
    )
    
    parser.add_argument(
        '--yes', '-y',
        action='store_true',
        help='Skip confirmation prompt'
    )
    
    args = parser.parse_args()
    
    # Change to project root directory
    os.chdir(project_root)
    
    reset_all(data_dir=args.data, skip_confirm=args.yes)


if __name__ == '__main__':
    main()

