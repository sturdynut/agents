#!/usr/bin/env python3
"""
Flask Web Application

Main web application for the multi-agent system with REST API and WebSocket support.
"""

import os
import logging
import threading
from datetime import datetime
from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
from knowledge_base import KnowledgeBase
from message_bus import MessageBus
from agent_manager import AgentManager
from conversation_orchestrator import ConversationOrchestrator

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
conversation_orchestrator = ConversationOrchestrator(
    agent_manager=agent_manager,
    knowledge_base=knowledge_base,
    message_bus=message_bus,
    orchestrator_model='llama3.2',
    orchestrator_settings={'temperature': 0.3, 'max_tokens': 2048}
)


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


@app.route('/api/agents/collaborate', methods=['POST'])
def start_agent_collaboration():
    """Start a multi-round collaboration with selected agents."""
    data = request.json
    objective = data.get('objective', '')
    rounds = data.get('rounds', 1)
    requested_agent_names = data.get('agent_names', [])
    
    if not objective:
        return jsonify({'error': 'Objective is required'}), 400
    
    if rounds < 1 or rounds > 20:
        return jsonify({'error': 'Rounds must be between 1 and 20'}), 400
    
    # Get selected agents or all agents if none specified
    if requested_agent_names:
        # Validate requested agents exist
        all_agents = agent_manager.list_agents()
        all_agent_names = [agent['name'] for agent in all_agents]
        agent_names = [name for name in requested_agent_names if name in all_agent_names]
        
        if len(agent_names) != len(requested_agent_names):
            invalid_names = set(requested_agent_names) - set(agent_names)
            return jsonify({'error': f'Invalid agent names: {", ".join(invalid_names)}'}), 400
    else:
        # Fallback to all agents if none specified
        all_agents = agent_manager.list_agents()
        agent_names = [agent['name'] for agent in all_agents]
    
    if len(agent_names) < 2:
        return jsonify({'error': 'At least 2 agents are required for collaboration'}), 400
    
    app.logger.info(f"Starting collaboration with {len(agent_names)} agents: {', '.join(agent_names)}")
    
    # Get agent instances and register them
    agents = {}
    for agent_name in agent_names:
        agent = agent_manager.get_agent(agent_name)
        if not agent:
            return jsonify({'error': f'Agent {agent_name} not found'}), 404
        agents[agent_name] = agent
        
        # Verify agents are registered in message bus
        if agent_name not in message_bus.agent_registry:
            app.logger.warning(f"Agent {agent_name} not in message bus registry, registering now")
            message_bus.register_agent(agent_name, agent)
    
    conversation_log = []
    total_turns = rounds * len(agent_names)
    
    # Build conversation context that all agents can see
    conversation_context = []
    
    try:
        turn = 0
        for round_num in range(rounds):
            app.logger.info(f"Round {round_num + 1}/{rounds}")
            
            # Each agent takes a turn in this round
            for agent_idx in range(len(agent_names)):
                turn += 1
                current_agent_name = agent_names[agent_idx]
                current_agent = agents[current_agent_name]
                
                app.logger.info(f"Turn {turn}/{total_turns}: {current_agent_name} taking turn")
                
                # Emit turn start event
                socketio.emit('collaboration_turn_start', {
                    'turn': turn,
                    'total_turns': total_turns,
                    'round': round_num + 1,
                    'total_rounds': rounds,
                    'agent': current_agent_name,
                    'status': f'{current_agent_name} is thinking...'
                })
                
                # Build context from previous conversation
                if conversation_context:
                    context_summary = "\n\nPrevious conversation:\n"
                    for msg in conversation_context[-5:]:  # Last 5 messages for context
                        context_summary += f"- {msg['sender']}: {msg['message'][:200]}...\n"
                    prompt = f"Your objective is: {objective}{context_summary}\n\nIt's your turn. What do you contribute towards achieving this objective?"
                else:
                    # First turn - first agent starts
                    prompt = f"Your objective is: {objective}\n\nPlease begin working towards this objective. Consider what needs to be done and take the first step."
                
                # Have the agent contribute
                try:
                    response = current_agent.chat(prompt)
                    app.logger.info(f"Received response from {current_agent_name} (length: {len(response) if response else 0})")
                except Exception as e:
                    error_msg = f'Error getting response from {current_agent_name} in turn {turn}: {str(e)}'
                    app.logger.error(error_msg, exc_info=True)
                    return jsonify({
                        'error': error_msg,
                        'conversation': conversation_log,
                        'failed_at_turn': turn
                    }), 500
                
                if not response:
                    error_msg = f'Empty response from {current_agent_name} in turn {turn}'
                    app.logger.error(error_msg)
                    return jsonify({
                        'error': error_msg,
                        'conversation': conversation_log,
                        'failed_at_turn': turn
                    }), 500
                
                # Store the contribution
                conversation_log.append({
                    'round': round_num + 1,
                    'turn': turn,
                    'sender': current_agent_name,
                    'message': response,
                    'timestamp': datetime.utcnow().isoformat()
                })
                
                conversation_context.append({
                    'sender': current_agent_name,
                    'message': response
                })
                
                # Store in knowledge base as agent chat
                knowledge_base.add_interaction(
                    agent_name=current_agent_name,
                    interaction_type='agent_chat',
                    content=f"Contribution towards objective: {response}",
                    metadata={'objective': objective, 'round': round_num + 1, 'turn': turn}
                )
                
                # Emit message event for real-time display
                socketio.emit('collaboration_message', {
                    'round': round_num + 1,
                    'total_rounds': rounds,
                    'turn': turn,
                    'total_turns': total_turns,
                    'sender': current_agent_name,
                    'message': response,
                    'timestamp': datetime.utcnow().isoformat()
                })
        
        app.logger.info(f"Collaboration completed successfully: {len(conversation_log)} messages")
        
        # Emit completion event
        socketio.emit('collaboration_complete', {
            'success': True,
            'total_rounds': rounds,
            'total_turns': turn,
            'messages_count': len(conversation_log),
            'agents': agent_names
        })
        
        return jsonify({
            'success': True,
            'conversation': conversation_log,
            'total_rounds': rounds,
            'total_turns': turn,
            'agents': agent_names,
            'agents_count': len(agent_names)
        })
    except Exception as e:
        error_msg = f'Error during collaboration: {str(e)}'
        app.logger.error(error_msg, exc_info=True)
        
        # Emit error event
        socketio.emit('collaboration_error', {
            'error': error_msg,
            'conversation': conversation_log
        })
        
        return jsonify({
            'error': error_msg,
            'conversation': conversation_log
        }), 500


@app.route('/api/agents/orchestrate', methods=['POST'])
def start_orchestrated_conversation():
    """Start an orchestrated conversation with intelligent routing."""
    data = request.json
    objective = data.get('objective', '')
    max_turns = data.get('max_turns', 20)
    requested_agent_names = data.get('agent_names', [])
    conversation_mode = data.get('conversation_mode', 'intelligent')  # 'intelligent' or 'round_robin'
    
    if not objective:
        return jsonify({'error': 'Objective is required'}), 400
    
    if max_turns < 1 or max_turns > 50:
        return jsonify({'error': 'Max turns must be between 1 and 50'}), 400
    
    # Get selected agents or all agents if none specified
    if requested_agent_names:
        # Validate requested agents exist
        all_agents = agent_manager.list_agents()
        all_agent_names = [agent['name'] for agent in all_agents]
        agent_names = [name for name in requested_agent_names if name in all_agent_names]
        
        if len(agent_names) != len(requested_agent_names):
            invalid_names = set(requested_agent_names) - set(agent_names)
            return jsonify({'error': f'Invalid agent names: {", ".join(invalid_names)}'}), 400
    else:
        # Fallback to all agents if none specified
        all_agents = agent_manager.list_agents()
        agent_names = [agent['name'] for agent in all_agents]
    
    if len(agent_names) < 1:
        return jsonify({'error': 'At least 1 agent is required for orchestrated conversation'}), 400
    
    app.logger.info(f"Starting orchestrated conversation with {len(agent_names)} agents: {', '.join(agent_names)}")
    
    # Check if resuming a session
    resume_session_id = data.get('resume_session_id')
    
    # Generate session ID if starting new
    if not resume_session_id:
        from datetime import datetime
        session_id = f"conv_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
    else:
        session_id = resume_session_id
    
    # Return immediately with session ID
    response_data = {
        'success': True,
        'conversation_id': session_id,
        'message': 'Session started, conversation will begin shortly',
        'status': 'starting'
    }
    
    # Define progress callback for real-time updates
    # This will be called from within the background task which has app context
    def progress_callback(msg_data):
        """Emit real-time progress updates via WebSocket."""
        try:
            # Handle agent thinking event
            if msg_data.get('type') == 'agent_thinking':
                app.logger.info(f"Emitting agent_thinking: {msg_data.get('agent')}")
                socketio.emit('agent_thinking', {
                    'agent': msg_data['agent'],
                    'turn': msg_data.get('turn', 1),
                    'session_id': session_id
                }, namespace='/')
                socketio.sleep(0.1)  # Small delay to ensure event is sent
                return
            
            # Handle regular message
            app.logger.info(f"Emitting orchestration_message: {msg_data.get('sender')} - turn {msg_data.get('turn')}")
            socketio.emit('orchestration_message', {
                'turn': msg_data['turn'],
                'sender': msg_data['sender'],
                'message': msg_data['message'],
                'timestamp': msg_data['timestamp'],
                'next_agent': msg_data.get('next_agent'),
                'responding_to': msg_data.get('responding_to'),
                'responding_to_message': msg_data.get('responding_to_message'),
                'session_id': session_id
            }, namespace='/')
            socketio.sleep(0.1)  # Small delay to ensure event is sent
            
            # Emit agent thinking event for next agent
            if msg_data.get('next_agent'):
                app.logger.info(f"Emitting agent_thinking for next: {msg_data.get('next_agent')}")
                socketio.emit('agent_thinking', {
                    'agent': msg_data['next_agent'],
                    'turn': msg_data['turn'] + 1,
                    'responding_to': msg_data['sender'],
                    'session_id': session_id
                }, namespace='/')
                socketio.sleep(0.1)  # Small delay to ensure event is sent
        except Exception as e:
            app.logger.error(f"Error in progress callback: {e}", exc_info=True)
    
    # Run conversation in background thread using SocketIO's background task
    def run_conversation():
        with app.app_context():
            try:
                result = conversation_orchestrator.start_orchestrated_conversation(
                    objective=objective,
                    max_turns=max_turns,
                    progress_callback=progress_callback,
                    agent_names=agent_names,
                    resume_session_id=resume_session_id,
                    conversation_id=session_id,
                    conversation_mode=conversation_mode
                )
                
                if result['success']:
                    # Emit completion event
                    app.logger.info(f"Emitting orchestration_complete: {result['conversation_id']}")
                    socketio.emit('orchestration_complete', {
                        'success': True,
                        'conversation_id': result['conversation_id'],
                        'total_turns': result['total_turns'],
                        'agents_used': result['agents_used'],
                        'messages_count': len(result['conversation'])
                    }, namespace='/')
                else:
                    # Emit error event
                    app.logger.error(f"Emitting orchestration_error: {result.get('error')}")
                    socketio.emit('orchestration_error', {
                        'error': result.get('error', 'Unknown error'),
                        'conversation': result.get('conversation', [])
                    }, namespace='/')
                    
            except Exception as e:
                error_msg = f'Error during orchestrated conversation: {str(e)}'
                app.logger.error(error_msg, exc_info=True)
                
                # Emit error event
                socketio.emit('orchestration_error', {
                    'error': error_msg,
                    'conversation': []
                }, namespace='/')
    
    # Emit a test event to verify WebSocket connection
    app.logger.info(f"Emitting session_started event for session {session_id}")
    socketio.emit('session_started', {
        'session_id': session_id,
        'message': 'Session started, waiting for first agent...'
    }, namespace='/')
    
    # Start conversation in background thread using SocketIO's background task
    socketio.start_background_task(run_conversation)
    
    return jsonify(response_data)


@app.route('/api/sessions', methods=['GET'])
def list_sessions():
    """List all conversation sessions."""
    status = request.args.get('status')
    limit = request.args.get('limit', 50, type=int)
    
    sessions = knowledge_base.list_sessions(status=status, limit=limit)
    return jsonify({'sessions': sessions})


@app.route('/api/sessions/<session_id>', methods=['GET'])
def get_session(session_id):
    """Get a specific conversation session."""
    session = knowledge_base.get_session(session_id)
    if not session:
        return jsonify({'error': 'Session not found'}), 404
    return jsonify({'session': session})


@app.route('/api/sessions/<session_id>', methods=['DELETE'])
def delete_session(session_id):
    """Delete a conversation session."""
    # For now, we'll mark it as deleted by updating status
    session = knowledge_base.get_session(session_id)
    if not session:
        return jsonify({'error': 'Session not found'}), 404
    
    knowledge_base.save_session(
        session_id=session_id,
        objective=session['objective'],
        agent_names=session['agent_names'],
        conversation_mode=session['conversation_mode'],
        conversation_history=session['conversation_history'],
        current_agent=session['current_agent'],
        total_turns=session['total_turns'],
        status='deleted'
    )
    
    return jsonify({'message': 'Session deleted'})


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
    
    socketio.run(app, host='0.0.0.0', port=5001, debug=True)

