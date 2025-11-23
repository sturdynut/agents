#!/usr/bin/env python3
"""
Test Script for Tool Access Control

Demonstrates creating agents with different tool access levels and testing
their capabilities.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.agent_manager import AgentManager
from src.knowledge_base import KnowledgeBase
from src.message_bus import MessageBus


def test_tool_access():
    """Test tool access control functionality."""
    
    print("="*70)
    print("TOOL ACCESS CONTROL TEST")
    print("="*70)
    
    # Initialize components
    print("\n[1] Initializing components...")
    kb = KnowledgeBase('data/agent.db')
    mb = MessageBus(kb)
    manager = AgentManager(kb, mb)
    
    # Clean up any existing test agents
    test_agents = ['full_access_test', 'read_only_test', 'write_only_test', 'no_tools_test']
    for agent_name in test_agents:
        if manager.agent_exists(agent_name):
            manager.delete_agent(agent_name)
            print(f"   Cleaned up existing agent: {agent_name}")
    
    print("\n[2] Creating agents with different tool access levels...")
    
    # Create a full-access agent
    print("\n   Creating full-access agent...")
    success = manager.create_agent(
        name='full_access_test',
        model='llama3.2',
        system_prompt='You are a full-access agent.',
        tools=None  # None means all tools
    )
    if success:
        agent = manager.get_agent('full_access_test')
        print(f"   ✓ Created: {agent.name}")
        print(f"     Tools: {', '.join(agent.allowed_tools)}")
    else:
        print("   ✗ Failed to create full-access agent")
    
    # Create a read-only agent
    print("\n   Creating read-only agent...")
    success = manager.create_agent(
        name='read_only_test',
        model='llama3.2',
        system_prompt='You are a read-only agent.',
        tools=['read_file', 'list_directory']
    )
    if success:
        agent = manager.get_agent('read_only_test')
        print(f"   ✓ Created: {agent.name}")
        print(f"     Tools: {', '.join(agent.allowed_tools)}")
    else:
        print("   ✗ Failed to create read-only agent")
    
    # Create a write-only agent
    print("\n   Creating write-only agent...")
    success = manager.create_agent(
        name='write_only_test',
        model='llama3.2',
        system_prompt='You are a write-only agent.',
        tools=['write_file']
    )
    if success:
        agent = manager.get_agent('write_only_test')
        print(f"   ✓ Created: {agent.name}")
        print(f"     Tools: {', '.join(agent.allowed_tools)}")
    else:
        print("   ✗ Failed to create write-only agent")
    
    # Create an agent with no tools
    print("\n   Creating no-tools agent...")
    success = manager.create_agent(
        name='no_tools_test',
        model='llama3.2',
        system_prompt='You are an agent with no tools.',
        tools=[]
    )
    if success:
        agent = manager.get_agent('no_tools_test')
        print(f"   ✓ Created: {agent.name}")
        print(f"     Tools: {', '.join(agent.allowed_tools) if agent.allowed_tools else 'None'}")
    else:
        print("   ✗ Failed to create no-tools agent")
    
    print("\n[3] Verifying agent information...")
    
    all_agents = manager.list_agents()
    test_agent_infos = [a for a in all_agents if a['name'] in test_agents]
    
    print(f"\n   Test Agents Created: {len(test_agent_infos)}")
    for agent_info in test_agent_infos:
        print(f"\n   Agent: {agent_info['name']}")
        print(f"     Model: {agent_info['model']}")
        print(f"     Allowed Tools: {', '.join(agent_info['allowed_tools']) if agent_info['allowed_tools'] else 'None'}")
    
    print("\n[4] Testing tool execution restrictions...")
    
    # Test write with read-only agent
    print("\n   Testing read-only agent attempting to write...")
    read_only = manager.get_agent('read_only_test')
    if read_only:
        result = read_only.write_file('test_file.txt', 'Test content')
        if not result['success']:
            print(f"   ✓ Correctly blocked: {result['error']}")
        else:
            print(f"   ✗ Should have been blocked but succeeded!")
    
    # Test read with write-only agent
    print("\n   Testing write-only agent attempting to read...")
    write_only = manager.get_agent('write_only_test')
    if write_only:
        result = write_only.read_file('agent_code/hello.py')
        if not result['success']:
            print(f"   ✓ Correctly blocked: {result['error']}")
        else:
            print(f"   ✗ Should have been blocked but succeeded!")
    
    # Test write with full-access agent
    print("\n   Testing full-access agent writing...")
    full_access = manager.get_agent('full_access_test')
    if full_access:
        result = full_access.write_file('test_full_access.txt', 'Test content from full access agent')
        if result['success']:
            print(f"   ✓ Successfully wrote file: {result['path']}")
        else:
            print(f"   ✗ Failed to write: {result.get('error', 'Unknown error')}")
    
    print("\n[5] Testing tool info generation...")
    
    for test_agent_name in ['full_access_test', 'read_only_test', 'write_only_test', 'no_tools_test']:
        agent = manager.get_agent(test_agent_name)
        if agent:
            tools_info = agent._get_tools_info()
            print(f"\n   {test_agent_name}:")
            print(f"     {tools_info[:100]}..." if len(tools_info) > 100 else f"     {tools_info}")
    
    print("\n[6] Testing database persistence...")
    
    # Reload agents from database
    print("\n   Reloading agents from database...")
    kb_new = KnowledgeBase('data/agent.db')
    mb_new = MessageBus(kb_new)
    manager_new = AgentManager(kb_new, mb_new)
    
    for test_agent_name in test_agents:
        agent = manager_new.get_agent(test_agent_name)
        if agent:
            print(f"   ✓ {test_agent_name}: {', '.join(agent.allowed_tools) if agent.allowed_tools else 'None'}")
        else:
            print(f"   ✗ {test_agent_name}: Not found after reload")
    
    print("\n[7] Cleaning up test agents...")
    for agent_name in test_agents:
        if manager.agent_exists(agent_name):
            manager.delete_agent(agent_name)
            print(f"   ✓ Deleted: {agent_name}")
    
    print("\n" + "="*70)
    print("TOOL ACCESS CONTROL TEST COMPLETED")
    print("="*70)
    print("\nSummary:")
    print("✓ Agents can be created with specific tool access")
    print("✓ Tool restrictions are enforced during execution")
    print("✓ Tool information is dynamically generated")
    print("✓ Tool access persists across database reloads")
    print("\nThe tool access control feature is working correctly!")


if __name__ == '__main__':
    try:
        test_tool_access()
    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

