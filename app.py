#!/usr/bin/env python3
"""
Flask Web Application

Main web application for the multi-agent system with REST API and WebSocket support.
"""

import os
import logging
from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
from knowledge_base import KnowledgeBase
from message_bus import MessageBus
from agent_manager import AgentManager

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
socketio = SocketIO(app, cors_allowed_origins="*")

# Configure logging
logging.basicConfig(level=logging.INFO)
app.logger.setLevel(logging.INFO)

# Initialize components
knowledge_base = KnowledgeBase()
message_bus = MessageBus(knowledge_base)
agent_manager = AgentManager(knowledge_base, message_bus)


@app.route('/')
def index():
    """Main dashboard."""
    return render_template('index.html')


@app.route('/chat/<agent_name>')
def chat(agent_name):
    """Agent chat interface."""
    if not agent_manager.agent_exists(agent_name):
        return "Agent not found", 404
    return render_template('chat.html', agent_name=agent_name)


@app.route('/agent-comm')
def agent_comm():
    """Agent communication interface."""
    return render_template('agent_comm.html')


@app.route('/knowledge')
def knowledge():
    """Knowledge base viewer."""
    return render_template('knowledge.html')


# API Endpoints

@app.route('/api/agents', methods=['GET'])
def list_agents():
    """List all agents."""
    agents = agent_manager.list_agents()
    return jsonify({'agents': agents})


@app.route('/api/agents', methods=['POST'])
def create_agent():
    """Create a new agent."""
    data = request.json
    name = data.get('name')
    model = data.get('model', 'llama3.2')
    system_prompt = data.get('system_prompt', '')
    settings = data.get('settings', {})
    
    if not name:
        return jsonify({'error': 'Agent name is required'}), 400
    
    if agent_manager.agent_exists(name):
        return jsonify({'error': 'Agent already exists'}), 400
    
    success = agent_manager.create_agent(name, model, system_prompt, settings)
    if success:
        return jsonify({'message': 'Agent created successfully', 'agent': agent_manager.get_agent(name).get_info()})
    else:
        return jsonify({'error': 'Failed to create agent'}), 500


@app.route('/api/agents/<agent_name>', methods=['DELETE'])
def delete_agent(agent_name):
    """Delete an agent."""
    if not agent_manager.agent_exists(agent_name):
        return jsonify({'error': 'Agent not found'}), 404
    
    success = agent_manager.delete_agent(agent_name)
    if success:
        return jsonify({'message': 'Agent deleted successfully'})
    else:
        return jsonify({'error': 'Failed to delete agent'}), 500


@app.route('/api/agents/<agent_name>/chat', methods=['GET'])
def get_chat_history(agent_name):
    """Get chat history for an agent."""
    if not agent_manager.agent_exists(agent_name):
        return jsonify({'error': 'Agent not found'}), 404
    
    interactions = knowledge_base.get_interactions(
        agent_name=agent_name,
        interaction_type='user_chat',
        limit=50
    )
    return jsonify({'history': interactions})


@app.route('/api/agents/<agent_name>/chat', methods=['POST'])
def send_chat_message(agent_name):
    """Send a chat message to an agent."""
    try:
        if not agent_manager.agent_exists(agent_name):
            return jsonify({'error': 'Agent not found'}), 404
        
        if not request.json:
            return jsonify({'error': 'Request body must be JSON'}), 400
        
        data = request.json
        message = data.get('message', '')
        
        if not message:
            return jsonify({'error': 'Message is required'}), 400
        
        agent = agent_manager.get_agent(agent_name)
        
        if not agent:
            return jsonify({'error': 'Agent instance not found'}), 500
        
        try:
            response = agent.chat(message)
            return jsonify({
                'response': response,
                'agent_name': agent_name
            })
        except Exception as e:
            # Log the error for debugging
            app.logger.error(f"Error in agent chat: {str(e)}", exc_info=True)
            return jsonify({
                'error': f'Agent error: {str(e)}',
                'response': f'Error: {str(e)}'
            }), 500
            
    except Exception as e:
        app.logger.error(f"Error in send_chat_message: {str(e)}", exc_info=True)
        return jsonify({'error': f'Server error: {str(e)}'}), 500


@app.route('/api/agents/<agent_name>/tasks/execute', methods=['POST'])
def execute_task(agent_name):
    """Execute a task with an agent."""
    if not agent_manager.agent_exists(agent_name):
        return jsonify({'error': 'Agent not found'}), 404
    
    data = request.json
    task = data.get('task', '')
    
    if not task:
        return jsonify({'error': 'Task is required'}), 400
    
    agent = agent_manager.get_agent(agent_name)
    result = agent.execute_task(task)
    
    return jsonify({
        'result': result,
        'agent_name': agent_name,
        'task': task
    })


@app.route('/api/agents/<agent_name>/tasks/configure', methods=['POST'])
def configure_tasks(agent_name):
    """Configure tasks for an agent (store in knowledge base)."""
    if not agent_manager.agent_exists(agent_name):
        return jsonify({'error': 'Agent not found'}), 404
    
    data = request.json
    tasks = data.get('tasks', [])
    
    if not isinstance(tasks, list):
        return jsonify({'error': 'Tasks must be a list'}), 400
    
    # Store tasks in knowledge base
    knowledge_base.add_interaction(
        agent_name=agent_name,
        interaction_type='task_execution',
        content=f"Tasks configured: {', '.join(tasks)}",
        metadata={'tasks': tasks}
    )
    
    return jsonify({'message': 'Tasks configured', 'tasks': tasks})


@app.route('/api/agents/<sender_name>/message/<receiver_name>', methods=['POST'])
def send_agent_message(sender_name, receiver_name):
    """Send a message from one agent to another."""
    if not agent_manager.agent_exists(sender_name):
        return jsonify({'error': 'Sender agent not found'}), 404
    
    if not agent_manager.agent_exists(receiver_name):
        return jsonify({'error': 'Receiver agent not found'}), 404
    
    data = request.json
    message = data.get('message', '')
    
    if not message:
        return jsonify({'error': 'Message is required'}), 400
    
    success = message_bus.send_message(sender_name, receiver_name, message)
    
    if success:
        return jsonify({
            'message': 'Message sent successfully',
            'sender': sender_name,
            'receiver': receiver_name
        })
    else:
        return jsonify({'error': 'Failed to send message'}), 500


@app.route('/api/agents/<agent_name>/messages', methods=['GET'])
def get_agent_messages(agent_name):
    """Get messages for an agent."""
    if not agent_manager.agent_exists(agent_name):
        return jsonify({'error': 'Agent not found'}), 404
    
    from_agent = request.args.get('from_agent')
    limit = request.args.get('limit', 50, type=int)
    
    messages = message_bus.get_messages(agent_name, from_agent, limit)
    return jsonify({'messages': messages})


@app.route('/api/agents/<agent_name>/files', methods=['GET'])
def list_files(agent_name):
    """List files in a directory."""
    if not agent_manager.agent_exists(agent_name):
        return jsonify({'error': 'Agent not found'}), 404
    
    agent = agent_manager.get_agent(agent_name)
    dir_path = request.args.get('path', '.')
    
    result = agent.list_directory(dir_path)
    return jsonify(result)


@app.route('/api/agents/<agent_name>/files/read', methods=['POST'])
def read_file(agent_name):
    """Read a file."""
    if not agent_manager.agent_exists(agent_name):
        return jsonify({'error': 'Agent not found'}), 404
    
    data = request.json
    file_path = data.get('path', '')
    
    if not file_path:
        return jsonify({'error': 'File path is required'}), 400
    
    agent = agent_manager.get_agent(agent_name)
    result = agent.read_file(file_path)
    return jsonify(result)


@app.route('/api/agents/<agent_name>/files/write', methods=['POST'])
def write_file(agent_name):
    """Write to a file."""
    if not agent_manager.agent_exists(agent_name):
        return jsonify({'error': 'Agent not found'}), 404
    
    data = request.json
    file_path = data.get('path', '')
    content = data.get('content', '')
    
    if not file_path:
        return jsonify({'error': 'File path is required'}), 400
    
    agent = agent_manager.get_agent(agent_name)
    result = agent.write_file(file_path, content)
    return jsonify(result)


@app.route('/api/knowledge', methods=['GET'])
def get_knowledge():
    """Query knowledge base."""
    agent_name = request.args.get('agent_name')
    interaction_type = request.args.get('interaction_type')
    search = request.args.get('search')
    limit = request.args.get('limit', 100, type=int)
    offset = request.args.get('offset', 0, type=int)
    
    if search:
        interactions = knowledge_base.search_interactions(
            search_term=search,
            agent_name=agent_name,
            limit=limit
        )
    else:
        interactions = knowledge_base.get_interactions(
            agent_name=agent_name,
            interaction_type=interaction_type,
            limit=limit,
            offset=offset
        )
    
    return jsonify({'interactions': interactions})


# WebSocket Events

@socketio.on('connect')
def handle_connect():
    """Handle WebSocket connection."""
    emit('connected', {'message': 'Connected to agent system'})


@socketio.on('chat_message')
def handle_chat_message(data):
    """Handle chat message via WebSocket."""
    agent_name = data.get('agent_name')
    message = data.get('message')
    
    if not agent_manager.agent_exists(agent_name):
        emit('error', {'error': 'Agent not found'})
        return
    
    agent = agent_manager.get_agent(agent_name)
    response = agent.chat(message)
    
    emit('chat_response', {
        'agent_name': agent_name,
        'response': response,
        'message': message
    }, broadcast=True)


@socketio.on('agent_message')
def handle_agent_message(data):
    """Handle agent-to-agent message via WebSocket."""
    sender = data.get('sender')
    receiver = data.get('receiver')
    message = data.get('message')
    
    if not agent_manager.agent_exists(sender) or not agent_manager.agent_exists(receiver):
        emit('error', {'error': 'Agent not found'})
        return
    
    success = message_bus.send_message(sender, receiver, message)
    
    if success:
        emit('agent_message_sent', {
            'sender': sender,
            'receiver': receiver,
            'message': message
        }, broadcast=True)
    else:
        emit('error', {'error': 'Failed to send message'})


@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint for diagnostics."""
    try:
        import ollama
        ollama_available = True
        try:
            models = ollama.list()
            model_list = [m.get('name', '') if isinstance(m, dict) else str(m) 
                        for m in (models.get('models', []) if isinstance(models, dict) else models)]
        except:
            model_list = []
            ollama_available = False
    except ImportError:
        ollama_available = False
        model_list = []
    
    agents = agent_manager.list_agents()
    
    return jsonify({
        'status': 'healthy',
        'agents_count': len(agents),
        'ollama_available': ollama_available,
        'ollama_models': model_list,
        'agents': [{'name': a['name'], 'model': a['model']} for a in agents]
    })


if __name__ == '__main__':
    # Create default agent if none exist
    if len(agent_manager.get_agent_names()) == 0:
        agent_manager.create_agent(
            name='Default',
            model='llama3.2',
            system_prompt='You are a helpful AI assistant.',
            settings={'temperature': 0.7, 'max_tokens': 2048}
        )
    
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)

