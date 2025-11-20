// Chat interface JavaScript

// Get agent name from window (set by template) or use fallback
const agentName = window.agentName;

// Debug logging
console.log('Chat.js loaded. Agent name:', agentName);
console.log('Window.agentName:', window.agentName);

// Check if agentName is available
if (!agentName) {
    console.error('Cannot initialize chat: agentName is not defined');
    console.error('Available window properties:', Object.keys(window).filter(k => k.includes('agent')));
    document.addEventListener('DOMContentLoaded', () => {
        const chatMessages = document.getElementById('chatMessages');
        if (chatMessages) {
            chatMessages.innerHTML = '<div class="message agent-message error" style="color: red; padding: 10px;">Error: Agent name not found. Please go back and try again.</div>';
        }
    });
}

async function loadChatHistory() {
    if (!agentName) {
        console.error('Cannot load chat history: agentName is not defined');
        return;
    }
    try {
        const response = await fetch(`/api/agents/${agentName}/chat`);
        const data = await response.json();
        const messages = data.history || [];
        
        const chatMessages = document.getElementById('chatMessages');
        chatMessages.innerHTML = '';
        
        messages.reverse().forEach(interaction => {
            const messageDiv = document.createElement('div');
            messageDiv.className = 'message';
            
            const content = JSON.parse(interaction.content || '{}');
            const userMsg = content.user_message || '';
            const agentMsg = content.agent_response || '';
            
            if (userMsg) {
                const userMessageDiv = document.createElement('div');
                userMessageDiv.className = 'message user-message';
                userMessageDiv.textContent = userMsg;
                chatMessages.appendChild(userMessageDiv);
            }
            
            if (agentMsg) {
                const agentMessageDiv = document.createElement('div');
                agentMessageDiv.className = 'message agent-message';
                agentMessageDiv.textContent = agentMsg;
                chatMessages.appendChild(agentMessageDiv);
            }
        });
        
        chatMessages.scrollTop = chatMessages.scrollHeight;
    } catch (error) {
        console.error('Error loading chat history:', error);
    }
}

async function sendMessage(message) {
    if (!agentName) {
        console.error('Cannot send message: agentName is not defined');
        return 'Error: Agent name not found';
    }
    try {
        const response = await fetch(`/api/agents/${agentName}/chat`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ message })
        });
        
        // Check if response is OK before parsing
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({ error: 'Unknown error occurred' }));
            console.error('Server error:', errorData);
            return `Error: ${errorData.error || `HTTP ${response.status}`}`;
        }
        
        const data = await response.json();
        
        // Check if response field exists
        if (!data.response) {
            console.error('Unexpected response format:', data);
            return 'Error: Invalid response from server';
        }
        
        return data.response;
    } catch (error) {
        console.error('Error sending message:', error);
        return `Error: ${error.message || 'Failed to communicate with server'}`;
    }
}

function addMessageToChat(message, isUser = true) {
    const chatMessages = document.getElementById('chatMessages');
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${isUser ? 'user-message' : 'agent-message'}`;
    messageDiv.textContent = message;
    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// Wait for DOM to be ready
document.addEventListener('DOMContentLoaded', () => {
    console.log('DOM loaded, initializing chat interface...');
    
    // Chat input
    const chatInput = document.getElementById('chatInput');
    const sendBtn = document.getElementById('sendBtn');
    
    console.log('Chat elements found:', {
        chatInput: !!chatInput,
        sendBtn: !!sendBtn,
        agentName: agentName
    });
    
    if (!sendBtn) {
        console.error('Send button not found!');
        return;
    }
    
    if (!agentName) {
        console.error('Agent name not available!');
        sendBtn.disabled = true;
        sendBtn.textContent = 'Error: Agent not found';
        if (chatInput) {
            chatInput.disabled = true;
        }
        return;
    }

    if (sendBtn && agentName) {
        sendBtn.addEventListener('click', async () => {
        const message = chatInput.value.trim();
        if (!message) return;
        
        // Disable button and show loading
        sendBtn.disabled = true;
        sendBtn.textContent = 'Sending...';
        chatInput.disabled = true;
        
        addMessageToChat(message, true);
        chatInput.value = '';
        
        // Add loading message
        const loadingId = 'loading-' + Date.now();
        const loadingDiv = document.createElement('div');
        loadingDiv.id = loadingId;
        loadingDiv.className = 'message agent-message';
        loadingDiv.textContent = 'Thinking...';
        document.getElementById('chatMessages').appendChild(loadingDiv);
        document.getElementById('chatMessages').scrollTop = document.getElementById('chatMessages').scrollHeight;
        
        try {
            const response = await sendMessage(message);
            
            // Remove loading message
            const loadingMsg = document.getElementById(loadingId);
            if (loadingMsg) {
                loadingMsg.remove();
            }
            
            addMessageToChat(response, false);
        } catch (error) {
            // Remove loading message
            const loadingMsg = document.getElementById(loadingId);
            if (loadingMsg) {
                loadingMsg.remove();
            }
            
            addMessageToChat(`Error: ${error.message}`, false);
        } finally {
            // Re-enable button
            sendBtn.disabled = false;
            sendBtn.textContent = 'Send';
            chatInput.disabled = false;
            chatInput.focus();
        }
        });
    }
    
    if (chatInput && agentName && sendBtn) {
        chatInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                sendBtn.click();
            }
        });
    }
});

// Task execution - wrapped in DOMContentLoaded
document.addEventListener('DOMContentLoaded', () => {
    const executeTaskBtn = document.getElementById('executeTaskBtn');
    const taskInput = document.getElementById('taskInput');
    
    if (executeTaskBtn && agentName) {
        executeTaskBtn.addEventListener('click', async () => {
            const task = taskInput.value.trim();
            if (!task) {
                alert('Please enter a task');
                return;
            }
            
            try {
                const response = await fetch(`/api/agents/${agentName}/tasks/execute`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ task })
                });
                
                const data = await response.json();
                addMessageToChat(`Task: ${task}`, true);
                addMessageToChat(data.result, false);
                if (taskInput) taskInput.value = '';
            } catch (error) {
                alert('Error executing task: ' + error.message);
            }
        });
    }
});

// File operations - wrapped in DOMContentLoaded
document.addEventListener('DOMContentLoaded', () => {
    const readFileBtn = document.getElementById('readFileBtn');
    const listDirBtn = document.getElementById('listDirBtn');
    const filePath = document.getElementById('filePath');
    const fileResult = document.getElementById('fileResult');
    
    if (readFileBtn && agentName) {
        readFileBtn.addEventListener('click', async () => {
            const path = filePath ? filePath.value.trim() : '';
            if (!path) {
                alert('Please enter a file path');
                return;
            }
            
            try {
                const response = await fetch(`/api/agents/${agentName}/files/read`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ path })
                });
                
                const data = await response.json();
                if (fileResult) {
                    if (data.success) {
                        fileResult.innerHTML = `<pre>${data.content}</pre>`;
                    } else {
                        fileResult.innerHTML = `<p class="error">Error: ${data.error}</p>`;
                    }
                }
            } catch (error) {
                if (fileResult) {
                    fileResult.innerHTML = `<p class="error">Error: ${error.message}</p>`;
                }
            }
        });
    }
    
    if (listDirBtn && agentName) {
        listDirBtn.addEventListener('click', async () => {
            const path = filePath ? (filePath.value.trim() || '.') : '.';
            
            try {
                const response = await fetch(`/api/agents/${agentName}/files?path=${encodeURIComponent(path)}`);
                const data = await response.json();
                if (fileResult) {
                    if (data.success) {
                        const items = data.items.map(item => 
                            `${item.type === 'directory' ? '📁' : '📄'} ${item.name}${item.size ? ` (${item.size} bytes)` : ''}`
                        ).join('\n');
                        fileResult.innerHTML = `<pre>${items}</pre>`;
                    } else {
                        fileResult.innerHTML = `<p class="error">Error: ${data.error}</p>`;
                    }
                }
            } catch (error) {
                if (fileResult) {
                    fileResult.innerHTML = `<p class="error">Error: ${error.message}</p>`;
                }
            }
        });
    }
});

// Load agent info
async function loadAgentInfo() {
    try {
        const response = await fetch('/api/agents');
        const data = await response.json();
        const agent = data.agents.find(a => a.name === agentName);
        
        if (agent) {
            const agentModel = document.getElementById('agentModel');
            if (agentModel) {
                agentModel.textContent = `Model: ${agent.model}`;
            }
        }
    } catch (error) {
        console.error('Error loading agent info:', error);
    }
}

// Initialize only if agentName is available
if (agentName) {
    loadChatHistory();
    loadAgentInfo();
} else {
    console.error('Chat initialization failed: agentName is not defined');
    document.addEventListener('DOMContentLoaded', () => {
        const chatMessages = document.getElementById('chatMessages');
        const sendBtn = document.getElementById('sendBtn');
        const chatInput = document.getElementById('chatInput');
        
        if (chatMessages) {
            chatMessages.innerHTML = '<div class="message agent-message error" style="color: red; padding: 10px;">Error: Agent name not found. Please go back to the dashboard and try again.</div>';
        }
        if (sendBtn) {
            sendBtn.disabled = true;
            sendBtn.textContent = 'Error: Agent not found';
        }
        if (chatInput) {
            chatInput.disabled = true;
            chatInput.placeholder = 'Error: Agent name not found';
        }
    });
}

