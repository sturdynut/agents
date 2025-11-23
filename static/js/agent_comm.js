// Agent communication JavaScript

let conversationInProgress = false;
let conversationAborted = false;

async function loadAgents() {
    try {
        const response = await fetch('/api/agents');
        const data = await response.json();
        return data.agents || [];
    } catch (error) {
        console.error('Error loading agents:', error);
        return [];
    }
}

async function populateAgentList() {
    const agents = await loadAgents();
    const agentsList = document.getElementById('agentsList');
    
    if (agentsList) {
        if (agents.length === 0) {
            agentsList.textContent = 'No agents available. Create agents first.';
            agentsList.className = 'text-sm text-red-600';
        } else {
            const agentNames = agents.map(a => a.name).join(', ');
            agentsList.textContent = agentNames;
            agentsList.className = 'text-sm text-slate-600';
        }
    }
}

async function loadMessageHistory() {
    try {
        const response = await fetch('/api/knowledge?interaction_type=agent_chat&limit=100');
        const data = await response.json();
        const interactions = data.interactions || [];
        
        const messageHistory = document.getElementById('messageHistory');
        messageHistory.innerHTML = '';
        
        // Most recent first (API returns DESC, so newest is first)
        interactions.forEach(interaction => {
            const messageDiv = document.createElement('div');
            messageDiv.className = 'bg-slate-50 hover:bg-slate-100 rounded-lg p-4 border-l-4 border-indigo-500 transition-colors duration-200';
            messageDiv.innerHTML = `
                <div class="flex items-center justify-between mb-2">
                    <div class="flex items-center gap-2">
                        <strong class="text-indigo-600">${interaction.agent_name}</strong>
                        ${interaction.related_agent ? `<span class="text-slate-400">→</span><strong class="text-indigo-600">${interaction.related_agent}</strong>` : ''}
                    </div>
                    <span class="text-xs text-slate-500">${new Date(interaction.timestamp).toLocaleString()}</span>
                </div>
                <div class="text-slate-700 whitespace-pre-wrap">${interaction.content}</div>
            `;
            messageHistory.appendChild(messageDiv);
        });
    } catch (error) {
        console.error('Error loading message history:', error);
    }
}

// Objective-based conversation form
const conversationForm = document.getElementById('conversationForm');
const conversationStatus = document.getElementById('conversationStatus');
const startConversationBtn = document.getElementById('startConversationBtn');
const cancelConversationBtn = document.getElementById('cancelConversationBtn');

if (conversationForm) {
    conversationForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        if (conversationInProgress) {
            showNotification('A conversation is already in progress', 'error');
            return;
        }
        
        const formData = new FormData(conversationForm);
        const objective = formData.get('objective');
        const rounds = parseInt(formData.get('rounds'));
        
        if (!objective) {
            showNotification('Please enter an objective', 'error');
            return;
        }
        
        // Check if we have agents
        let agents = await loadAgents();
        if (agents.length < 2) {
            showNotification('You need at least 2 agents to start a collaboration', 'error');
            return;
        }
        
        if (rounds < 1 || rounds > 20) {
            showNotification('Rounds must be between 1 and 20', 'error');
            return;
        }
        
        // Start conversation
        conversationInProgress = true;
        conversationAborted = false;
        conversationForm.classList.add('hidden');
        conversationStatus.classList.remove('hidden');
        
        // Display objective
        document.getElementById('currentObjective').textContent = objective;
        const totalTurns = rounds * agents.length;
        updateConversationStatus(0, rounds, 'Sending request to server...', 0, totalTurns);
        
        const btnText = startConversationBtn.querySelector('.btn-text');
        const btnSpinner = startConversationBtn.querySelector('.btn-spinner');
        btnText.classList.add('hidden');
        btnSpinner.classList.remove('hidden');
        startConversationBtn.disabled = true;
        
        // Update status periodically while waiting
        let statusInterval = setInterval(() => {
            if (!conversationInProgress || conversationAborted) {
                if (statusInterval) clearInterval(statusInterval);
                return;
            }
            const currentStatus = document.getElementById('conversationStatusText');
            if (currentStatus) {
                const text = currentStatus.textContent;
                if (text.includes('Processing') || text.includes('Connecting') || text.includes('Sending')) {
                    const dots = (text.match(/\./g)?.length || 0) % 3;
                    const baseText = text.replace(/\.+$/, '');
                    currentStatus.textContent = baseText + '.'.repeat(dots + 1);
                }
            }
        }, 1000);
        
        try {
            // Create an AbortController for timeout
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 300000); // 5 minute timeout
            
            agents = await loadAgents();
            const totalTurns = rounds * agents.length;
            updateConversationStatus(0, rounds, 'Processing...', 0, totalTurns);
            
            const response = await fetch('/api/agents/collaborate', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    objective: objective,
                    rounds: rounds
                }),
                signal: controller.signal
            });
            
            clearTimeout(timeoutId);
            if (statusInterval) clearInterval(statusInterval);
            
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({ error: 'Unknown error' }));
                throw new Error(errorData.error || `HTTP ${response.status}`);
            }
            
            const data = await response.json();
            
            if (conversationAborted) {
                showNotification('Conversation cancelled', 'info');
                return;
            }
            
            if (response.ok && data.success) {
                // Update progress to 100%
                agents = await loadAgents();
                const totalTurns = rounds * agents.length;
                updateConversationStatus(rounds, rounds, 'Completed!', totalTurns, totalTurns);
                
                // Animate progress bar
                setTimeout(() => {
                    const progressFill = document.getElementById('progressFill');
                    if (progressFill) {
                        progressFill.style.width = '100%';
                    }
                }, 100);
                
                showNotification(`Conversation completed! ${data.conversation.length} messages exchanged.`, 'success');
                
                // Display conversation in history
                setTimeout(() => {
                    loadMessageHistory();
                }, 500);
            } else {
                agents = await loadAgents();
                const totalTurns = rounds * agents.length;
                updateConversationStatus(0, rounds, 'Error occurred', 0, totalTurns);
                showNotification('Error: ' + (data.error || 'Unknown error'), 'error');
            }
        } catch (error) {
            if (statusInterval) {
                clearInterval(statusInterval);
                statusInterval = null;
            }
            if (!conversationAborted) {
                agents = await loadAgents();
                const totalTurns = rounds * agents.length;
                updateConversationStatus(0, rounds, 'Error occurred', 0, totalTurns);
                let errorMessage = 'Error starting conversation: ';
                if (error.name === 'AbortError') {
                    errorMessage += 'Request timed out. The conversation may be taking too long.';
                } else {
                    errorMessage += error.message;
                }
                showNotification(errorMessage, 'error');
                console.error('Conversation error:', error);
            }
        } finally {
            setTimeout(() => {
                conversationInProgress = false;
                conversationForm.classList.remove('hidden');
                conversationStatus.classList.add('hidden');
                btnText.classList.remove('hidden');
                btnSpinner.classList.add('hidden');
                startConversationBtn.disabled = false;
                conversationForm.reset();
            }, 2000);
        }
    });
}

if (cancelConversationBtn) {
    cancelConversationBtn.addEventListener('click', () => {
        conversationAborted = true;
        conversationInProgress = false;
        showNotification('Conversation cancellation requested', 'info');
    });
}

function updateConversationStatus(currentRound, totalRounds, statusText, currentTurn, totalTurns) {
    const currentRoundEl = document.getElementById('currentRound');
    const totalRoundsEl = document.getElementById('totalRounds');
    const statusTextEl = document.getElementById('conversationStatusText');
    const progressFill = document.getElementById('progressFill');
    
    if (currentRoundEl) currentRoundEl.textContent = currentRound;
    if (totalRoundsEl) totalRoundsEl.textContent = totalRounds;
    if (statusTextEl) {
        if (currentTurn && totalTurns) {
            statusTextEl.textContent = `${statusText} (Turn ${currentTurn}/${totalTurns})`;
        } else {
            statusTextEl.textContent = statusText;
        }
    }
    
    if (progressFill && totalTurns > 0) {
        const progress = (currentTurn / totalTurns) * 100;
        progressFill.style.width = `${progress}%`;
    } else if (progressFill && totalRounds > 0) {
        const progress = (currentRound / totalRounds) * 100;
        progressFill.style.width = `${progress}%`;
    }
}

function showNotification(message, type = 'info') {
    // Remove existing notifications
    const existing = document.querySelector('.notification-toast');
    if (existing) {
        existing.remove();
    }
    
    const notification = document.createElement('div');
    const bgColors = {
        'success': 'bg-green-500',
        'error': 'bg-red-500',
        'info': 'bg-blue-500'
    };
    notification.className = `notification-toast fixed top-4 right-4 z-50 px-6 py-4 rounded-lg shadow-lg text-white font-medium transform translate-x-full transition-transform duration-300 ${bgColors[type] || bgColors.info}`;
    notification.textContent = message;
    document.body.appendChild(notification);
    
    // Animate in
    setTimeout(() => {
        notification.classList.remove('translate-x-full');
    }, 10);
    
    // Remove after 3 seconds
    setTimeout(() => {
        notification.classList.add('translate-x-full');
        setTimeout(() => {
            notification.remove();
        }, 300);
    }, 3000);
}

// Initialize
populateAgentList();
loadMessageHistory();
setInterval(() => {
    if (!conversationInProgress) {
        loadMessageHistory();
    }
}, 5000); // Refresh every 5 seconds
setInterval(populateAgentList, 10000); // Refresh agent list every 10 seconds

