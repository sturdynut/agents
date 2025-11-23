#!/usr/bin/env python3
"""
Test script to verify agent file writing capabilities.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.knowledge_base import KnowledgeBase
from src.message_bus import MessageBus
from src.agent_manager import AgentManager


def test_agent_file_write():
    """Test that an agent can write files using the tool calling system."""
    print("="*60)
    print("TESTING AGENT FILE WRITE CAPABILITIES")
    print("="*60)
    
    # Initialize components
    print("\n[1/4] Initializing components...")
    knowledge_base = KnowledgeBase()
    message_bus = MessageBus(knowledge_base)
    agent_manager = AgentManager(knowledge_base, message_bus)
    
    # Get Coder agent
    print("[2/4] Getting Coder agent...")
    coder = agent_manager.get_agent('Coder')
    if not coder:
        print("ERROR: Coder agent not found!")
        return False
    
    print(f"✓ Found agent: {coder.name}")
    
    # Test 1: Simple file write via chat
    print("\n[3/4] Testing file write via chat...")
    print("-"*60)
    test_message = '''Create a simple Python hello world script called hello.py in the agent_code folder.'''
    
    print(f"Sending message: {test_message}")
    response = coder.chat(test_message)
    print("\nAgent response:")
    print(response)
    print("-"*60)
    
    # Test 2: Check if file was created
    print("\n[4/4] Verifying file was created...")
    import os
    file_path = "agent_code/hello.py"
    
    if os.path.exists(file_path):
        print(f"✓ SUCCESS: File '{file_path}' was created!")
        with open(file_path, 'r') as f:
            content = f.read()
        print("\nFile contents:")
        print("-"*60)
        print(content)
        print("-"*60)
        return True
    else:
        print(f"✗ FAILURE: File '{file_path}' was NOT created")
        print("\nThe agent may not have used the write_file tool correctly.")
        return False


def main():
    """Main entry point."""
    try:
        success = test_agent_file_write()
        
        print("\n" + "="*60)
        if success:
            print("TEST PASSED: Agent can write files!")
        else:
            print("TEST FAILED: Agent cannot write files")
        print("="*60)
        
        sys.exit(0 if success else 1)
        
    except Exception as e:
        print(f"\nERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()

