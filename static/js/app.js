// Main application JavaScript

const API_BASE = '/api';

// Utility functions
async function apiRequest(endpoint, options = {}) {
    const response = await fetch(`${API_BASE}${endpoint}`, {
        headers: {
            'Content-Type': 'application/json',
            ...options.headers
        },
        ...options
    });
    
    if (!response.ok) {
        const error = await response.json();
        throw new Error(error.error || 'Request failed');
    }
    
    return response.json();
}

// Agent management
async function loadAgents() {
    try {
        const data = await apiRequest('/agents');
        return data.agents || [];
    } catch (error) {
        console.error('Error loading agents:', error);
        return [];
    }
}

async function createAgent(agentData) {
    return await apiRequest('/agents', {
        method: 'POST',
        body: JSON.stringify(agentData)
    });
}

async function deleteAgent(agentName) {
    return await apiRequest(`/agents/${agentName}`, {
        method: 'DELETE'
    });
}

// Dashboard functionality
if (document.getElementById('agentList')) {
    async function renderAgents() {
        const agents = await loadAgents();
        const agentList = document.getElementById('agentList');
        const agentCount = document.getElementById('agentCount');
        
        agentCount.textContent = agents.length;
        
        agentList.innerHTML = '';
        
        agents.forEach(agent => {
            const agentItem = document.createElement('div');
            agentItem.className = 'agent-item';
            agentItem.innerHTML = `
                <div class="agent-item-content">
                    <h3>${agent.name}</h3>
                    <p>Model: ${agent.model}</p>
                </div>
                <div class="agent-item-actions">
                    <a href="/chat/${agent.name}" class="btn btn-small">Chat</a>
                    <button class="btn btn-small btn-danger" onclick="deleteAgentHandler('${agent.name}')">Delete</button>
                </div>
            `;
            agentList.appendChild(agentItem);
        });
    }
    
    // Create agent modal
    const createAgentBtn = document.getElementById('createAgentBtn');
    const createAgentModal = document.getElementById('createAgentModal');
    const createAgentForm = document.getElementById('createAgentForm');
    const closeModal = document.querySelector('.close');
    
    if (createAgentBtn) {
        createAgentBtn.addEventListener('click', () => {
            createAgentModal.style.display = 'block';
        });
    }
    
    if (closeModal) {
        closeModal.addEventListener('click', () => {
            createAgentModal.style.display = 'none';
        });
    }
    
    if (createAgentForm) {
        createAgentForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const formData = new FormData(createAgentForm);
            const agentData = {
                name: formData.get('name'),
                model: formData.get('model') || 'llama3.2',
                system_prompt: formData.get('system_prompt') || '',
                settings: {
                    temperature: parseFloat(formData.get('temperature') || 0.7),
                    max_tokens: parseInt(formData.get('max_tokens') || 2048)
                }
            };
            
            try {
                await createAgent(agentData);
                createAgentModal.style.display = 'none';
                createAgentForm.reset();
                renderAgents();
            } catch (error) {
                alert('Error creating agent: ' + error.message);
            }
        });
    }
    
    async function deleteAgentHandler(agentName) {
        if (!confirm(`Are you sure you want to delete agent "${agentName}"?`)) {
            return;
        }
        
        try {
            await deleteAgent(agentName);
            renderAgents();
        } catch (error) {
            alert('Error deleting agent: ' + error.message);
        }
    }
    
    window.deleteAgentHandler = deleteAgentHandler;
    
    // Load agents on page load
    renderAgents();
    setInterval(renderAgents, 5000); // Refresh every 5 seconds
}

