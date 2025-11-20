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

async function populateAgentSelects() {
    const agents = await loadAgents();
    const senderSelect = document.getElementById('senderAgent');
    const receiverSelect = document.getElementById('receiverAgent');
    const convAgent1 = document.getElementById('convAgent1');
    const convAgent2 = document.getElementById('convAgent2');
    
    [senderSelect, receiverSelect, convAgent1, convAgent2].forEach(select => {
        if (!select) return;
        // Preserve the currently selected value
        const currentValue = select.value;
        select.innerHTML = '<option value="">Select agent...</option>';
        agents.forEach(agent => {
            const option = document.createElement('option');
            option.value = agent.name;
            option.textContent = agent.name;
            select.appendChild(option);
        });
        // Restore the selected value if it still exists
        if (currentValue && agents.some(agent => agent.name === currentValue)) {
            select.value = currentValue;
        }
    });
}

async function loadMessageHistory() {
    try {
        const response = await fetch('/api/knowledge?interaction_type=agent_chat&limit=50');
        const data = await response.json();
        const interactions = data.interactions || [];
        
        const messageHistory = document.getElementById('messageHistory');
        messageHistory.innerHTML = '';
        
        interactions.reverse().forEach(interaction => {
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

// Single message form
const agentMessageForm = document.getElementById('agentMessageForm');

if (agentMessageForm) {
    agentMessageForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const formData = new FormData(agentMessageForm);
        const sender = formData.get('sender');
        const receiver = formData.get('receiver');
        const message = formData.get('message');
        
        if (!sender || !receiver || !message) {
            showNotification('Please fill in all fields', 'error');
            return;
        }
        
        if (sender === receiver) {
            showNotification('Sender and receiver must be different', 'error');
            return;
        }
        
        const submitBtn = agentMessageForm.querySelector('button[type="submit"]');
        const originalText = submitBtn.textContent;
        submitBtn.disabled = true;
        submitBtn.textContent = 'Sending...';
        
        try {
            const response = await fetch(`/api/agents/${sender}/message/${receiver}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ message })
            });
            
            const data = await response.json();
            if (response.ok) {
                showNotification('Message sent successfully!', 'success');
                agentMessageForm.reset();
                loadMessageHistory();
            } else {
                showNotification('Error: ' + data.error, 'error');
            }
        } catch (error) {
            showNotification('Error sending message: ' + error.message, 'error');
        } finally {
            submitBtn.disabled = false;
            submitBtn.textContent = originalText;
        }
    });
}

// Multi-round conversation form
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
        const agent1 = formData.get('agent1');
        const agent2 = formData.get('agent2');
        const initialMessage = formData.get('initial_message');
        const rounds = parseInt(formData.get('rounds'));
        
        if (!agent1 || !agent2 || !initialMessage) {
            showNotification('Please fill in all fields', 'error');
            return;
        }
        
        if (agent1 === agent2) {
            showNotification('Agent 1 and Agent 2 must be different', 'error');
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
        
        updateConversationStatus(0, rounds, 'Sending request to server...');
        
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
            
            updateConversationStatus(0, rounds, 'Processing...');
            
            const response = await fetch(`/api/agents/${agent1}/conversation/${agent2}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    initial_message: initialMessage,
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
                updateConversationStatus(rounds, rounds, 'Completed!');
                
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
                updateConversationStatus(0, rounds, 'Error occurred');
                showNotification('Error: ' + (data.error || 'Unknown error'), 'error');
            }
        } catch (error) {
            if (statusInterval) {
                clearInterval(statusInterval);
                statusInterval = null;
            }
            if (!conversationAborted) {
                updateConversationStatus(0, rounds, 'Error occurred');
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

function updateConversationStatus(currentRound, totalRounds, statusText) {
    const currentRoundEl = document.getElementById('currentRound');
    const totalRoundsEl = document.getElementById('totalRounds');
    const statusTextEl = document.getElementById('conversationStatusText');
    const progressFill = document.getElementById('progressFill');
    
    if (currentRoundEl) currentRoundEl.textContent = currentRound;
    if (totalRoundsEl) totalRoundsEl.textContent = totalRounds;
    if (statusTextEl) statusTextEl.textContent = statusText;
    
    if (progressFill && totalRounds > 0) {
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
populateAgentSelects();
loadMessageHistory();
setInterval(() => {
    if (!conversationInProgress) {
        loadMessageHistory();
    }
}, 5000); // Refresh every 5 seconds
setInterval(populateAgentSelects, 10000); // Refresh agent list every 10 seconds

