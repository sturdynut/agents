// Agent communication JavaScript - Session-based with real-time DAG visualization

let currentSessionId = null;
let conversationInProgress = false;
let socket = null;
let currentSessionData = null;

// DAG visualization state
let dagState = {
  agents: [],
  agentNodes: {},
  edges: [],
  activeAgent: null,
  messageCount: 0,
  turnCount: 0,
  completedAgents: new Set()
};

// Color palette for agent nodes - vibrant, distinct colors
const agentColors = [
  { bg: '#6366f1', glow: 'rgba(99, 102, 241, 0.5)' },   // Indigo
  { bg: '#8b5cf6', glow: 'rgba(139, 92, 246, 0.5)' },   // Purple
  { bg: '#06b6d4', glow: 'rgba(6, 182, 212, 0.5)' },    // Cyan
  { bg: '#10b981', glow: 'rgba(16, 185, 129, 0.5)' },   // Emerald
  { bg: '#f59e0b', glow: 'rgba(245, 158, 11, 0.5)' },   // Amber
  { bg: '#ef4444', glow: 'rgba(239, 68, 68, 0.5)' },    // Red
  { bg: '#ec4899', glow: 'rgba(236, 72, 153, 0.5)' },   // Pink
  { bg: '#14b8a6', glow: 'rgba(20, 184, 166, 0.5)' },   // Teal
];

// Initialize WebSocket connection
function initWebSocket() {
  if (typeof io === "undefined") {
    console.warn("Socket.IO not loaded, real-time updates will not work");
    return;
  }

  socket = io();

  socket.on("connect", () => {
    console.log("WebSocket connected - ID:", socket.id);
    updateConnectionStatus(true);
  });

  socket.on("disconnect", () => {
    console.log("WebSocket disconnected");
    updateConnectionStatus(false);
  });

  socket.on("connect_error", (error) => {
    console.error("WebSocket connection error:", error);
    updateConnectionStatus(false);
  });

  socket.on("session_started", (data) => {
    console.log("Session started event received:", data);
    if (data.session_id && !currentSessionId) {
      currentSessionId = data.session_id;
    }
    if (conversationInProgress) {
      showNotification("Session started - conversation beginning...", "info");
    }
  });

  socket.onAny((eventName, ...args) => {
    console.log("WebSocket event received:", eventName, args);
  });

  socket.on("agent_thinking", (data) => {
    console.log("Received agent_thinking event:", data);
    const activeView = document.getElementById("activeConversationView");
    const isViewVisible = activeView && !activeView.classList.contains("hidden");
    const isMatchingSession = !currentSessionId || !data.session_id || data.session_id === currentSessionId;

    if ((conversationInProgress || isViewVisible) && isMatchingSession) {
      setActiveAgent(data.agent);
      if (data.responding_to) {
        highlightEdge(data.responding_to, data.agent);
      }
    }
  });

  socket.on("orchestration_message", (data) => {
    console.log("Received orchestration_message event:", data);
    const activeView = document.getElementById("activeConversationView");
    const isViewVisible = activeView && !activeView.classList.contains("hidden");
    const isMatchingSession = !currentSessionId || !data.session_id || data.session_id === currentSessionId;

    if ((conversationInProgress || isViewVisible) && isMatchingSession) {
      dagState.messageCount++;
      dagState.turnCount = data.turn || dagState.turnCount + 1;
      dagState.completedAgents.add(data.sender);
      
      if (data.responding_to && data.responding_to !== data.sender) {
        addOrUpdateEdge(data.responding_to, data.sender);
      }
      
      updateNodeState(data.sender, 'completed');
      updateDagStats();
      addMessageToHistory(data.sender, data.message, data.timestamp, data.responding_to, data.responding_to_message);

      if (data.next_agent) {
        setActiveAgent(data.next_agent);
        highlightEdge(data.sender, data.next_agent);
      } else {
        setActiveAgent(null);
      }
    }
  });

  socket.on("orchestration_complete", (data) => {
    console.log("Received orchestration_complete event:", data);
    const activeView = document.getElementById("activeConversationView");
    const isViewVisible = activeView && !activeView.classList.contains("hidden");

    if (conversationInProgress || isViewVisible) {
      setActiveAgent(null);
      dagState.agents.forEach(agent => {
        if (dagState.completedAgents.has(agent)) {
          updateNodeState(agent, 'completed');
        }
      });
      showNotification(`Session completed! ${data.messages_count} messages exchanged over ${data.total_turns} turns.`, "success");
      conversationInProgress = false;
      updateConversationStatus(`Completed - ${data.messages_count} messages`);
      loadSessions();
    }
  });

  socket.on("orchestration_error", (data) => {
    console.error("Received orchestration_error event:", data);
    const activeView = document.getElementById("activeConversationView");
    const isViewVisible = activeView && !activeView.classList.contains("hidden");

    if (conversationInProgress || isViewVisible) {
      setActiveAgent(null);
      showNotification("Error: " + data.error, "error");
      conversationInProgress = false;
      updateConversationStatus("Error occurred");
    }
  });
}

function updateConnectionStatus(connected) {
  const dot = document.getElementById("connectionDot");
  const text = document.getElementById("connectionText");
  if (dot && text) {
    if (connected) {
      dot.className = "w-2 h-2 bg-green-500 rounded-full pulse-dot";
      text.textContent = "Connected";
      text.className = "text-green-700 dark:text-green-400";
    } else {
      dot.className = "w-2 h-2 bg-red-500 rounded-full";
      text.textContent = "Disconnected";
      text.className = "text-red-700 dark:text-red-400";
    }
  }
}

function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

async function loadAgents() {
  try {
    const response = await fetch("/api/agents");
    const data = await response.json();
    return data.agents || [];
  } catch (error) {
    console.error("Error loading agents:", error);
    return [];
  }
}

async function populateAgentList() {
  const agents = await loadAgents();
  const agentsCheckboxList = document.getElementById("agentsCheckboxList");

  if (agentsCheckboxList) {
    if (agents.length === 0) {
      agentsCheckboxList.innerHTML = '<p class="text-sm text-red-600">No agents available. Create agents first.</p>';
    } else {
      agentsCheckboxList.innerHTML = "";
      agents.forEach((agent, index) => {
        const checkboxDiv = document.createElement("div");
        checkboxDiv.className = "agent-item flex items-center space-x-2 p-2 rounded-lg border border-transparent hover:border-slate-300 dark:hover:border-slate-500 cursor-grab active:cursor-grabbing transition-all";
        checkboxDiv.draggable = true;
        checkboxDiv.dataset.agentName = agent.name;
        checkboxDiv.innerHTML = `
          <div class="drag-handle text-slate-400 dark:text-slate-500 mr-1">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 8h16M4 16h16"></path>
            </svg>
          </div>
          <span class="order-number text-xs text-slate-500 dark:text-slate-400 w-5 text-center font-mono">${index + 1}</span>
          <input type="checkbox" id="agent_${agent.name}" name="selectedAgents" value="${escapeHtml(agent.name)}" 
                 class="w-4 h-4 text-indigo-600 border-slate-300 dark:border-slate-500 rounded focus:ring-indigo-500 bg-white dark:bg-slate-600" checked>
          <label for="agent_${agent.name}" class="text-sm text-slate-700 dark:text-slate-200 cursor-pointer flex-1">
            <span class="font-medium">${escapeHtml(agent.name)}</span>
            ${agent.model ? `<span class="text-slate-500 dark:text-slate-400 text-xs">(${escapeHtml(agent.model)})</span>` : ""}
          </label>
        `;
        agentsCheckboxList.appendChild(checkboxDiv);
        checkboxDiv.addEventListener("dragstart", handleDragStart);
        checkboxDiv.addEventListener("dragend", handleDragEnd);
        checkboxDiv.addEventListener("dragover", handleDragOver);
        checkboxDiv.addEventListener("drop", handleDrop);
        checkboxDiv.addEventListener("dragenter", handleDragEnter);
        checkboxDiv.addEventListener("dragleave", handleDragLeave);
      });
    }
  }
}

let draggedItem = null;

function handleDragStart(e) {
  draggedItem = this;
  this.classList.add("opacity-50", "bg-slate-100", "dark:bg-slate-700");
  e.dataTransfer.effectAllowed = "move";
  e.dataTransfer.setData("text/plain", this.dataset.agentName);
}

function handleDragEnd(e) {
  this.classList.remove("opacity-50", "bg-slate-100", "dark:bg-slate-700");
  document.querySelectorAll(".agent-item").forEach(item => {
    item.classList.remove("border-indigo-500", "border-t-2", "border-b-2");
  });
  draggedItem = null;
  updateOrderNumbers();
}

function handleDragOver(e) {
  e.preventDefault();
  e.dataTransfer.dropEffect = "move";
}

function handleDragEnter(e) {
  e.preventDefault();
  if (this !== draggedItem) this.classList.add("border-indigo-500");
}

function handleDragLeave(e) {
  this.classList.remove("border-indigo-500");
}

function handleDrop(e) {
  e.preventDefault();
  if (this !== draggedItem && draggedItem) {
    const list = this.parentNode;
    const allItems = [...list.querySelectorAll(".agent-item")];
    const draggedIndex = allItems.indexOf(draggedItem);
    const targetIndex = allItems.indexOf(this);
    if (draggedIndex < targetIndex) {
      this.parentNode.insertBefore(draggedItem, this.nextSibling);
    } else {
      this.parentNode.insertBefore(draggedItem, this);
    }
    updateOrderNumbers();
  }
  this.classList.remove("border-indigo-500");
}

function updateOrderNumbers() {
  const agentsCheckboxList = document.getElementById("agentsCheckboxList");
  if (agentsCheckboxList) {
    const items = agentsCheckboxList.querySelectorAll(".agent-item");
    items.forEach((item, index) => {
      const orderNumber = item.querySelector(".order-number");
      if (orderNumber) orderNumber.textContent = index + 1;
    });
  }
}

function getSelectedAgents() {
  const agentsCheckboxList = document.getElementById("agentsCheckboxList");
  if (!agentsCheckboxList) return [];
  const orderedAgents = [];
  const items = agentsCheckboxList.querySelectorAll(".agent-item");
  items.forEach((item) => {
    const checkbox = item.querySelector('input[name="selectedAgents"]');
    if (checkbox && checkbox.checked) orderedAgents.push(checkbox.value);
  });
  return orderedAgents;
}

// ==================== DAG VISUALIZATION ====================

function initializeDag(agents) {
  dagState = {
    agents: agents,
    agentNodes: {},
    edges: [],
    activeAgent: null,
    messageCount: 0,
    turnCount: 0,
    completedAgents: new Set()
  };
  
  calculateNodePositions();
  renderDag();
}

function calculateNodePositions() {
  const container = document.getElementById("dagContainer");
  if (!container) return;
  
  const rect = container.getBoundingClientRect();
  const width = rect.width || 800;
  const height = rect.height || 350;
  const padding = 70;
  
  const agents = dagState.agents;
  const count = agents.length;
  
  if (count === 0) return;
  
  // For small numbers, use specific layouts
  if (count === 1) {
    // Single agent in center
    dagState.agentNodes[agents[0]] = {
      name: agents[0],
      x: width / 2,
      y: height / 2,
      color: agentColors[0],
      state: 'idle',
      messageCount: 0
    };
  } else if (count === 2) {
    // Two agents side by side
    const spacing = Math.min(300, width - padding * 2);
    dagState.agentNodes[agents[0]] = {
      name: agents[0],
      x: width / 2 - spacing / 2,
      y: height / 2,
      color: agentColors[0],
      state: 'idle',
      messageCount: 0
    };
    dagState.agentNodes[agents[1]] = {
      name: agents[1],
      x: width / 2 + spacing / 2,
      y: height / 2,
      color: agentColors[1],
      state: 'idle',
      messageCount: 0
    };
  } else {
    // Circular layout for 3+ agents
    const centerX = width / 2;
    const centerY = height / 2;
    const radius = Math.min(width - padding * 2, height - padding * 2) / 2.2;
    
    agents.forEach((agent, index) => {
      // Start from top (-90 degrees) and go clockwise
      const angle = ((index / count) * 2 * Math.PI) - (Math.PI / 2);
      const x = centerX + radius * Math.cos(angle);
      const y = centerY + radius * Math.sin(angle);
      
      dagState.agentNodes[agent] = {
        name: agent,
        x: x,
        y: y,
        color: agentColors[index % agentColors.length],
        state: 'idle',
        messageCount: 0
      };
    });
  }
}

function renderDag() {
  const container = document.getElementById("dagContainer");
  if (!container) return;
  
  // Create or get canvas container
  let canvas = document.getElementById("dagCanvas");
  if (!canvas) {
    canvas = document.createElement("div");
    canvas.id = "dagCanvas";
    canvas.className = "absolute inset-0";
    container.appendChild(canvas);
  }
  
  const isDark = document.documentElement.classList.contains('dark');
  
  // Build HTML for nodes and edges
  let html = '';
  
  // Render edges first (behind nodes)
  dagState.edges.forEach(edge => {
    html += renderEdgeHTML(edge, isDark);
  });
  
  // Render nodes
  Object.values(dagState.agentNodes).forEach(node => {
    html += renderNodeHTML(node, isDark);
  });
  
  canvas.innerHTML = html;
  
  // Update stats
  updateDagStats();
  
  // Update active agent display
  updateActiveAgentDisplay();
}

function renderNodeHTML(node, isDark) {
  const isActive = node.state === 'active';
  const isCompleted = node.state === 'completed';
  const size = 56;
  const halfSize = size / 2;
  
  // Truncate name smartly
  let displayName = node.name;
  if (displayName.length > 8) {
    displayName = displayName.substring(0, 7) + '…';
  }
  
  const pulseClass = isActive ? 'animate-pulse' : '';
  const glowStyle = isActive ? `box-shadow: 0 0 20px ${node.color.glow}, 0 0 40px ${node.color.glow};` : 
                   isCompleted ? `box-shadow: 0 0 10px ${node.color.glow};` : '';
  
  const ringColor = isActive ? 'ring-white/50' : isCompleted ? 'ring-white/30' : 'ring-transparent';
  const scale = isActive ? 'scale-110' : '';
  
  return `
    <div class="absolute transition-all duration-300 ${scale}" 
         style="left: ${node.x - halfSize}px; top: ${node.y - halfSize}px; width: ${size}px; height: ${size}px;">
      <!-- Outer glow ring for active -->
      ${isActive ? `
        <div class="absolute inset-[-8px] rounded-full opacity-30 animate-ping" 
             style="background: ${node.color.bg};"></div>
      ` : ''}
      
      <!-- Main node -->
      <div class="relative w-full h-full rounded-full flex items-center justify-center ring-2 ${ringColor} transition-all duration-300 ${pulseClass}"
           style="background: ${node.color.bg}; ${glowStyle}">
        <span class="text-white font-semibold text-xs text-center px-1 truncate" style="max-width: ${size - 8}px;">
          ${escapeHtml(displayName)}
        </span>
      </div>
      
      <!-- Message count badge -->
      ${node.messageCount > 0 ? `
        <div class="absolute -top-1 -right-1 w-5 h-5 rounded-full bg-emerald-500 flex items-center justify-center ring-2 ${isDark ? 'ring-slate-800' : 'ring-white'}">
          <span class="text-white text-[10px] font-bold">${node.messageCount > 9 ? '9+' : node.messageCount}</span>
        </div>
      ` : ''}
      
      <!-- Thinking indicator -->
      ${isActive ? `
        <div class="absolute -bottom-6 left-1/2 -translate-x-1/2 flex gap-1">
          <div class="w-1.5 h-1.5 rounded-full bg-white/80 animate-bounce" style="animation-delay: 0ms;"></div>
          <div class="w-1.5 h-1.5 rounded-full bg-white/80 animate-bounce" style="animation-delay: 150ms;"></div>
          <div class="w-1.5 h-1.5 rounded-full bg-white/80 animate-bounce" style="animation-delay: 300ms;"></div>
        </div>
      ` : ''}
    </div>
  `;
}

function renderEdgeHTML(edge, isDark) {
  const fromNode = dagState.agentNodes[edge.from];
  const toNode = dagState.agentNodes[edge.to];
  if (!fromNode || !toNode) return '';
  
  const nodeRadius = 32;
  
  // Calculate direction
  const dx = toNode.x - fromNode.x;
  const dy = toNode.y - fromNode.y;
  const dist = Math.sqrt(dx * dx + dy * dy);
  if (dist === 0) return '';
  
  const normX = dx / dist;
  const normY = dy / dist;
  
  // Start and end points (at edge of nodes)
  const startX = fromNode.x + normX * nodeRadius;
  const startY = fromNode.y + normY * nodeRadius;
  const endX = toNode.x - normX * (nodeRadius + 8);
  const endY = toNode.y - normY * (nodeRadius + 8);
  
  // Calculate curve control point (perpendicular offset)
  const midX = (startX + endX) / 2;
  const midY = (startY + endY) / 2;
  const curveOffset = Math.min(30, dist * 0.15);
  const perpX = -normY * curveOffset;
  const perpY = normX * curveOffset;
  const ctrlX = midX + perpX;
  const ctrlY = midY + perpY;
  
  const isActive = edge.active;
  const strokeColor = isActive ? '#a78bfa' : (isDark ? 'rgba(148, 163, 184, 0.4)' : 'rgba(100, 116, 139, 0.4)');
  const strokeWidth = isActive ? 3 : 2;
  const dashArray = isActive ? 'none' : '6,4';
  const opacity = isActive ? 1 : 0.6;
  
  // Calculate arrow position and rotation
  const arrowSize = 8;
  const arrowX = endX;
  const arrowY = endY;
  const arrowAngle = Math.atan2(toNode.y - ctrlY, toNode.x - ctrlX) * (180 / Math.PI);
  
  return `
    <svg class="absolute inset-0 pointer-events-none overflow-visible" style="z-index: 0;">
      <!-- Edge path -->
      <path d="M ${startX} ${startY} Q ${ctrlX} ${ctrlY} ${endX} ${endY}"
            fill="none" 
            stroke="${strokeColor}" 
            stroke-width="${strokeWidth}"
            stroke-dasharray="${dashArray}"
            opacity="${opacity}"
            ${isActive ? 'class="animate-pulse"' : ''}
      />
      <!-- Arrow head -->
      <polygon 
        points="0,-${arrowSize/2} ${arrowSize},0 0,${arrowSize/2}"
        fill="${strokeColor}"
        transform="translate(${arrowX}, ${arrowY}) rotate(${arrowAngle})"
        opacity="${opacity}"
      />
    </svg>
    ${edge.messageCount > 1 ? `
      <div class="absolute px-1.5 py-0.5 rounded text-[10px] font-medium pointer-events-none"
           style="left: ${ctrlX - 8}px; top: ${ctrlY - 8}px; background: ${isDark ? '#1e293b' : '#fff'}; color: #6366f1; border: 1px solid #6366f1;">
        ${edge.messageCount}
      </div>
    ` : ''}
  `;
}

function setActiveAgent(agentName) {
  dagState.activeAgent = agentName;
  
  Object.keys(dagState.agentNodes).forEach(name => {
    const node = dagState.agentNodes[name];
    if (name === agentName) {
      node.state = 'active';
    } else if (dagState.completedAgents.has(name)) {
      node.state = 'completed';
    } else {
      node.state = 'idle';
    }
  });
  
  dagState.edges.forEach(edge => edge.active = false);
  renderDag();
}

function updateNodeState(agentName, state) {
  if (dagState.agentNodes[agentName]) {
    dagState.agentNodes[agentName].state = state;
    dagState.agentNodes[agentName].messageCount++;
    renderDag();
  }
}

function addOrUpdateEdge(from, to) {
  const existingEdge = dagState.edges.find(e => e.from === from && e.to === to);
  if (existingEdge) {
    existingEdge.messageCount++;
  } else {
    dagState.edges.push({ from, to, messageCount: 1, active: false });
  }
  renderDag();
}

function highlightEdge(from, to) {
  dagState.edges.forEach(edge => edge.active = false);
  const edge = dagState.edges.find(e => e.from === from && e.to === to);
  if (edge) {
    edge.active = true;
  } else {
    dagState.edges.push({ from, to, messageCount: 0, active: true });
  }
  renderDag();
}

function updateDagStats() {
  const turnEl = document.getElementById("dagTurnCount");
  const msgEl = document.getElementById("dagMessageCount");
  if (turnEl) turnEl.textContent = dagState.turnCount;
  if (msgEl) msgEl.textContent = dagState.messageCount;
}

function updateActiveAgentDisplay() {
  const overlay = document.getElementById("activeAgentOverlay");
  const text = document.getElementById("activeAgentText");
  if (overlay && text) {
    if (dagState.activeAgent) {
      text.textContent = `${dagState.activeAgent} is thinking...`;
      overlay.classList.remove("hidden");
    } else {
      overlay.classList.add("hidden");
    }
  }
}

function updateConversationStatus(status) {
  const statusEl = document.getElementById("conversationStatus");
  if (statusEl) statusEl.textContent = status;
}

// ==================== END DAG VISUALIZATION ====================

async function loadSessions() {
  try {
    const response = await fetch("/api/sessions?status=active");
    const data = await response.json();
    const sessions = data.sessions || [];
    
    // Load into sidebar
    const sidebarList = document.getElementById("sidebarSessionsList");
    if (sidebarList) {
      if (sessions.length === 0) {
        sidebarList.innerHTML = `
          <div class="text-center py-6">
            <div class="w-12 h-12 bg-slate-100 dark:bg-slate-700 rounded-full flex items-center justify-center mx-auto mb-3">
              <svg class="w-6 h-6 text-slate-400 dark:text-slate-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"></path>
              </svg>
            </div>
            <p class="text-sm text-slate-500 dark:text-slate-400">No sessions yet</p>
            <p class="text-xs text-slate-400 dark:text-slate-500 mt-1">Start a new session to begin</p>
          </div>
        `;
      } else {
        sidebarList.innerHTML = "";
        sessions.forEach((session) => {
          const isActive = currentSessionId === session.session_id;
          const sessionDiv = document.createElement("div");
          sessionDiv.className = `session-item p-3 rounded-lg border border-slate-200 dark:border-slate-600 cursor-pointer transition-all hover:border-indigo-300 dark:hover:border-indigo-600 ${isActive ? 'active' : 'bg-slate-50 dark:bg-slate-700/50 hover:bg-slate-100 dark:hover:bg-slate-700'}`;
          sessionDiv.dataset.sessionId = session.session_id;
          
          // Format date nicely
          const date = new Date(session.updated_at);
          const timeStr = date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
          const dateStr = date.toLocaleDateString([], { month: 'short', day: 'numeric' });
          
          sessionDiv.innerHTML = `
            <div class="flex items-start gap-2">
              <div class="flex-1 min-w-0">
                <div class="font-medium text-slate-900 dark:text-white text-sm truncate" title="${escapeHtml(session.objective)}">${escapeHtml(session.objective.substring(0, 40))}${session.objective.length > 40 ? "..." : ""}</div>
                <div class="flex items-center gap-2 mt-1.5">
                  <span class="inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium bg-indigo-100 dark:bg-indigo-900/50 text-indigo-700 dark:text-indigo-300">
                    ${session.total_turns} turns
                  </span>
                  <span class="text-xs text-slate-500 dark:text-slate-400">${dateStr} ${timeStr}</span>
                </div>
                <div class="text-xs text-slate-500 dark:text-slate-400 mt-1 truncate">
                  ${session.agent_names.slice(0, 3).join(", ")}${session.agent_names.length > 3 ? ` +${session.agent_names.length - 3}` : ""}
                </div>
              </div>
              ${isActive ? '<div class="w-2 h-2 rounded-full bg-indigo-500 animate-pulse flex-shrink-0 mt-2"></div>' : ''}
            </div>
          `;
          
          sessionDiv.addEventListener("click", () => {
            selectSession(session.session_id);
          });
          
          sidebarList.appendChild(sessionDiv);
        });
      }
    }
    
    // Also keep the old sessionsList for backward compatibility
    const sessionsList = document.getElementById("sessionsList");
    if (sessionsList) {
      if (sessions.length === 0) {
        sessionsList.innerHTML = '<p class="text-sm text-slate-500 dark:text-slate-400">No previous sessions found.</p>';
      } else {
        sessionsList.innerHTML = "";
        sessions.forEach((session) => {
          const sessionDiv = document.createElement("div");
          sessionDiv.className = "p-3 bg-slate-50 dark:bg-slate-700/50 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg border border-slate-200 dark:border-slate-600 cursor-pointer transition-colors";
          sessionDiv.innerHTML = `
            <div class="flex items-center justify-between">
              <div class="flex-1">
                <div class="font-medium text-slate-900 dark:text-white">${escapeHtml(session.objective.substring(0, 60))}${session.objective.length > 60 ? "..." : ""}</div>
                <div class="text-xs text-slate-500 dark:text-slate-400 mt-1">
                  ${session.agent_names.join(", ")} • ${session.total_turns} turns • ${new Date(session.updated_at).toLocaleString()}
                </div>
              </div>
              <button class="ml-3 px-3 py-1 bg-indigo-600 hover:bg-indigo-700 text-white text-sm rounded transition-colors resume-session-btn" data-session-id="${session.session_id}">
                Resume
              </button>
            </div>
          `;
          sessionsList.appendChild(sessionDiv);
        });
        document.querySelectorAll(".resume-session-btn").forEach((btn) => {
          btn.addEventListener("click", (e) => {
            e.stopPropagation();
            resumeSession(btn.getAttribute("data-session-id"));
          });
        });
      }
    }
  } catch (error) {
    console.error("Error loading sessions:", error);
  }
}

// Select a session from the sidebar (view its history)
async function selectSession(sessionId) {
  try {
    const response = await fetch(`/api/sessions/${sessionId}`);
    const data = await response.json();
    const session = data.session;

    if (!session) {
      showNotification("Session not found", "error");
      return;
    }

    currentSessionData = session;
    currentSessionId = sessionId;
    
    // Update sidebar to highlight selected session
    updateSidebarSelection(sessionId);

    // Hide other views and show resume form
    document.getElementById("sessionSelectionView").classList.add("hidden");
    document.getElementById("newSessionForm").classList.add("hidden");
    document.getElementById("resumeSessionForm").classList.remove("hidden");
    document.getElementById("activeConversationView").classList.add("hidden");

    document.getElementById("resumeSessionInfo").innerHTML = `
      <div class="space-y-3">
        <div>
          <div class="text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-1">Objective</div>
          <div class="text-slate-900 dark:text-white">${escapeHtml(session.objective)}</div>
        </div>
        <div class="grid grid-cols-2 gap-4">
          <div>
            <div class="text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-1">Agents</div>
            <div class="text-slate-900 dark:text-white text-sm">${escapeHtml(session.agent_names.join(", "))}</div>
          </div>
          <div>
            <div class="text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-1">Progress</div>
            <div class="text-slate-900 dark:text-white text-sm">${session.total_turns} turns completed</div>
          </div>
        </div>
        <div>
          <div class="text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-1">Last Updated</div>
          <div class="text-slate-900 dark:text-white text-sm">${new Date(session.updated_at).toLocaleString()}</div>
        </div>
      </div>
    `;

    // Pre-load conversation history for viewing
    if (session.conversation_history && session.conversation_history.length > 0) {
      // Initialize DAG for display
      setTimeout(() => {
        document.getElementById("activeConversationView").classList.remove("hidden");
        document.getElementById("resumeSessionForm").classList.add("hidden");
        initializeDag(session.agent_names);
        
        // Rebuild state from history
        session.conversation_history.forEach((msg, index) => {
          dagState.completedAgents.add(msg.sender);
          dagState.messageCount++;
          dagState.turnCount = index + 1;
          if (dagState.agentNodes[msg.sender]) {
            dagState.agentNodes[msg.sender].messageCount++;
          }
          if (index > 0) {
            const prevMsg = session.conversation_history[index - 1];
            if (prevMsg.sender !== msg.sender) {
              addOrUpdateEdge(prevMsg.sender, msg.sender);
            }
          }
        });
        
        updateDagStats();
        renderDag();
        loadConversationHistory(session.conversation_history);
        updateConversationStatus(`${session.total_turns} turns • Click "Resume" in sidebar to continue`);
      }, 50);
    }
  } catch (error) {
    console.error("Error loading session:", error);
    showNotification("Error loading session", "error");
  }
}

// Update sidebar to highlight the selected session
function updateSidebarSelection(sessionId) {
  const items = document.querySelectorAll("#sidebarSessionsList .session-item");
  items.forEach(item => {
    if (item.dataset.sessionId === sessionId) {
      item.classList.add("active");
      item.classList.remove("bg-slate-50", "dark:bg-slate-700/50", "hover:bg-slate-100", "dark:hover:bg-slate-700");
    } else {
      item.classList.remove("active");
      item.classList.add("bg-slate-50", "dark:bg-slate-700/50", "hover:bg-slate-100", "dark:hover:bg-slate-700");
    }
  });
}

function showSessionSelection() {
  document.getElementById("sessionSelectionView").classList.remove("hidden");
  document.getElementById("newSessionForm").classList.add("hidden");
  document.getElementById("resumeSessionForm").classList.add("hidden");
  document.getElementById("activeConversationView").classList.add("hidden");
  currentSessionId = null;
  currentSessionData = null;
  conversationInProgress = false;
  
  // Clear sidebar selection
  const items = document.querySelectorAll("#sidebarSessionsList .session-item");
  items.forEach(item => {
    item.classList.remove("active");
    item.classList.add("bg-slate-50", "dark:bg-slate-700/50", "hover:bg-slate-100", "dark:hover:bg-slate-700");
  });
  
  loadSessions();
}

function showNewSessionForm() {
  document.getElementById("sessionSelectionView").classList.add("hidden");
  document.getElementById("newSessionForm").classList.remove("hidden");
  document.getElementById("resumeSessionForm").classList.add("hidden");
  document.getElementById("activeConversationView").classList.add("hidden");
  
  // Clear sidebar selection when starting new session
  currentSessionId = null;
  currentSessionData = null;
  const items = document.querySelectorAll("#sidebarSessionsList .session-item");
  items.forEach(item => {
    item.classList.remove("active");
    item.classList.add("bg-slate-50", "dark:bg-slate-700/50", "hover:bg-slate-100", "dark:hover:bg-slate-700");
  });
  
  populateAgentList();
}

async function resumeSession(sessionId) {
  try {
    const response = await fetch(`/api/sessions/${sessionId}`);
    const data = await response.json();
    const session = data.session;

    if (!session) {
      showNotification("Session not found", "error");
      return;
    }

    currentSessionData = session;
    currentSessionId = sessionId;

    document.getElementById("sessionSelectionView").classList.add("hidden");
    document.getElementById("newSessionForm").classList.add("hidden");
    document.getElementById("resumeSessionForm").classList.remove("hidden");

    document.getElementById("resumeSessionInfo").innerHTML = `
      <div class="space-y-2">
        <div><strong>Objective:</strong> ${escapeHtml(session.objective)}</div>
        <div><strong>Agents:</strong> ${escapeHtml(session.agent_names.join(", "))}</div>
        <div><strong>Total Turns:</strong> ${session.total_turns}</div>
        <div><strong>Last Updated:</strong> ${new Date(session.updated_at).toLocaleString()}</div>
      </div>
    `;

    loadConversationHistory(session.conversation_history);
  } catch (error) {
    console.error("Error loading session:", error);
    showNotification("Error loading session", "error");
  }
}

async function startNewSession() {
  const form = document.getElementById("conversationForm");
  const formData = new FormData(form);
  const objective = formData.get("objective");
  const maxTurns = parseInt(formData.get("maxTurns") || "20");
  const conversationMode = formData.get("conversationMode") || "intelligent";
  const selectedAgents = getSelectedAgents();

  if (!objective) {
    showNotification("Please enter an objective", "error");
    return;
  }

  if (selectedAgents.length === 0) {
    document.getElementById("agentSelectionError").classList.remove("hidden");
    showNotification("Please select at least one agent", "error");
    return;
  }

  document.getElementById("agentSelectionError").classList.add("hidden");

  try {
    conversationInProgress = true;
    currentSessionId = null;

    document.getElementById("newSessionForm").classList.add("hidden");
    document.getElementById("activeConversationView").classList.remove("hidden");
    document.getElementById("conversationHistory").innerHTML = "";
    
    // Small delay to let container render before initializing DAG
    setTimeout(() => {
      initializeDag(selectedAgents);
      updateConversationStatus("Starting conversation...");
    }, 50);

    const response = await fetch("/api/agents/orchestrate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        objective: objective,
        max_turns: maxTurns,
        agent_names: selectedAgents,
        conversation_mode: conversationMode,
      }),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ error: "Unknown error" }));
      showNotification("Error: " + (errorData.error || "Unknown error"), "error");
      conversationInProgress = false;
      showSessionSelection();
      return;
    }

    const data = await response.json();

    if (data.success) {
      currentSessionId = data.conversation_id;
      showNotification("Session started successfully", "success");
      updateConversationStatus("In progress...");
      if (selectedAgents.length > 0) {
        setActiveAgent(selectedAgents[0]);
      }
    } else {
      showNotification("Error: " + (data.error || "Unknown error"), "error");
      conversationInProgress = false;
      showSessionSelection();
    }
  } catch (error) {
    console.error("Error starting session:", error);
    showNotification("Error starting session: " + error.message, "error");
    conversationInProgress = false;
    showSessionSelection();
  }
}

async function resumeSessionWithTurns() {
  if (!currentSessionData) {
    showNotification("No session data available", "error");
    return;
  }

  const form = document.getElementById("resumeForm");
  const formData = new FormData(form);
  const additionalTurns = parseInt(formData.get("additionalTurns") || "10");

  try {
    conversationInProgress = true;

    document.getElementById("resumeSessionForm").classList.add("hidden");
    document.getElementById("activeConversationView").classList.remove("hidden");

    setTimeout(() => {
      initializeDag(currentSessionData.agent_names);
      
      // Rebuild state from history
      currentSessionData.conversation_history.forEach((msg, index) => {
        dagState.completedAgents.add(msg.sender);
        dagState.messageCount++;
        dagState.turnCount = index + 1;
        if (dagState.agentNodes[msg.sender]) {
          dagState.agentNodes[msg.sender].messageCount++;
        }
        if (index > 0) {
          const prevMsg = currentSessionData.conversation_history[index - 1];
          if (prevMsg.sender !== msg.sender) {
            addOrUpdateEdge(prevMsg.sender, msg.sender);
          }
        }
      });
      
      updateDagStats();
      renderDag();
      updateConversationStatus("Resuming conversation...");
    }, 50);

    const response = await fetch("/api/agents/orchestrate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        objective: currentSessionData.objective,
        max_turns: additionalTurns,
        agent_names: currentSessionData.agent_names,
        resume_session_id: currentSessionId,
      }),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ error: "Unknown error" }));
      showNotification("Error: " + (errorData.error || "Unknown error"), "error");
      conversationInProgress = false;
      return;
    }

    const data = await response.json();

    if (data.success) {
      showNotification("Session resumed successfully", "success");
      updateConversationStatus("In progress...");
      if (currentSessionData.current_agent) {
        setActiveAgent(currentSessionData.current_agent);
      }
    } else {
      showNotification("Error: " + (data.error || "Unknown error"), "error");
      conversationInProgress = false;
    }
  } catch (error) {
    console.error("Error resuming session:", error);
    showNotification("Error resuming session: " + error.message, "error");
    conversationInProgress = false;
  }
}

function addMessageToHistory(agentName, message, timestamp, respondingTo = null, respondingToMessage = null) {
  const history = document.getElementById("conversationHistory");
  if (!history) return;

  const agentIndex = dagState.agents.indexOf(agentName);
  const color = agentColors[agentIndex % agentColors.length];
  
  const messageDiv = document.createElement("div");
  messageDiv.className = "bg-slate-50 dark:bg-slate-700/50 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg p-4 transition-colors duration-200";
  messageDiv.style.borderLeft = `4px solid ${color.bg}`;

  const timeStr = timestamp ? new Date(timestamp).toLocaleString() : new Date().toLocaleString();

  let respondingToHtml = "";
  if (respondingTo) {
    const respColor = agentColors[dagState.agents.indexOf(respondingTo) % agentColors.length];
    let messagePreview = respondingToMessage ? `: "${escapeHtml(respondingToMessage.substring(0, 100))}${respondingToMessage.length > 100 ? "..." : ""}"` : "";
    respondingToHtml = `<div class="text-xs text-slate-500 dark:text-slate-400 mb-2">↳ Responding to <span class="font-medium" style="color: ${respColor.bg}">${escapeHtml(respondingTo)}</span>${messagePreview}</div>`;
  }

  messageDiv.innerHTML = `
    <div class="flex items-center justify-between mb-2">
      <div class="flex items-center gap-2">
        <div class="w-3 h-3 rounded-full" style="background-color: ${color.bg}"></div>
        <strong style="color: ${color.bg}">${escapeHtml(agentName)}</strong>
        <span class="text-xs px-1.5 py-0.5 bg-slate-200 dark:bg-slate-600 rounded text-slate-600 dark:text-slate-300 font-mono">Turn ${dagState.turnCount}</span>
      </div>
      <span class="text-xs text-slate-500 dark:text-slate-400">${timeStr}</span>
    </div>
    ${respondingToHtml}
    <div class="text-slate-700 dark:text-slate-300 whitespace-pre-wrap text-sm leading-relaxed">${escapeHtml(message)}</div>
  `;

  history.appendChild(messageDiv);
  history.scrollTop = history.scrollHeight;
}

function loadConversationHistory(history) {
  const historyContainer = document.getElementById("conversationHistory");
  historyContainer.innerHTML = "";
  if (history && history.length > 0) {
    history.forEach((msg, index) => {
      dagState.turnCount = index + 1;
      addMessageToHistory(msg.sender, msg.message, msg.timestamp, null);
    });
  }
}

function showNotification(message, type = "info") {
  const existing = document.querySelector(".notification-toast");
  if (existing) existing.remove();

  const bgColors = { success: "bg-green-500", error: "bg-red-500", info: "bg-blue-500" };
  const notification = document.createElement("div");
  notification.className = `notification-toast fixed top-4 right-4 z-50 px-6 py-4 rounded-lg shadow-lg text-white font-medium transform translate-x-full transition-transform duration-300 ${bgColors[type] || bgColors.info}`;
  notification.textContent = message;
  document.body.appendChild(notification);

  setTimeout(() => notification.classList.remove("translate-x-full"), 10);
  setTimeout(() => {
    notification.classList.add("translate-x-full");
    setTimeout(() => notification.remove(), 300);
  }, 3000);
}

// Copy conversation to clipboard
function copyConversationToClipboard() {
  const history = document.getElementById("conversationHistory");
  if (!history) return;
  
  const messages = history.querySelectorAll("div.bg-slate-50, div.dark\\:bg-slate-700\\/50");
  if (messages.length === 0) {
    showCopyFeedback("No messages to copy", false);
    return;
  }
  
  let conversationText = "Multi-Agent Conversation\n";
  conversationText += "=".repeat(50) + "\n";
  
  if (currentSessionData && currentSessionData.objective) {
    conversationText += `Objective: ${currentSessionData.objective}\n`;
  }
  
  conversationText += "=".repeat(50) + "\n\n";
  
  messages.forEach(msgDiv => {
    // Extract agent name (inside the strong tag with color style)
    const agentNameEl = msgDiv.querySelector("strong");
    const agentName = agentNameEl ? agentNameEl.textContent.trim() : "Unknown";
    
    // Extract timestamp
    const timestampEl = msgDiv.querySelector("span.text-xs.text-slate-500");
    const timestamp = timestampEl ? timestampEl.textContent.trim() : "";
    
    // Extract turn number
    const turnEl = msgDiv.querySelector("span.font-mono");
    const turn = turnEl ? turnEl.textContent.trim() : "";
    
    // Extract message content
    const messageEl = msgDiv.querySelector("div.whitespace-pre-wrap");
    const message = messageEl ? messageEl.textContent.trim() : "";
    
    // Extract responding to info if present
    const respondingToEl = msgDiv.querySelector("div.text-xs.text-slate-500.mb-2");
    const respondingTo = respondingToEl ? respondingToEl.textContent.trim() : "";
    
    if (message) {
      conversationText += `[${turn}] ${agentName} (${timestamp})\n`;
      if (respondingTo) {
        conversationText += `${respondingTo}\n`;
      }
      conversationText += `${message}\n\n`;
      conversationText += "-".repeat(40) + "\n\n";
    }
  });
  
  navigator.clipboard.writeText(conversationText.trim()).then(() => {
    showCopyFeedback("Copied!", true);
  }).catch(err => {
    console.error("Failed to copy:", err);
    showCopyFeedback("Failed to copy", false);
  });
}

function showCopyFeedback(text, success) {
  const copyBtnText = document.getElementById("copyBtnText");
  const copyBtn = document.getElementById("copyConversationBtn");
  
  if (copyBtnText && copyBtn) {
    const originalText = copyBtnText.textContent;
    copyBtnText.textContent = text;
    
    if (success) {
      copyBtn.classList.add("text-green-600", "dark:text-green-400");
    } else {
      copyBtn.classList.add("text-red-600", "dark:text-red-400");
    }
    
    setTimeout(() => {
      copyBtnText.textContent = originalText;
      copyBtn.classList.remove("text-green-600", "dark:text-green-400", "text-red-600", "dark:text-red-400");
    }, 2000);
  }
}

function handleResize() {
  if (dagState.agents.length > 0) {
    calculateNodePositions();
    renderDag();
  }
}

// Event listeners
document.addEventListener("DOMContentLoaded", () => {
  // New session buttons (both main and sidebar)
  const newSessionBtn = document.getElementById("newSessionBtn");
  if (newSessionBtn) {
    newSessionBtn.addEventListener("click", showNewSessionForm);
  }
  
  const sidebarNewSessionBtn = document.getElementById("sidebarNewSessionBtn");
  if (sidebarNewSessionBtn) {
    sidebarNewSessionBtn.addEventListener("click", showNewSessionForm);
  }
  
  // Resume session button (legacy)
  const resumeSessionBtn = document.getElementById("resumeSessionBtn");
  if (resumeSessionBtn) {
    resumeSessionBtn.addEventListener("click", () => {
      const previousSessionsList = document.getElementById("previousSessionsList");
      if (previousSessionsList) {
        previousSessionsList.classList.remove("hidden");
      }
      loadSessions();
    });
  }
  
  // Refresh sessions button in sidebar
  const refreshSessionsBtn = document.getElementById("refreshSessionsBtn");
  if (refreshSessionsBtn) {
    refreshSessionsBtn.addEventListener("click", () => {
      loadSessions();
      showNotification("Sessions refreshed", "info");
    });
  }

  const cancelNewSessionBtn = document.getElementById("cancelNewSessionBtn");
  if (cancelNewSessionBtn) {
    cancelNewSessionBtn.addEventListener("click", showSessionSelection);
  }
  
  const cancelResumeBtn = document.getElementById("cancelResumeBtn");
  if (cancelResumeBtn) {
    cancelResumeBtn.addEventListener("click", showSessionSelection);
  }
  
  const endSessionBtn = document.getElementById("endSessionBtn");
  if (endSessionBtn) {
    endSessionBtn.addEventListener("click", () => {
      conversationInProgress = false;
      showSessionSelection();
    });
  }
  
  // Copy conversation button
  const copyBtn = document.getElementById("copyConversationBtn");
  if (copyBtn) {
    copyBtn.addEventListener("click", copyConversationToClipboard);
  }

  const selectAllAgents = document.getElementById("selectAllAgents");
  if (selectAllAgents) {
    selectAllAgents.addEventListener("click", () => {
      document.querySelectorAll('input[name="selectedAgents"]').forEach((cb) => (cb.checked = true));
    });
  }
  
  const deselectAllAgents = document.getElementById("deselectAllAgents");
  if (deselectAllAgents) {
    deselectAllAgents.addEventListener("click", () => {
      document.querySelectorAll('input[name="selectedAgents"]').forEach((cb) => (cb.checked = false));
    });
  }

  const conversationForm = document.getElementById("conversationForm");
  if (conversationForm) {
    conversationForm.addEventListener("submit", (e) => {
      e.preventDefault();
      startNewSession();
    });
  }

  const resumeForm = document.getElementById("resumeForm");
  if (resumeForm) {
    resumeForm.addEventListener("submit", (e) => {
      e.preventDefault();
      resumeSessionWithTurns();
    });
  }

  window.addEventListener("resize", handleResize);

  initWebSocket();
  populateAgentList();
  loadSessions();
});
