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

async function loadStats() {
    try {
        const data = await apiRequest('/stats');
        return data;
    } catch (error) {
        console.error('Error loading stats:', error);
        return { agents_count: 0, messages_count: 0 };
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

async function updateAgent(agentName, agentData) {
    return await apiRequest(`/agents/${agentName}`, {
        method: 'PUT',
        body: JSON.stringify(agentData)
    });
}

async function getAgentDetails(agentName) {
    return await apiRequest(`/agents/${agentName}`);
}

// Dashboard functionality
if (document.getElementById('agentList')) {
    async function renderAgents() {
        const agents = await loadAgents();
        const stats = await loadStats();
        const agentList = document.getElementById('agentList');
        const agentCount = document.getElementById('agentCount');
        const messageCount = document.getElementById('messageCount');
        
        agentCount.textContent = stats.agents_count || agents.length;
        messageCount.textContent = stats.messages_count || 0;
        
        agentList.innerHTML = '';
        
        if (agents.length === 0) {
            agentList.innerHTML = `
                <div class="text-center py-12">
                    <svg class="w-16 h-16 mx-auto text-slate-300 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"></path>
                    </svg>
                    <p class="text-slate-500 text-lg">No agents yet</p>
                    <p class="text-slate-400 text-sm mt-1">Click "Create Agent" to get started</p>
                </div>
            `;
            return;
        }
        
        // Fetch detailed info for each agent including message count
        for (const agent of agents) {
            try {
                const detailsResponse = await getAgentDetails(agent.name);
                const agentDetails = detailsResponse.agent;
                
                const agentItem = document.createElement('div');
                agentItem.className = 'bg-gradient-to-br from-white to-slate-50 rounded-xl p-6 border border-slate-200 hover:shadow-lg transition-all duration-200';
                
                const systemPromptText = agentDetails.system_prompt || 'No system prompt set';
                
                // Generate tools display
                const allowedTools = agentDetails.allowed_tools || [];
                let toolsHtml = '';
                if (allowedTools.length === 0) {
                    toolsHtml = '<span class="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-700"><svg class="w-3 h-3 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636"></path></svg>No tools</span>';
                } else if (allowedTools.length === 3) {
                    toolsHtml = '<span class="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-green-100 text-green-700"><svg class="w-3 h-3 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path></svg>All tools</span>';
                } else {
                    const toolNames = allowedTools.map(t => t.replace('_', ' ')).join(', ');
                    toolsHtml = `<span class="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-amber-100 text-amber-700" title="${toolNames}"><svg class="w-3 h-3 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"></path><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"></path></svg>${allowedTools.length} tools</span>`;
                }
                
                agentItem.innerHTML = `
                    <div class="flex items-start justify-between mb-4">
                        <div class="flex-1">
                            <h3 class="text-xl font-bold text-slate-900 mb-2">${agentDetails.name}</h3>
                            <div class="flex flex-wrap gap-3 mb-3">
                                <span class="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-indigo-100 text-indigo-700">
                                    <svg class="w-3 h-3 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"></path>
                                    </svg>
                                    ${agentDetails.model}
                                </span>
                                <span class="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-700">
                                    <svg class="w-3 h-3 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"></path>
                                    </svg>
                                    ${agentDetails.message_count || 0} messages
                                </span>
                                <span class="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-purple-100 text-purple-700">
                                    <svg class="w-3 h-3 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"></path>
                                    </svg>
                                    Temp: ${agentDetails.settings?.temperature || 0.7}
                                </span>
                                ${toolsHtml}
                            </div>
                        </div>
                    </div>
                    
                    <div class="mb-4">
                        <p class="text-sm font-medium text-slate-700 mb-2">System Prompt:</p>
                        <div class="text-sm text-slate-600 bg-slate-50 rounded-lg p-4 border border-slate-200 min-h-[120px] max-h-[200px] overflow-y-auto whitespace-pre-wrap">${systemPromptText}</div>
                    </div>
                    
                    <div class="flex gap-2">
                        <a href="/chat/${agentDetails.name}" class="inline-flex items-center justify-center px-4 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium rounded-lg transition-colors duration-200 shadow-sm hover:shadow-md">
                            <svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"></path>
                            </svg>
                            Chat
                        </a>
                        <button onclick="editAgentHandler('${agentDetails.name}')" class="px-4 py-2.5 bg-slate-100 hover:bg-slate-200 text-slate-700 text-sm font-medium rounded-lg transition-colors duration-200">
                            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"></path>
                            </svg>
                        </button>
                        <button onclick="deleteAgentHandler('${agentDetails.name}')" class="px-4 py-2.5 bg-red-100 hover:bg-red-200 text-red-700 text-sm font-medium rounded-lg transition-colors duration-200">
                            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path>
                            </svg>
                        </button>
                    </div>
                `;
                agentList.appendChild(agentItem);
            } catch (error) {
                console.error(`Error loading details for agent ${agent.name}:`, error);
            }
        }
    }
    
    // Create agent modal
    const createAgentBtn = document.getElementById('createAgentBtn');
    const createAgentModal = document.getElementById('createAgentModal');
    const createAgentForm = document.getElementById('createAgentForm');
    const closeModal = document.querySelector('.close');
    
    if (createAgentBtn) {
        createAgentBtn.addEventListener('click', () => {
            createAgentModal.classList.remove('hidden');
        });
    }
    
    if (closeModal) {
        closeModal.addEventListener('click', () => {
            createAgentModal.classList.add('hidden');
        });
    }
    
    // Close modal when clicking outside
    if (createAgentModal) {
        createAgentModal.addEventListener('click', (e) => {
            if (e.target === createAgentModal) {
                createAgentModal.classList.add('hidden');
            }
        });
    }
    
    if (createAgentForm) {
        createAgentForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const formData = new FormData(createAgentForm);
            
            // Get selected tools
            const selectedTools = [];
            const toolCheckboxes = createAgentForm.querySelectorAll('input[name="tools"]:checked');
            toolCheckboxes.forEach(checkbox => {
                selectedTools.push(checkbox.value);
            });
            
            const agentData = {
                name: formData.get('name'),
                model: formData.get('model') || 'llama3.2',
                system_prompt: formData.get('system_prompt') || '',
                settings: {
                    temperature: parseFloat(formData.get('temperature') || 0.7),
                    max_tokens: parseInt(formData.get('max_tokens') || 2048)
                }
            };
            
            // Only add tools if some are selected (otherwise defaults to all tools)
            if (selectedTools.length > 0 && selectedTools.length < 3) {
                agentData.tools = selectedTools;
            }
            
            try {
                await createAgent(agentData);
                createAgentModal.classList.add('hidden');
                createAgentForm.reset();
                // Re-check all tool boxes by default
                createAgentForm.querySelectorAll('input[name="tools"]').forEach(cb => cb.checked = true);
                renderAgents();
            } catch (error) {
                alert('Error creating agent: ' + error.message);
            }
        });
    }
    
    // Edit agent modal
    const editAgentModal = document.getElementById('editAgentModal');
    const editAgentForm = document.getElementById('editAgentForm');
    const closeEditModal = document.querySelector('.close-edit');
    
    if (closeEditModal) {
        closeEditModal.addEventListener('click', () => {
            editAgentModal.classList.add('hidden');
        });
    }
    
    // Close edit modal when clicking outside
    if (editAgentModal) {
        editAgentModal.addEventListener('click', (e) => {
            if (e.target === editAgentModal) {
                editAgentModal.classList.add('hidden');
            }
        });
    }
    
    if (editAgentForm) {
        editAgentForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const formData = new FormData(editAgentForm);
            const originalName = formData.get('original_name');
            
            // Get selected tools
            const selectedTools = [];
            const toolCheckboxes = editAgentForm.querySelectorAll('input[name="tools"]:checked');
            toolCheckboxes.forEach(checkbox => {
                selectedTools.push(checkbox.value);
            });
            
            const agentData = {
                name: formData.get('name'),
                model: formData.get('model'),
                system_prompt: formData.get('system_prompt') || '',
                settings: {
                    temperature: parseFloat(formData.get('temperature') || 0.7),
                    max_tokens: parseInt(formData.get('max_tokens') || 2048)
                },
                tools: selectedTools
            };
            
            try {
                await updateAgent(originalName, agentData);
                editAgentModal.classList.add('hidden');
                editAgentForm.reset();
                renderAgents();
            } catch (error) {
                alert('Error updating agent: ' + error.message);
            }
        });
    }
    
    async function editAgentHandler(agentName) {
        try {
            const response = await getAgentDetails(agentName);
            const agent = response.agent;
            
            // Populate the form
            document.getElementById('editAgentOriginalName').value = agent.name;
            document.getElementById('editAgentName').value = agent.name;
            document.getElementById('editAgentModel').value = agent.model;
            document.getElementById('editSystemPrompt').value = agent.system_prompt || '';
            document.getElementById('editTemperature').value = agent.settings?.temperature || 0.7;
            document.getElementById('editMaxTokens').value = agent.settings?.max_tokens || 2048;
            
            // Populate tool checkboxes
            const allowedTools = agent.allowed_tools || ['write_file', 'read_file', 'list_directory'];
            document.getElementById('edit_tool_write_file').checked = allowedTools.includes('write_file');
            document.getElementById('edit_tool_read_file').checked = allowedTools.includes('read_file');
            document.getElementById('edit_tool_list_directory').checked = allowedTools.includes('list_directory');
            
            // Show the modal
            editAgentModal.classList.remove('hidden');
        } catch (error) {
            alert('Error loading agent details: ' + error.message);
        }
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
    
    window.editAgentHandler = editAgentHandler;
    window.deleteAgentHandler = deleteAgentHandler;
    
    // Load agents on page load
    renderAgents();
}

