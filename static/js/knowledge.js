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
    if (!filterAgent) return;
    
    // Preserve the currently selected value
    const currentValue = filterAgent.value;
    filterAgent.innerHTML = '<option value="">All Agents</option>';
    agents.forEach(agent => {
        const option = document.createElement('option');
        option.value = agent.name;
        option.textContent = agent.name;
        filterAgent.appendChild(option);
    });
    // Restore the selected value if it still exists
    if (currentValue && agents.some(agent => agent.name === currentValue)) {
        filterAgent.value = currentValue;
    }
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
                <div class="bg-slate-50 hover:bg-slate-100 rounded-lg p-5 border-l-4 border-indigo-500 transition-colors duration-200">
                    <div class="flex items-center justify-between mb-3 flex-wrap gap-2">
                        <div class="flex items-center gap-2 flex-wrap">
                            <span class="text-xl">${typeIcon}</span>
                            <strong class="text-indigo-600">${interaction.agent_name}</strong>
                            ${interaction.related_agent ? `<span class="text-slate-400">→</span><strong class="text-indigo-600">${interaction.related_agent}</strong>` : ''}
                            <span class="px-2 py-1 bg-indigo-100 text-indigo-700 text-xs font-medium rounded-full">${interaction.interaction_type}</span>
                        </div>
                        <span class="text-xs text-slate-500">${new Date(interaction.timestamp).toLocaleString()}</span>
                    </div>
                    <div class="text-slate-700 whitespace-pre-wrap mb-3">${interaction.content}</div>
                    ${interaction.metadata ? `<div class="mt-3 p-3 bg-slate-100 rounded-lg"><pre class="text-xs text-slate-600 overflow-x-auto">${JSON.stringify(interaction.metadata, null, 2)}</pre></div>` : ''}
                </div>
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

