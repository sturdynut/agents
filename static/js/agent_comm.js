// Agent communication JavaScript

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
    
    [senderSelect, receiverSelect].forEach(select => {
        select.innerHTML = '<option value="">Select agent...</option>';
        agents.forEach(agent => {
            const option = document.createElement('option');
            option.value = agent.name;
            option.textContent = agent.name;
            select.appendChild(option);
        });
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
            messageDiv.className = 'message-item';
            messageDiv.innerHTML = `
                <div class="message-header">
                    <strong>${interaction.agent_name}</strong>
                    ${interaction.related_agent ? `→ <strong>${interaction.related_agent}</strong>` : ''}
                    <span class="timestamp">${new Date(interaction.timestamp).toLocaleString()}</span>
                </div>
                <div class="message-content">${interaction.content}</div>
            `;
            messageHistory.appendChild(messageDiv);
        });
    } catch (error) {
        console.error('Error loading message history:', error);
    }
}

const agentMessageForm = document.getElementById('agentMessageForm');

if (agentMessageForm) {
    agentMessageForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const formData = new FormData(agentMessageForm);
        const sender = formData.get('sender');
        const receiver = formData.get('receiver');
        const message = formData.get('message');
        
        if (!sender || !receiver || !message) {
            alert('Please fill in all fields');
            return;
        }
        
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
                alert('Message sent successfully!');
                agentMessageForm.reset();
                loadMessageHistory();
            } else {
                alert('Error: ' + data.error);
            }
        } catch (error) {
            alert('Error sending message: ' + error.message);
        }
    });
}

// Initialize
populateAgentSelects();
loadMessageHistory();
setInterval(loadMessageHistory, 5000); // Refresh every 5 seconds
setInterval(populateAgentSelects, 10000); // Refresh agent list every 10 seconds

