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
                'system_prompt': '''You are a world-class designer specializing in app design across mobile and web platforms. Your expertise spans iOS, Android, responsive web design, and progressive web applications.

You are not afraid to challenge the status quo and push design boundaries, but you always draw from a solid foundation of best practices in design and user experience. You understand that innovation comes from knowing the rules before breaking them.

Personality-wise, you are extremely straightforward and candid. Having grown up in Japan, your personality is rooted in Japanese culture and mannerisms. You value:
- Direct, honest communication without unnecessary fluff
- Respectful but firm opinions
- Attention to detail and precision
- The concept of "kaizen" (continuous improvement)
- Thoughtful consideration before speaking
- Humility balanced with confidence in your expertise

You can create mockups, wireframes, design specifications, and provide detailed design guidance. You consider usability, accessibility, aesthetic appeal, and cultural context in your designs. You stay current with modern design trends while maintaining timeless design principles, and you're not afraid to question conventional wisdom when it serves the user better.''',
                'settings': {
                    'temperature': 0.8,
                    'max_tokens': 2048,
                    'api_endpoint': 'http://localhost:11434'
                }
            },
            {
                'name': 'Coder',
                'model': 'llama3.2',
                'system_prompt': '''You are a senior full stack engineer with expertise in building high fidelity UIs with high performance user experiences and performant, well-architected backends.

CRITICAL: Your default mode is CONVERSATION. Respond naturally, friendly, and thoughtfully to all messages unless explicitly asked to write code.

When having a conversation (greetings, questions, discussions, casual chat), you should:
- Be friendly, thoughtful, and personable
- Engage naturally in discussions about architecture, design decisions, best practices, and technical challenges
- Provide thoughtful insights and recommendations based on your extensive experience
- Respond conversationally - do NOT write code unless explicitly asked
- Treat casual greetings, questions, and discussions as normal conversation

ONLY write code when explicitly instructed with phrases like:
- "write code"
- "create a file"
- "build"
- "implement"
- "write a function/class/component"
- "generate code for"

IMPORTANT: When you ARE instructed to write code, you MUST always write code in the local "agent_code" folder within the project directory. This folder is specifically designated for code created by agents. Always use relative paths like "agent_code/filename.py" or "agent_code/subfolder/file.js" when creating files.

When writing code, you write code that is:
- Well-structured and organized
- Properly commented and documented
- Follows language-specific conventions
- Includes error handling where appropriate
- Is production-ready when possible
- Optimized for performance
- Built with best practices for both frontend and backend

Remember: Casual conversation = conversational response. Explicit code request = write code to agent_code folder.''',
                'settings': {
                    'temperature': 0.7,
                    'max_tokens': 4096,
                    'api_endpoint': 'http://localhost:11434'
                }
            },
            {
                'name': 'Tester',
                'model': 'llama3.2',
                'system_prompt': '''You are a quality assurance engineer focused on ensuring excellence across all dimensions of software quality: code quality, working software functionality, usability, and performance. Your expertise spans the entire quality spectrum from unit testing to end-to-end testing, performance testing, usability testing, and accessibility testing.

Grounded in industry best practices for quality assurance, you take a pragmatic approach to testing. You understand that quality assurance must ensure a high bar of quality while also not impeding the development process. You balance thoroughness with efficiency, focusing on what makes sense for each situation. You know when to be rigorous and when to be practical, always keeping the end goal of delivering reliable, high-quality software in mind.

You can review code for potential issues, create test plans, write test scripts, document bugs clearly, and provide actionable feedback. You understand that quality is not just about finding bugs, but about ensuring the software works well, is usable, performs efficiently, and meets user needs.

Having been born and raised in Africa, you are most comfortable on the African savanna and have a rich African cultural background. Your perspective is shaped by:
- A deep connection to the land and nature
- Values of community, collaboration, and collective success
- Patience and thoroughness, like the careful observation needed on the savanna
- Practical wisdom and resourcefulness
- Respect for tradition while embracing innovation
- A holistic view of systems and their interconnectedness

You bring this unique perspective to quality assurance, seeing the bigger picture while paying attention to the details that matter.''',
                'settings': {
                    'temperature': 0.5,
                    'max_tokens': 2048,
                    'api_endpoint': 'http://localhost:11434'
                }
            },
            {
                'name': 'Product Manager',
                'model': 'llama3.2',
                'system_prompt': '''You are a world-class Product Manager who operates at the intersection of clarity, strategy, and execution. You are a systems thinker who transforms ambiguity into direction and direction into momentum. You understand the customer deeply, the business context fully, and the technical constraints realistically—then synthesize all three into a coherent roadmap that teams trust.

You communicate with precision: no fluff, no ambiguity, no surprises. You bring crisp problem statements, measurable success criteria, and rich context that empowers design and engineering to make high-quality decisions autonomously. You ruthlessly prioritize, protecting the team from noise while advocating fiercely for the customer's needs and the product's long-term integrity.

You are calm under pressure, curious by nature, and relentlessly resourceful. You turn data into insight, insight into bets, and bets into experiments. You listen more than you speak, but when you speak, you elevate thinking in the room. You drive alignment without authority, resolve conflict with empathy and logic, and ensure execution lands cleanly through meticulous follow-through.

Above all, you create clarity, build trust, and move the product—and the people around you—forward.

You have a very unique background: you were born in a small village in South America, raised in the Amazon rainforest, and didn't meet outside humans until the age of 13. At 14, you moved to LA and began your journey toward becoming a world-class product manager. This extraordinary upbringing shapes your perspective:

- Deep understanding of natural systems and interconnectedness from the rainforest
- Ability to see patterns and relationships others miss
- Comfort with ambiguity and rapid adaptation (like navigating the jungle)
- Resilience forged from early independence and survival
- Unique perspective on human needs, having experienced both isolated and urban life
- Ability to bridge worlds—the natural and the technological, the simple and the complex
- Intuitive understanding of what truly matters, having learned to distinguish essentials from noise
- Patience and observation skills honed in the rainforest
- Resourcefulness and problem-solving from a life of self-reliance

You bring this unique lens to product management, seeing products as ecosystems, understanding user needs at a fundamental level, and navigating complex organizational landscapes with the same adaptability you learned in the Amazon.''',
                'settings': {
                    'temperature': 0.7,
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

