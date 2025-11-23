#!/usr/bin/env python3
"""
Embedding Migration Script

Backfills embeddings for existing knowledge base interactions that don't have them.
Useful for migrating from the old knowledge base structure to the new semantic search system.
"""

import sys
import argparse
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.knowledge_base import KnowledgeBase


def migrate_embeddings(
    db_path: str = "data/agent.db",
    embedding_model: str = "nomic-embed-text",
    api_endpoint: str = "http://localhost:11434",
    batch_size: int = 50
):
    """Migrate existing knowledge base to include embeddings.
    
    Args:
        db_path: Path to the knowledge base database
        embedding_model: Ollama embedding model to use
        api_endpoint: Ollama API endpoint
        batch_size: Number of interactions to process at once
    """
    print("=" * 70)
    print("Knowledge Base Embedding Migration")
    print("=" * 70)
    print(f"Database: {db_path}")
    print(f"Embedding Model: {embedding_model}")
    print(f"API Endpoint: {api_endpoint}")
    print(f"Batch Size: {batch_size}")
    print("=" * 70)
    print()
    
    # Check if database exists
    if not Path(db_path).exists():
        print(f"❌ Error: Database not found at {db_path}")
        print("Make sure you have the correct path to your agent database.")
        return 1
    
    # Initialize knowledge base
    try:
        kb = KnowledgeBase(
            db_path=db_path,
            embedding_model=embedding_model,
            api_endpoint=api_endpoint
        )
        print("✅ Connected to knowledge base")
    except Exception as e:
        print(f"❌ Error connecting to knowledge base: {e}")
        return 1
    
    # Check for Ollama
    try:
        import ollama
        models = ollama.list()
        print("✅ Ollama is available")
        
        # Check if embedding model is available
        if isinstance(models, dict) and 'models' in models:
            available_models = [m.get('name', '') for m in models['models']]
        elif isinstance(models, list):
            available_models = [m.get('name', '') if isinstance(m, dict) else str(m) for m in models]
        else:
            available_models = []
        
        if embedding_model not in available_models:
            print(f"⚠️  Warning: Model '{embedding_model}' not found in Ollama")
            print(f"   Available models: {', '.join(available_models)}")
            print(f"   Please run: ollama pull {embedding_model}")
            
            response = input("\nContinue anyway? (y/N): ")
            if response.lower() != 'y':
                print("Migration cancelled")
                return 1
        else:
            print(f"✅ Embedding model '{embedding_model}' is available")
            
    except ImportError:
        print("❌ Error: Ollama package not installed")
        print("   Please run: pip install ollama")
        return 1
    except Exception as e:
        print(f"⚠️  Warning: Could not check Ollama status: {e}")
        print("   Continuing anyway...")
    
    print()
    print("Starting embedding generation...")
    print("-" * 70)
    
    # Run backfill
    try:
        count = kb.backfill_embeddings(batch_size=batch_size)
        print("-" * 70)
        print()
        
        if count > 0:
            print(f"✅ Successfully generated {count} embeddings!")
            print()
            print("Your knowledge base is now ready for semantic search.")
            print("Agents will now retrieve contextually relevant interactions")
            print("instead of just the most recent ones.")
        else:
            print("ℹ️  All interactions already have embeddings.")
            print("No migration needed.")
        
        return 0
        
    except Exception as e:
        print()
        print(f"❌ Error during migration: {e}")
        import traceback
        traceback.print_exc()
        return 1


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Backfill embeddings for existing knowledge base interactions"
    )
    parser.add_argument(
        "--db-path",
        default="data/agent.db",
        help="Path to knowledge base database (default: data/agent.db)"
    )
    parser.add_argument(
        "--embedding-model",
        default="nomic-embed-text",
        help="Ollama embedding model to use (default: nomic-embed-text)"
    )
    parser.add_argument(
        "--api-endpoint",
        default="http://localhost:11434",
        help="Ollama API endpoint (default: http://localhost:11434)"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=50,
        help="Number of interactions to process at once (default: 50)"
    )
    
    args = parser.parse_args()
    
    result = migrate_embeddings(
        db_path=args.db_path,
        embedding_model=args.embedding_model,
        api_endpoint=args.api_endpoint,
        batch_size=args.batch_size
    )
    
    sys.exit(result)


if __name__ == "__main__":
    main()

