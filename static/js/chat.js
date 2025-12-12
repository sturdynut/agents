// Chat interface JavaScript

// Get agent name from window (set by template) or use fallback
const agentName = window.agentName;

// Helper to get avatar URL
function getAvatarUrl() {
    return `/api/avatar/${encodeURIComponent(agentName)}`;
}

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
            chatMessages.innerHTML = '<div class="flex justify-start"><div class="max-w-[70%] bg-red-50 text-red-700 rounded-2xl rounded-bl-sm px-4 py-3 shadow-sm"><p class="text-sm">Error: Agent name not found. Please go back and try again.</p></div></div>';
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
            const content = JSON.parse(interaction.content || '{}');
            const userMsg = content.user_message || '';
            const agentMsg = content.agent_response || '';
            
            if (userMsg) {
                const userMessageDiv = document.createElement('div');
                userMessageDiv.className = 'flex justify-end';
                userMessageDiv.innerHTML = `
                    <div class="max-w-[70%] bg-indigo-600 text-white rounded-2xl rounded-br-sm px-4 py-3 shadow-sm">
                        <p class="text-sm whitespace-pre-wrap">${userMsg}</p>
                    </div>
                `;
                chatMessages.appendChild(userMessageDiv);
            }
            
            if (agentMsg) {
                const agentMessageDiv = document.createElement('div');
                agentMessageDiv.className = 'flex justify-start items-end gap-2';
                agentMessageDiv.innerHTML = `
                    <img src="${getAvatarUrl()}" alt="${agentName}" class="w-8 h-8 rounded-full flex-shrink-0 shadow-sm">
                    <div class="max-w-[70%] bg-slate-100 dark:bg-slate-700 text-slate-900 dark:text-white rounded-2xl rounded-bl-sm px-4 py-3 shadow-sm">
                        <p class="text-sm whitespace-pre-wrap">${agentMsg}</p>
                    </div>
                `;
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
    
    if (isUser) {
        messageDiv.className = 'flex justify-end';
        messageDiv.innerHTML = `
            <div class="max-w-[70%] bg-indigo-600 text-white rounded-2xl rounded-br-sm px-4 py-3 shadow-sm">
                <p class="text-sm whitespace-pre-wrap">${message}</p>
            </div>
        `;
    } else {
        messageDiv.className = 'flex justify-start items-end gap-2';
        messageDiv.innerHTML = `
            <img src="${getAvatarUrl()}" alt="${agentName}" class="w-8 h-8 rounded-full flex-shrink-0 shadow-sm">
            <div class="max-w-[70%] bg-slate-100 dark:bg-slate-700 text-slate-900 dark:text-white rounded-2xl rounded-bl-sm px-4 py-3 shadow-sm">
                <p class="text-sm whitespace-pre-wrap">${message}</p>
            </div>
        `;
    }
    
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
        chatInput.style.height = 'auto';
        
        // Add loading message with avatar
        const loadingId = 'loading-' + Date.now();
        const loadingDiv = document.createElement('div');
        loadingDiv.id = loadingId;
        loadingDiv.className = 'flex justify-start items-end gap-2';
        loadingDiv.innerHTML = `
            <img src="${getAvatarUrl()}" alt="${agentName}" class="w-8 h-8 rounded-full flex-shrink-0 shadow-sm">
            <div class="max-w-[70%] bg-slate-100 dark:bg-slate-700 text-slate-900 dark:text-white rounded-2xl rounded-bl-sm px-4 py-3 shadow-sm">
                <div class="flex items-center gap-2">
                    <div class="flex gap-1">
                        <div class="w-2 h-2 bg-indigo-500 rounded-full animate-bounce" style="animation-delay: 0ms"></div>
                        <div class="w-2 h-2 bg-indigo-500 rounded-full animate-bounce" style="animation-delay: 150ms"></div>
                        <div class="w-2 h-2 bg-indigo-500 rounded-full animate-bounce" style="animation-delay: 300ms"></div>
                    </div>
                    <p class="text-sm text-slate-500 dark:text-slate-400">Thinking...</p>
                </div>
            </div>
        `;
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
        // Handle Enter to send, Shift+Enter for new line
        chatInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendBtn.click();
            }
        });
        
        // Auto-resize textarea as user types
        chatInput.addEventListener('input', () => {
            chatInput.style.height = 'auto';
            chatInput.style.height = Math.min(chatInput.scrollHeight, 200) + 'px';
        });
        
        // Handle paste events for auto-resize
        chatInput.addEventListener('paste', () => {
            setTimeout(() => {
                chatInput.style.height = 'auto';
                chatInput.style.height = Math.min(chatInput.scrollHeight, 200) + 'px';
            }, 0);
        });
    }
});

// Task Modal and Execution - wrapped in DOMContentLoaded
document.addEventListener('DOMContentLoaded', () => {
    const addTaskBtn = document.getElementById('addTaskBtn');
    const taskModal = document.getElementById('taskModal');
    const taskModalBackdrop = document.getElementById('taskModalBackdrop');
    const closeTaskModal = document.getElementById('closeTaskModal');
    const cancelTaskBtn = document.getElementById('cancelTaskBtn');
    const executeTaskBtn = document.getElementById('executeTaskBtn');
    const executeTaskBtnText = document.getElementById('executeTaskBtnText');
    const taskInput = document.getElementById('taskInput');
    
    // Open modal
    if (addTaskBtn && taskModal) {
        addTaskBtn.addEventListener('click', () => {
            taskModal.classList.remove('hidden');
            if (taskInput) {
                taskInput.value = '';
                taskInput.focus();
            }
        });
    }
    
    // Close modal functions
    function closeModal() {
        if (taskModal) {
            taskModal.classList.add('hidden');
        }
    }
    
    if (closeTaskModal) {
        closeTaskModal.addEventListener('click', closeModal);
    }
    
    if (cancelTaskBtn) {
        cancelTaskBtn.addEventListener('click', closeModal);
    }
    
    if (taskModalBackdrop) {
        taskModalBackdrop.addEventListener('click', closeModal);
    }
    
    // Close on Escape key
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && taskModal && !taskModal.classList.contains('hidden')) {
            closeModal();
        }
    });
    
    // Execute task
    if (executeTaskBtn && agentName) {
        executeTaskBtn.addEventListener('click', async () => {
            const task = taskInput ? taskInput.value.trim() : '';
            if (!task) {
                alert('Please enter a task');
                return;
            }
            
            // Show loading state
            executeTaskBtn.disabled = true;
            if (executeTaskBtnText) {
                executeTaskBtnText.textContent = 'Executing...';
            }
            executeTaskBtn.classList.add('opacity-75', 'cursor-not-allowed');
            
            // Close modal and show task in chat
            closeModal();
            
            // Add task message to chat
            addMessageToChat(`🎯 Task: ${task}`, true);
            
            // Add loading indicator in chat with avatar
            const loadingId = 'task-loading-' + Date.now();
            const loadingDiv = document.createElement('div');
            loadingDiv.id = loadingId;
            loadingDiv.className = 'flex justify-start items-end gap-2';
            loadingDiv.innerHTML = `
                <img src="${getAvatarUrl()}" alt="${agentName}" class="w-8 h-8 rounded-full flex-shrink-0 shadow-sm">
                <div class="max-w-[70%] bg-amber-50 dark:bg-amber-900/20 text-amber-800 dark:text-amber-200 rounded-2xl rounded-bl-sm px-4 py-3 shadow-sm border border-amber-200 dark:border-amber-800">
                    <div class="flex items-center gap-3">
                        <div class="flex gap-1">
                            <div class="w-2 h-2 bg-amber-500 rounded-full animate-bounce" style="animation-delay: 0ms"></div>
                            <div class="w-2 h-2 bg-amber-500 rounded-full animate-bounce" style="animation-delay: 150ms"></div>
                            <div class="w-2 h-2 bg-amber-500 rounded-full animate-bounce" style="animation-delay: 300ms"></div>
                        </div>
                        <p class="text-sm font-medium">Executing task... This may take a moment.</p>
                    </div>
                </div>
            `;
            document.getElementById('chatMessages').appendChild(loadingDiv);
            document.getElementById('chatMessages').scrollTop = document.getElementById('chatMessages').scrollHeight;
            
            try {
                const response = await fetch(`/api/agents/${agentName}/tasks/execute`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ task })
                });
                
                const data = await response.json();
                
                // Remove loading message
                const loadingMsg = document.getElementById(loadingId);
                if (loadingMsg) {
                    loadingMsg.remove();
                }
                
                // Add result to chat with special styling and avatar
                const resultDiv = document.createElement('div');
                resultDiv.className = 'flex justify-start items-end gap-2';
                resultDiv.innerHTML = `
                    <img src="${getAvatarUrl()}" alt="${agentName}" class="w-8 h-8 rounded-full flex-shrink-0 shadow-sm">
                    <div class="max-w-[70%] bg-slate-100 dark:bg-slate-700 text-slate-900 dark:text-white rounded-2xl rounded-bl-sm px-4 py-3 shadow-sm">
                        <div class="flex items-center gap-2 mb-2 text-xs text-amber-600 dark:text-amber-400 font-medium">
                            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                            </svg>
                            Task Completed
                        </div>
                        <p class="text-sm whitespace-pre-wrap">${data.result || data.error || 'Task completed'}</p>
                    </div>
                `;
                document.getElementById('chatMessages').appendChild(resultDiv);
                document.getElementById('chatMessages').scrollTop = document.getElementById('chatMessages').scrollHeight;
                
                if (taskInput) taskInput.value = '';
            } catch (error) {
                // Remove loading message
                const loadingMsg = document.getElementById(loadingId);
                if (loadingMsg) {
                    loadingMsg.remove();
                }
                
                addMessageToChat(`❌ Error executing task: ${error.message}`, false);
            } finally {
                // Reset button state
                executeTaskBtn.disabled = false;
                if (executeTaskBtnText) {
                    executeTaskBtnText.textContent = 'Execute Task';
                }
                executeTaskBtn.classList.remove('opacity-75', 'cursor-not-allowed');
            }
        });
    }
    
    // Allow Enter+Ctrl/Cmd to submit task
    if (taskInput) {
        taskInput.addEventListener('keydown', (e) => {
            if ((e.ctrlKey || e.metaKey) && e.key === 'Enter' && executeTaskBtn) {
                executeTaskBtn.click();
            }
        });
    }
});

// Tool display configuration with full Tailwind classes
const TOOL_STYLES = {
    write_file: { 
        label: 'Write', 
        classes: 'bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-400' 
    },
    read_file: { 
        label: 'Read', 
        classes: 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400' 
    },
    create_folder: { 
        label: 'Folder', 
        classes: 'bg-teal-100 dark:bg-teal-900/30 text-teal-700 dark:text-teal-400' 
    },
    list_directory: { 
        label: 'List', 
        classes: 'bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400' 
    },
    web_search: { 
        label: 'Search', 
        classes: 'bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-400' 
    }
};

// Current agent's model (for tracking changes)
let currentAgentModel = null;

// Load available models and populate selector
async function loadModelsForSelector(selectedModel) {
    const modelSelector = document.getElementById('modelSelector');
    if (!modelSelector) return;
    
    try {
        const response = await fetch('/api/models');
        const data = await response.json();
        const models = data.models || [];
        
        modelSelector.innerHTML = '';
        
        // Group models: installed first, then not installed
        const installedModels = models.filter(m => m.installed);
        const notInstalledModels = models.filter(m => !m.installed);
        
        // Helper to check if model matches selected
        const modelMatches = (modelName, selected) => {
            if (!selected) return false;
            const modelBase = modelName.split(':')[0];
            const selectedBase = selected.split(':')[0];
            return modelName === selected || modelBase === selectedBase;
        };
        
        // Add installed models group
        if (installedModels.length > 0) {
            const installedGroup = document.createElement('optgroup');
            installedGroup.label = '✓ Installed Models';
            installedModels.forEach(model => {
                const option = document.createElement('option');
                option.value = model.name;
                option.textContent = `${model.name} (${model.size})`;
                if (modelMatches(model.name, selectedModel)) {
                    option.selected = true;
                }
                installedGroup.appendChild(option);
            });
            modelSelector.appendChild(installedGroup);
        }
        
        // Add not installed models group
        if (notInstalledModels.length > 0) {
            const notInstalledGroup = document.createElement('optgroup');
            notInstalledGroup.label = '↓ Available to Download';
            notInstalledModels.forEach(model => {
                const option = document.createElement('option');
                option.value = model.name;
                option.textContent = `${model.name} (${model.size})`;
                option.classList.add('text-slate-400');
                if (modelMatches(model.name, selectedModel)) {
                    option.selected = true;
                }
                notInstalledGroup.appendChild(option);
            });
            modelSelector.appendChild(notInstalledGroup);
        }
        
        // If selected model not found in list, add it as custom option
        if (selectedModel && !modelSelector.value) {
            const customOption = document.createElement('option');
            customOption.value = selectedModel;
            customOption.textContent = `${selectedModel} (current)`;
            customOption.selected = true;
            modelSelector.insertBefore(customOption, modelSelector.firstChild);
        }
        
    } catch (error) {
        console.error('Error loading models:', error);
        modelSelector.innerHTML = '<option value="">Error loading models</option>';
    }
}

// Handle model change
async function handleModelChange(newModel) {
    if (!agentName || !newModel || newModel === currentAgentModel) return;
    
    const modelSelector = document.getElementById('modelSelector');
    const saveStatus = document.getElementById('modelSaveStatus');
    
    // Show saving state
    if (modelSelector) {
        modelSelector.disabled = true;
    }
    if (saveStatus) {
        saveStatus.textContent = 'Saving...';
        saveStatus.classList.remove('opacity-0', 'text-green-600', 'dark:text-green-400', 'text-red-600', 'dark:text-red-400');
        saveStatus.classList.add('text-slate-500');
    }
    
    try {
        const response = await fetch(`/api/agents/${encodeURIComponent(agentName)}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ model: newModel })
        });
        
        if (!response.ok) {
            throw new Error(`Failed to update model: ${response.statusText}`);
        }
        
        const data = await response.json();
        currentAgentModel = newModel;
        
        // Show success
        if (saveStatus) {
            saveStatus.textContent = '✓ Saved';
            saveStatus.classList.remove('text-slate-500');
            saveStatus.classList.add('text-green-600', 'dark:text-green-400');
            
            // Fade out after 2 seconds
            setTimeout(() => {
                saveStatus.classList.add('opacity-0');
            }, 2000);
        }
        
        console.log(`Model changed to: ${newModel}`);
        
    } catch (error) {
        console.error('Error updating model:', error);
        
        // Show error and revert selection
        if (saveStatus) {
            saveStatus.textContent = '✗ Error';
            saveStatus.classList.remove('text-slate-500');
            saveStatus.classList.add('text-red-600', 'dark:text-red-400');
        }
        
        // Revert to previous model
        if (modelSelector && currentAgentModel) {
            modelSelector.value = currentAgentModel;
        }
        
    } finally {
        if (modelSelector) {
            modelSelector.disabled = false;
        }
    }
}

// Load agent info
async function loadAgentInfo() {
    try {
        const response = await fetch('/api/agents');
        const data = await response.json();
        const agent = data.agents.find(a => a.name === agentName);
        
        if (agent) {
            currentAgentModel = agent.model;
            
            // Load models into selector
            await loadModelsForSelector(agent.model);
            
            // Display tools
            const agentTools = document.getElementById('agentTools');
            if (agentTools) {
                const tools = agent.allowed_tools || ['write_file', 'read_file', 'create_folder', 'list_directory', 'web_search'];
                
                if (tools.length === 0) {
                    agentTools.innerHTML = '<span class="text-xs px-2 py-0.5 rounded-full bg-slate-100 dark:bg-slate-700 text-slate-500 dark:text-slate-400">No tools</span>';
                } else {
                    agentTools.innerHTML = tools.map(tool => {
                        const style = TOOL_STYLES[tool] || { label: tool, classes: 'bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-400' };
                        return `<span class="text-xs px-2 py-0.5 rounded-full ${style.classes}">${style.label}</span>`;
                    }).join('');
                }
            }
        }
    } catch (error) {
        console.error('Error loading agent info:', error);
    }
}

// Setup model selector event listener
document.addEventListener('DOMContentLoaded', () => {
    const modelSelector = document.getElementById('modelSelector');
    if (modelSelector) {
        modelSelector.addEventListener('change', (e) => {
            handleModelChange(e.target.value);
        });
    }
});

// Copy conversation to clipboard
function copyConversationToClipboard() {
    const chatMessages = document.getElementById('chatMessages');
    if (!chatMessages) return;
    
    const messages = chatMessages.querySelectorAll('div.flex');
    if (messages.length === 0) {
        showCopyFeedback('No messages to copy', false);
        return;
    }
    
    let conversationText = `Conversation with ${agentName}\n`;
    conversationText += '='.repeat(40) + '\n\n';
    
    messages.forEach(msgDiv => {
        // Check if it's a user message (justify-end) or agent message (justify-start)
        const isUserMessage = msgDiv.classList.contains('justify-end');
        const messageContent = msgDiv.querySelector('p.whitespace-pre-wrap');
        
        if (messageContent) {
            const text = messageContent.textContent.trim();
            if (isUserMessage) {
                conversationText += `User: ${text}\n\n`;
            } else {
                conversationText += `${agentName}: ${text}\n\n`;
            }
        }
    });
    
    navigator.clipboard.writeText(conversationText.trim()).then(() => {
        showCopyFeedback('Copied!', true);
    }).catch(err => {
        console.error('Failed to copy:', err);
        showCopyFeedback('Failed to copy', false);
    });
}

function showCopyFeedback(text, success) {
    const copyBtnText = document.getElementById('copyBtnText');
    const copyBtn = document.getElementById('copyConversationBtn');
    
    if (copyBtnText && copyBtn) {
        const originalText = copyBtnText.textContent;
        copyBtnText.textContent = text;
        
        if (success) {
            copyBtn.classList.add('text-green-600', 'dark:text-green-400');
        } else {
            copyBtn.classList.add('text-red-600', 'dark:text-red-400');
        }
        
        setTimeout(() => {
            copyBtnText.textContent = originalText;
            copyBtn.classList.remove('text-green-600', 'dark:text-green-400', 'text-red-600', 'dark:text-red-400');
        }, 2000);
    }
}

// Setup copy button event listener
document.addEventListener('DOMContentLoaded', () => {
    const copyBtn = document.getElementById('copyConversationBtn');
    if (copyBtn) {
        copyBtn.addEventListener('click', copyConversationToClipboard);
    }
});

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
            chatMessages.innerHTML = '<div class="flex justify-start"><div class="max-w-[70%] bg-red-50 text-red-700 rounded-2xl rounded-bl-sm px-4 py-3 shadow-sm"><p class="text-sm">Error: Agent name not found. Please go back to the dashboard and try again.</p></div></div>';
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

