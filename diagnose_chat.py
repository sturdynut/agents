#!/usr/bin/env python3
"""
Diagnostic script to check why agents aren't responding to chat.
Run this to identify common issues.
"""

import sys
import os

def check_ollama_installed():
    """Check if Ollama package is installed."""
    try:
        import ollama
        print("✅ Ollama package is installed")
        return True
    except ImportError:
        print("❌ Ollama package not installed")
        print("   Install with: pip install ollama")
        return False

def check_ollama_running():
    """Check if Ollama service is running."""
    try:
        import ollama
        models = ollama.list()
        print("✅ Ollama service is running")
        return True
    except Exception as e:
        print(f"❌ Cannot connect to Ollama: {str(e)}")
        print("   Make sure Ollama is running:")
        print("   - On Windows/Mac: Ollama should start automatically")
        print("   - On Linux: Run 'ollama serve' or check service status")
        return False

def check_models():
    """Check available models."""
    try:
        import ollama
        models = ollama.list()
        if isinstance(models, dict) and 'models' in models:
            model_list = [m.get('name', '') for m in models['models']]
        elif isinstance(models, list):
            model_list = [m.get('name', '') if isinstance(m, dict) else str(m) for m in models]
        else:
            model_list = []
        
        if model_list:
            print(f"✅ Found {len(model_list)} model(s):")
            for model in model_list:
                print(f"   - {model}")
        else:
            print("⚠️  No models found")
            print("   Download a model with: ollama pull llama3.2")
        return model_list
    except Exception as e:
        print(f"❌ Error checking models: {str(e)}")
        return []

def check_agent_system():
    """Check if agent system files exist."""
    required_files = [
        'agent_core.py',
        'agent_manager.py',
        'knowledge_base.py',
        'message_bus.py',
        'app.py'
    ]
    
    missing = []
    for file in required_files:
        if os.path.exists(file):
            print(f"✅ {file} exists")
        else:
            print(f"❌ {file} missing")
            missing.append(file)
    
    return len(missing) == 0

def check_database():
    """Check if knowledge base database exists."""
    db_path = "data/knowledge.db"
    if os.path.exists(db_path):
        print(f"✅ Knowledge base database exists at {db_path}")
        return True
    else:
        print(f"⚠️  Knowledge base database not found at {db_path}")
        print("   (This is OK - it will be created on first use)")
        return True

def test_agent_creation():
    """Test creating an agent."""
    try:
        from knowledge_base import KnowledgeBase
        from message_bus import MessageBus
        from agent_manager import AgentManager
        
        kb = KnowledgeBase()
        mb = MessageBus(kb)
        am = AgentManager(kb, mb)
        
        # Try to create a test agent
        success = am.create_agent(
            name='TestAgent',
            model='llama3.2',
            system_prompt='Test',
            settings={}
        )
        
        if success:
            print("✅ Agent creation works")
            # Clean up
            am.delete_agent('TestAgent')
            return True
        else:
            print("❌ Agent creation failed (agent may already exist)")
            return False
    except Exception as e:
        print(f"❌ Error testing agent creation: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all diagnostic checks."""
    print("=" * 60)
    print("Agent Chat Diagnostic Tool")
    print("=" * 60)
    print()
    
    print("1. Checking Ollama package...")
    ollama_installed = check_ollama_installed()
    print()
    
    if ollama_installed:
        print("2. Checking Ollama service...")
        ollama_running = check_ollama_running()
        print()
        
        if ollama_running:
            print("3. Checking available models...")
            models = check_models()
            print()
            
            if not models:
                print("⚠️  WARNING: No models available!")
                print("   Agents won't work without a model.")
                print("   Download one with: ollama pull llama3.2")
                print()
    
    print("4. Checking agent system files...")
    check_agent_system()
    print()
    
    print("5. Checking database...")
    check_database()
    print()
    
    print("6. Testing agent creation...")
    test_agent_creation()
    print()
    
    print("=" * 60)
    print("Diagnostic Complete")
    print("=" * 60)
    print()
    print("Common issues and solutions:")
    print("1. Ollama not running: Start Ollama service")
    print("2. No models: Run 'ollama pull llama3.2'")
    print("3. Wrong model name: Check agent's model matches downloaded model")
    print("4. Port conflict: Make sure port 5000 is available")
    print()
    print("To test the API directly:")
    print("  curl http://localhost:5000/api/health")
    print()

if __name__ == '__main__':
    main()

