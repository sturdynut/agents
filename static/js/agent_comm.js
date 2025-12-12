// Agent communication JavaScript - Session-based with real-time conversation view

let currentSessionId = null;
let conversationInProgress = false;
let socket = null;
let currentSessionData = null;

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

  // Listen for session started event
  socket.on("session_started", (data) => {
    console.log("Session started event received:", data);

    // Update current session ID if provided
    if (data.session_id && !currentSessionId) {
      currentSessionId = data.session_id;
      console.log("Session ID set from event:", currentSessionId);
    }

    if (conversationInProgress) {
      console.log("Showing session started notification");
      showNotification("Session started - conversation beginning...", "info");
    }
  });

  // Listen for all events for debugging
  socket.onAny((eventName, ...args) => {
    console.log("WebSocket event received:", eventName, args);
  });

  // Listen for agent thinking
  socket.on("agent_thinking", (data) => {
    console.log("Received agent_thinking event:", data);

    // Process if we have a matching session or if view is visible
    const activeView = document.getElementById("activeConversationView");
    const isViewVisible =
      activeView && !activeView.classList.contains("hidden");
    const isMatchingSession =
      !currentSessionId ||
      !data.session_id ||
      data.session_id === currentSessionId;

    if ((conversationInProgress || isViewVisible) && isMatchingSession) {
      console.log("Processing agent_thinking event for agent:", data.agent);
      updateActiveAgent(data.agent, true);
      showAgentThinking(true);
      if (data.responding_to) {
        showRespondingTo(data.responding_to);
      }
    } else {
      console.log(
        "Ignoring agent_thinking - not matching session or not in progress"
      );
    }
  });

  // Listen for orchestration messages
  socket.on("orchestration_message", (data) => {
    console.log("Received orchestration_message event:", data);

    // Process if we have a matching session or if view is visible
    const activeView = document.getElementById("activeConversationView");
    const isViewVisible =
      activeView && !activeView.classList.contains("hidden");
    const isMatchingSession =
      !currentSessionId ||
      !data.session_id ||
      data.session_id === currentSessionId;

    if ((conversationInProgress || isViewVisible) && isMatchingSession) {
      console.log("Processing orchestration_message from:", data.sender);

      // Agent has responded
      showAgentThinking(false);
      console.log(
        "Adding message to history:",
        data.sender,
        data.message.substring(0, 50) + "..."
      );
      addMessageToHistory(
        data.sender,
        data.message,
        data.timestamp,
        data.responding_to,
        data.responding_to_message
      );

      // Show next agent if available
      if (data.next_agent) {
        updateNextAgent(data.next_agent);
      } else {
        updateNextAgent(null);
      }
    } else {
      console.log(
        "Ignoring orchestration_message - not matching session or not in progress"
      );
    }
  });

  // Listen for orchestration completion
  socket.on("orchestration_complete", (data) => {
    console.log("Received orchestration_complete event:", data);

    // Always process completion events if we have a matching session or view is visible
    const activeView = document.getElementById("activeConversationView");
    const isViewVisible =
      activeView && !activeView.classList.contains("hidden");

    if (conversationInProgress || isViewVisible) {
      showAgentThinking(false);
      updateNextAgent(null);
      showNotification(
        `Session completed! ${data.messages_count} messages exchanged over ${data.total_turns} turns.`,
        "success"
      );
      conversationInProgress = false;
      console.log("Conversation marked as complete");
      loadSessions(); // Refresh session list
    }
  });

  // Listen for orchestration errors
  socket.on("orchestration_error", (data) => {
    console.error("Received orchestration_error event:", data);

    const activeView = document.getElementById("activeConversationView");
    const isViewVisible =
      activeView && !activeView.classList.contains("hidden");

    if (conversationInProgress || isViewVisible) {
      showAgentThinking(false);
      updateNextAgent(null);
      showNotification("Error: " + data.error, "error");
      conversationInProgress = false;
      console.log("Conversation marked as failed");
    }
  });
}

// Update connection status indicator
function updateConnectionStatus(connected) {
  const dot = document.getElementById("connectionDot");
  const text = document.getElementById("connectionText");

  if (dot && text) {
    if (connected) {
      dot.className = "w-2 h-2 bg-green-500 rounded-full pulse-dot";
      text.textContent = "Connected";
      text.className = "text-green-700";
    } else {
      dot.className = "w-2 h-2 bg-red-500 rounded-full";
      text.textContent = "Disconnected";
      text.className = "text-red-700";
    }
  }
}

// Escape HTML to prevent XSS
function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

// Load agents
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

// Populate agent checkboxes
async function populateAgentList() {
  const agents = await loadAgents();
  const agentsCheckboxList = document.getElementById("agentsCheckboxList");

  if (agentsCheckboxList) {
    if (agents.length === 0) {
      agentsCheckboxList.innerHTML =
        '<p class="text-sm text-red-600">No agents available. Create agents first.</p>';
    } else {
      agentsCheckboxList.innerHTML = "";
      agents.forEach((agent) => {
        const checkboxDiv = document.createElement("div");
        checkboxDiv.className = "flex items-center space-x-2";
        checkboxDiv.innerHTML = `
                    <input type="checkbox" 
                           id="agent_${agent.name}" 
                           name="selectedAgents" 
                           value="${escapeHtml(agent.name)}" 
                           class="w-4 h-4 text-indigo-600 border-slate-300 dark:border-slate-500 rounded focus:ring-indigo-500 bg-white dark:bg-slate-600"
                           checked>
                    <label for="agent_${
                      agent.name
                    }" class="text-sm text-slate-700 dark:text-slate-200 cursor-pointer flex-1">
                        <span class="font-medium">${escapeHtml(
                          agent.name
                        )}</span>
                        ${
                          agent.model
                            ? `<span class="text-slate-500 dark:text-slate-400 text-xs">(${escapeHtml(
                                agent.model
                              )})</span>`
                            : ""
                        }
                    </label>
                `;
        agentsCheckboxList.appendChild(checkboxDiv);
      });
    }
  }
}

function getSelectedAgents() {
  const checkboxes = document.querySelectorAll(
    'input[name="selectedAgents"]:checked'
  );
  return Array.from(checkboxes).map((cb) => cb.value);
}

// Load previous sessions
async function loadSessions() {
  try {
    const response = await fetch("/api/sessions?status=active");
    const data = await response.json();
    const sessions = data.sessions || [];

    const sessionsList = document.getElementById("sessionsList");
    if (sessionsList) {
      if (sessions.length === 0) {
        sessionsList.innerHTML =
          '<p class="text-sm text-slate-500 dark:text-slate-400">No previous sessions found.</p>';
      } else {
        sessionsList.innerHTML = "";
        sessions.forEach((session) => {
          const sessionDiv = document.createElement("div");
          sessionDiv.className =
            "p-3 bg-slate-50 dark:bg-slate-700/50 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg border border-slate-200 dark:border-slate-600 cursor-pointer transition-colors";
          sessionDiv.innerHTML = `
                        <div class="flex items-center justify-between">
                            <div class="flex-1">
                                <div class="font-medium text-slate-900 dark:text-white">${escapeHtml(
                                  session.objective.substring(0, 60)
                                )}${
            session.objective.length > 60 ? "..." : ""
          }</div>
                                <div class="text-xs text-slate-500 dark:text-slate-400 mt-1">
                                    ${session.agent_names.join(", ")} • ${
            session.total_turns
          } turns • ${new Date(session.updated_at).toLocaleString()}
                                </div>
                            </div>
                            <button class="ml-3 px-3 py-1 bg-indigo-600 hover:bg-indigo-700 text-white text-sm rounded transition-colors resume-session-btn" data-session-id="${
                              session.session_id
                            }">
                                Resume
                            </button>
                        </div>
                    `;
          sessionsList.appendChild(sessionDiv);
        });

        // Add click handlers
        document.querySelectorAll(".resume-session-btn").forEach((btn) => {
          btn.addEventListener("click", (e) => {
            e.stopPropagation();
            const sessionId = btn.getAttribute("data-session-id");
            resumeSession(sessionId);
          });
        });
      }
    }
  } catch (error) {
    console.error("Error loading sessions:", error);
  }
}

// Show session selection view
function showSessionSelection() {
  document.getElementById("sessionSelectionView").classList.remove("hidden");
  document.getElementById("newSessionForm").classList.add("hidden");
  document.getElementById("resumeSessionForm").classList.add("hidden");
  document.getElementById("activeConversationView").classList.add("hidden");
  currentSessionId = null;
  conversationInProgress = false;
  loadSessions();
}

// Show new session form
function showNewSessionForm() {
  document.getElementById("sessionSelectionView").classList.add("hidden");
  document.getElementById("newSessionForm").classList.remove("hidden");
  document.getElementById("resumeSessionForm").classList.add("hidden");
  populateAgentList();
}

// Resume a session
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

    // Show resume form
    document.getElementById("sessionSelectionView").classList.add("hidden");
    document.getElementById("newSessionForm").classList.add("hidden");
    document.getElementById("resumeSessionForm").classList.remove("hidden");

    // Populate session info
    const resumeSessionInfo = document.getElementById("resumeSessionInfo");
    resumeSessionInfo.innerHTML = `
            <div class="space-y-2">
                <div><strong>Objective:</strong> ${escapeHtml(
                  session.objective
                )}</div>
                <div><strong>Agents:</strong> ${escapeHtml(
                  session.agent_names.join(", ")
                )}</div>
                <div><strong>Total Turns:</strong> ${session.total_turns}</div>
                <div><strong>Last Updated:</strong> ${new Date(
                  session.updated_at
                ).toLocaleString()}</div>
            </div>
        `;

    // Load conversation history
    loadConversationHistory(session.conversation_history);

    // Set active agent from session
    if (session.current_agent) {
      updateActiveAgent(session.current_agent, false);
    } else if (session.agent_names.length > 0) {
      updateActiveAgent(session.agent_names[0], false);
    }
  } catch (error) {
    console.error("Error loading session:", error);
    showNotification("Error loading session", "error");
  }
}

// Start new session
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

    // Hide forms, show active conversation
    document.getElementById("newSessionForm").classList.add("hidden");
    document
      .getElementById("activeConversationView")
      .classList.remove("hidden");

    // Clear conversation history
    document.getElementById("conversationHistory").innerHTML = "";

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
      const errorData = await response
        .json()
        .catch(() => ({ error: "Unknown error" }));
      showNotification(
        "Error: " + (errorData.error || "Unknown error"),
        "error"
      );
      conversationInProgress = false;
      showSessionSelection();
      return;
    }

    const data = await response.json();

    if (data.success) {
      currentSessionId = data.conversation_id;
      console.log("Session started with ID:", currentSessionId);
      showNotification(
        "Session started successfully - conversation beginning...",
        "success"
      );

      // Set initial active agent (first selected agent) - will be updated via WebSocket
      if (selectedAgents.length > 0) {
        console.log("Setting initial active agent:", selectedAgents[0]);
        updateActiveAgent(selectedAgents[0], true);
      }

      // Conversation will be updated via WebSocket events
      console.log("Waiting for WebSocket events...");
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

// Resume session with additional turns
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

    // Hide resume form, show active conversation
    document.getElementById("resumeSessionForm").classList.add("hidden");
    document
      .getElementById("activeConversationView")
      .classList.remove("hidden");

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
      const errorData = await response
        .json()
        .catch(() => ({ error: "Unknown error" }));
      showNotification(
        "Error: " + (errorData.error || "Unknown error"),
        "error"
      );
      conversationInProgress = false;
      return;
    }

    const data = await response.json();

    if (data.success) {
      showNotification(
        "Session resumed successfully - conversation continuing...",
        "success"
      );

      // Set active agent from session data - will be updated via WebSocket
      if (currentSessionData.current_agent) {
        updateActiveAgent(currentSessionData.current_agent, true);
      } else if (currentSessionData.agent_names.length > 0) {
        updateActiveAgent(currentSessionData.agent_names[0], true);
      }

      // Conversation will be updated via WebSocket events
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

// Update active agent display
function updateActiveAgent(agentName, isThinking = false) {
  document.getElementById("activeAgentName").textContent = agentName;
  showAgentThinking(isThinking);
}

// Show/hide agent thinking indicator
function showAgentThinking(show) {
  const indicator = document.getElementById("agentThinkingIndicator");
  if (show) {
    indicator.classList.remove("hidden");
  } else {
    indicator.classList.add("hidden");
  }
}

// Update next agent display
function updateNextAgent(agentName) {
  const nextAgentStatus = document.getElementById("nextAgentStatus");
  const nextAgentName = document.getElementById("nextAgentName");
  if (agentName) {
    nextAgentName.textContent = agentName;
    nextAgentStatus.classList.remove("hidden");
  } else {
    nextAgentStatus.classList.add("hidden");
  }
}

// Show responding to message
function showRespondingTo(agentName) {
  const respondingTo = document.getElementById("respondingToMessage");
  const respondingToAgent = document.getElementById("respondingToAgent");
  if (agentName) {
    respondingToAgent.textContent = agentName;
    respondingTo.classList.remove("hidden");
  } else {
    respondingTo.classList.add("hidden");
  }
}

// Add message to conversation history
function addMessageToHistory(
  agentName,
  message,
  timestamp,
  respondingTo = null,
  respondingToMessage = null
) {
  const history = document.getElementById("conversationHistory");
  if (!history) return;

  const messageDiv = document.createElement("div");
  messageDiv.className =
    "bg-slate-50 dark:bg-slate-700/50 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg p-4 border-l-4 border-indigo-500 dark:border-indigo-400 transition-colors duration-200";

  const timeStr = timestamp
    ? new Date(timestamp).toLocaleString()
    : new Date().toLocaleString();

  let respondingToHtml = "";
  if (respondingTo) {
    let messagePreview = "";
    if (respondingToMessage) {
      messagePreview = `: "${escapeHtml(respondingToMessage)}${
        respondingToMessage.length >= 200 ? "..." : ""
      }"`;
    }
    respondingToHtml = `<div class="text-xs text-slate-500 dark:text-slate-400 mb-2">↳ Responding to <span class="font-medium text-indigo-600 dark:text-indigo-400">${escapeHtml(
      respondingTo
    )}</span>${messagePreview}</div>`;
  }

  messageDiv.innerHTML = `
        <div class="flex items-center justify-between mb-2">
            <div class="flex items-center gap-2">
                <strong class="text-indigo-600 dark:text-indigo-400">${escapeHtml(
                  agentName
                )}</strong>
            </div>
            <span class="text-xs text-slate-500 dark:text-slate-400">${timeStr}</span>
        </div>
        ${respondingToHtml}
        <div class="text-slate-700 dark:text-slate-300 whitespace-pre-wrap">${escapeHtml(
          message
        )}</div>
    `;

  history.appendChild(messageDiv);
  history.scrollTop = history.scrollHeight;
}

// Load conversation history
function loadConversationHistory(history) {
  const historyContainer = document.getElementById("conversationHistory");
  historyContainer.innerHTML = "";

  if (history && history.length > 0) {
    history.forEach((msg) => {
      addMessageToHistory(msg.sender, msg.message, msg.timestamp, null);
    });
  }
}

// Show notification
function showNotification(message, type = "info") {
  const existing = document.querySelector(".notification-toast");
  if (existing) {
    existing.remove();
  }

  const notification = document.createElement("div");
  const bgColors = {
    success: "bg-green-500",
    error: "bg-red-500",
    info: "bg-blue-500",
  };
  notification.className = `notification-toast fixed top-4 right-4 z-50 px-6 py-4 rounded-lg shadow-lg text-white font-medium transform translate-x-full transition-transform duration-300 ${
    bgColors[type] || bgColors.info
  }`;
  notification.textContent = message;
  document.body.appendChild(notification);

  setTimeout(() => {
    notification.classList.remove("translate-x-full");
  }, 10);

  setTimeout(() => {
    notification.classList.add("translate-x-full");
    setTimeout(() => {
      notification.remove();
    }, 300);
  }, 3000);
}

// Event listeners
document.addEventListener("DOMContentLoaded", () => {
  // Session selection buttons
  document
    .getElementById("newSessionBtn")
    .addEventListener("click", showNewSessionForm);
  document.getElementById("resumeSessionBtn").addEventListener("click", () => {
    document.getElementById("previousSessionsList").classList.remove("hidden");
    loadSessions();
  });

  // Cancel buttons
  document
    .getElementById("cancelNewSessionBtn")
    .addEventListener("click", showSessionSelection);
  document
    .getElementById("cancelResumeBtn")
    .addEventListener("click", showSessionSelection);
  document.getElementById("endSessionBtn").addEventListener("click", () => {
    conversationInProgress = false;
    showSessionSelection();
  });

  // Select all / deselect all
  document.getElementById("selectAllAgents").addEventListener("click", () => {
    document
      .querySelectorAll('input[name="selectedAgents"]')
      .forEach((cb) => (cb.checked = true));
  });
  document.getElementById("deselectAllAgents").addEventListener("click", () => {
    document
      .querySelectorAll('input[name="selectedAgents"]')
      .forEach((cb) => (cb.checked = false));
  });

  // Form submissions
  document
    .getElementById("conversationForm")
    .addEventListener("submit", (e) => {
      e.preventDefault();
      startNewSession();
    });

  document.getElementById("resumeForm").addEventListener("submit", (e) => {
    e.preventDefault();
    resumeSessionWithTurns();
  });

  // Initialize
  initWebSocket();
  populateAgentList();
  loadSessions();
});
