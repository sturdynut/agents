// Knowledge base viewer JavaScript

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

async function populateAgentFilter() {
    const agents = await loadAgents();
    const filterAgent = document.getElementById('filterAgent');
    
    filterAgent.innerHTML = '<option value="">All Agents</option>';
    agents.forEach(agent => {
        const option = document.createElement('option');
        option.value = agent.name;
        option.textContent = agent.name;
        filterAgent.appendChild(option);
    });
}

async function loadKnowledge() {
    const filterAgent = document.getElementById('filterAgent').value;
    const filterType = document.getElementById('filterType').value;
    const searchTerm = document.getElementById('searchTerm').value;
    
    let endpoint = '/api/knowledge?';
    const params = [];
    
    if (filterAgent) params.push(`agent_name=${encodeURIComponent(filterAgent)}`);
    if (filterType) params.push(`interaction_type=${encodeURIComponent(filterType)}`);
    if (searchTerm) params.push(`search=${encodeURIComponent(searchTerm)}`);
    
    params.push('limit=100');
    endpoint += params.join('&');
    
    try {
        const response = await fetch(endpoint);
        const data = await response.json();
        const interactions = data.interactions || [];
        
        const knowledgeList = document.getElementById('knowledgeList');
        knowledgeList.innerHTML = '';
        
        interactions.reverse().forEach(interaction => {
            const itemDiv = document.createElement('div');
            itemDiv.className = 'knowledge-item';
            
            const typeIcon = {
                'user_chat': '💬',
                'agent_chat': '📡',
                'task_execution': '✅',
                'file_operation': '📁',
                'system': '⚙️'
            }[interaction.interaction_type] || '📝';
            
            itemDiv.innerHTML = `
                <div class="knowledge-header">
                    <span class="type-icon">${typeIcon}</span>
                    <strong>${interaction.agent_name}</strong>
                    ${interaction.related_agent ? `→ <strong>${interaction.related_agent}</strong>` : ''}
                    <span class="type-badge">${interaction.interaction_type}</span>
                    <span class="timestamp">${new Date(interaction.timestamp).toLocaleString()}</span>
                </div>
                <div class="knowledge-content">${interaction.content}</div>
                ${interaction.metadata ? `<div class="knowledge-metadata"><pre>${JSON.stringify(interaction.metadata, null, 2)}</pre></div>` : ''}
            `;
            knowledgeList.appendChild(itemDiv);
        });
    } catch (error) {
        console.error('Error loading knowledge:', error);
    }
}

const applyFiltersBtn = document.getElementById('applyFiltersBtn');
const clearFiltersBtn = document.getElementById('clearFiltersBtn');

if (applyFiltersBtn) {
    applyFiltersBtn.addEventListener('click', loadKnowledge);
}

if (clearFiltersBtn) {
    clearFiltersBtn.addEventListener('click', () => {
        document.getElementById('filterAgent').value = '';
        document.getElementById('filterType').value = '';
        document.getElementById('searchTerm').value = '';
        loadKnowledge();
    });
}

// Initialize
populateAgentFilter();
loadKnowledge();
setInterval(loadKnowledge, 10000); // Refresh every 10 seconds

