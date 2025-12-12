// Main application JavaScript

const API_BASE = "/api";

// Get avatar URL for an agent (uses python-avatars on the backend)
function getAgentAvatarUrl(name) {
  return `/api/avatar/${encodeURIComponent(name)}`;
}

// Utility functions
async function apiRequest(endpoint, options = {}) {
  const response = await fetch(`${API_BASE}${endpoint}`, {
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
    ...options,
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error || "Request failed");
  }

  return response.json();
}

// Agent management
async function loadAgents() {
  try {
    const data = await apiRequest("/agents");
    return data.agents || [];
  } catch (error) {
    console.error("Error loading agents:", error);
    return [];
  }
}

async function loadStats() {
  try {
    const data = await apiRequest("/stats");
    return data;
  } catch (error) {
    console.error("Error loading stats:", error);
    return { agents_count: 0, messages_count: 0 };
  }
}

async function createAgent(agentData) {
  return await apiRequest("/agents", {
    method: "POST",
    body: JSON.stringify(agentData),
  });
}

async function deleteAgent(agentName) {
  return await apiRequest(`/agents/${agentName}`, {
    method: "DELETE",
  });
}

async function updateAgent(agentName, agentData) {
  return await apiRequest(`/agents/${agentName}`, {
    method: "PUT",
    body: JSON.stringify(agentData),
  });
}

async function getAgentDetails(agentName) {
  return await apiRequest(`/agents/${agentName}`);
}

// Dashboard functionality
if (document.getElementById("agentList")) {
  // Toggle system prompt expansion
  function toggleSystemPrompt(agentName) {
    const content = document.getElementById(`prompt-content-${agentName}`);
    const toggleBtn = document.getElementById(`prompt-toggle-${agentName}`);
    const chevron = toggleBtn.querySelector("svg");

    if (content.classList.contains("hidden")) {
      content.classList.remove("hidden");
      chevron.classList.add("rotate-180");
      toggleBtn.querySelector("span").textContent = "Hide system prompt";
    } else {
      content.classList.add("hidden");
      chevron.classList.remove("rotate-180");
      toggleBtn.querySelector("span").textContent = "Show system prompt";
    }
  }

  window.toggleSystemPrompt = toggleSystemPrompt;

  async function renderAgents() {
    const agents = await loadAgents();
    const stats = await loadStats();
    const agentList = document.getElementById("agentList");
    const agentCount = document.getElementById("agentCount");
    const messageCount = document.getElementById("messageCount");

    agentCount.textContent = stats.agents_count || agents.length;
    messageCount.textContent = stats.messages_count || 0;

    agentList.innerHTML = "";

    if (agents.length === 0) {
      agentList.innerHTML = `
                <div class="col-span-full text-center py-16">
                    <div class="w-20 h-20 mx-auto mb-4 rounded-full bg-gradient-to-br from-slate-100 to-slate-200 dark:from-slate-700 dark:to-slate-800 flex items-center justify-center">
                        <svg class="w-10 h-10 text-slate-400 dark:text-slate-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"></path>
                        </svg>
                    </div>
                    <p class="text-slate-600 dark:text-slate-300 text-lg font-medium">No agents yet</p>
                    <p class="text-slate-400 dark:text-slate-500 text-sm mt-1">Click "+ Agent" to get started</p>
                </div>
            `;
      return;
    }

    // Fetch detailed info for each agent including message count
    for (const agent of agents) {
      try {
        const detailsResponse = await getAgentDetails(agent.name);
        const agentDetails = detailsResponse.agent;

        const agentCard = document.createElement("div");
        agentCard.className =
          "group bg-white dark:bg-slate-800 rounded-2xl border border-slate-200/80 dark:border-slate-700 shadow-sm hover:shadow-xl hover:border-slate-300 dark:hover:border-slate-600 transition-all duration-300 overflow-hidden";

        const systemPromptText =
          agentDetails.system_prompt || "No system prompt set";
        const avatarUrl = getAgentAvatarUrl(agentDetails.name);

        // Generate tools display
        const allowedTools = agentDetails.allowed_tools || [];
        let toolsHtml = "";
        if (allowedTools.length === 0) {
          toolsHtml =
            '<span class="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-400">No tools</span>';
        } else if (allowedTools.length === 4) {
          toolsHtml =
            '<span class="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-400">All tools</span>';
        } else {
          toolsHtml = `<span class="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400">${allowedTools.length} tools</span>`;
        }

        // Escape agent name for use in IDs
        const safeAgentName = agentDetails.name.replace(/[^a-zA-Z0-9]/g, "_");

        agentCard.innerHTML = `
                    <!-- Card Header with Avatar -->
                    <div class="relative p-6 pb-4">
                        <div class="flex items-start gap-4">
                            <!-- Avatar -->
                            <div class="flex-shrink-0">
                                <img src="${avatarUrl}" alt="${
          agentDetails.name
        }" class="w-16 h-16 rounded-2xl shadow-lg group-hover:scale-105 transition-transform duration-300" />
                            </div>
                            
                            <!-- Agent Info -->
                            <div class="flex-1 min-w-0">
                                <h3 class="text-xl font-bold text-slate-900 dark:text-white truncate">${
                                  agentDetails.name
                                }</h3>
                                <p class="text-sm text-slate-500 dark:text-slate-400 mt-0.5">${
                                  agentDetails.model
                                }</p>
                                
                                <!-- Stats Row -->
                                <div class="flex flex-wrap gap-2 mt-3">
                                    <span class="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400">
                                        <svg class="w-3 h-3 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"></path>
                                        </svg>
                                        ${agentDetails.message_count || 0}
                                    </span>
                                    <span class="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium bg-purple-50 dark:bg-purple-900/30 text-purple-700 dark:text-purple-400">
                                        <svg class="w-3 h-3 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"></path>
                                        </svg>
                                        ${
                                          agentDetails.settings?.temperature ||
                                          0.7
                                        }
                                    </span>
                                    ${toolsHtml}
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    <!-- Collapsible System Prompt -->
                    <div class="px-6 pb-2">
                        <button 
                            id="prompt-toggle-${safeAgentName}"
                            onclick="toggleSystemPrompt('${safeAgentName}')"
                            class="flex items-center gap-2 text-sm text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-300 transition-colors w-full"
                        >
                            <svg class="w-4 h-4 transition-transform duration-200" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"></path>
                            </svg>
                            <span>Show system prompt</span>
                        </button>
                        <div id="prompt-content-${safeAgentName}" class="hidden mt-3">
                            <div class="text-sm text-slate-600 dark:text-slate-300 bg-slate-50 dark:bg-slate-700/50 rounded-xl p-4 border border-slate-100 dark:border-slate-600 max-h-48 overflow-y-auto whitespace-pre-wrap leading-relaxed">${systemPromptText}</div>
                        </div>
                    </div>
                    
                    <!-- Card Footer / Actions -->
                    <div class="px-6 py-4 bg-slate-50/50 dark:bg-slate-900/30 border-t border-slate-100 dark:border-slate-700 mt-2">
                        <div class="flex items-center gap-2">
                            <a href="/chat/${
                              agentDetails.name
                            }" class="flex-1 inline-flex items-center justify-center px-4 py-2.5 bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-700 hover:to-purple-700 text-white text-sm font-medium rounded-xl transition-all duration-200 shadow-sm hover:shadow-md">
                                <svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"></path>
                                </svg>
                                Chat
                            </a>
                            <button onclick="editAgentHandler('${
                              agentDetails.name
                            }')" class="p-2.5 bg-white dark:bg-slate-700 hover:bg-slate-100 dark:hover:bg-slate-600 text-slate-600 dark:text-slate-300 hover:text-slate-800 dark:hover:text-white rounded-xl transition-colors duration-200 border border-slate-200 dark:border-slate-600" title="Edit agent">
                                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"></path>
                                </svg>
                            </button>
                            <button onclick="deleteAgentHandler('${
                              agentDetails.name
                            }')" class="p-2.5 bg-white dark:bg-slate-700 hover:bg-red-50 dark:hover:bg-red-900/30 text-slate-600 dark:text-slate-300 hover:text-red-600 dark:hover:text-red-400 rounded-xl transition-colors duration-200 border border-slate-200 dark:border-slate-600" title="Delete agent">
                                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path>
                                </svg>
                            </button>
                        </div>
                    </div>
                `;
        agentList.appendChild(agentCard);
      } catch (error) {
        console.error(`Error loading details for agent ${agent.name}:`, error);
      }
    }
  }

  // Create agent modal
  const createAgentBtn = document.getElementById("createAgentBtn");
  const createAgentModal = document.getElementById("createAgentModal");
  const createAgentForm = document.getElementById("createAgentForm");
  const closeModal = document.querySelector(".close");

  if (createAgentBtn) {
    createAgentBtn.addEventListener("click", () => {
      createAgentModal.classList.remove("hidden");
    });
  }

  if (closeModal) {
    closeModal.addEventListener("click", () => {
      createAgentModal.classList.add("hidden");
    });
  }

  // Close modal when clicking outside
  if (createAgentModal) {
    createAgentModal.addEventListener("click", (e) => {
      if (e.target === createAgentModal) {
        createAgentModal.classList.add("hidden");
      }
    });
  }

  if (createAgentForm) {
    createAgentForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const formData = new FormData(createAgentForm);

      // Get selected tools
      const selectedTools = [];
      const toolCheckboxes = createAgentForm.querySelectorAll(
        'input[name="tools"]:checked'
      );
      toolCheckboxes.forEach((checkbox) => {
        selectedTools.push(checkbox.value);
      });

      const agentData = {
        name: formData.get("name"),
        model: formData.get("model") || "llama3.2",
        system_prompt: formData.get("system_prompt") || "",
        settings: {
          temperature: parseFloat(formData.get("temperature") || 0.7),
          max_tokens: parseInt(formData.get("max_tokens") || 2048),
        },
      };

      // Only add tools if some are selected (otherwise defaults to all tools)
      if (selectedTools.length > 0 && selectedTools.length < 3) {
        agentData.tools = selectedTools;
      }

      try {
        await createAgent(agentData);
        createAgentModal.classList.add("hidden");
        createAgentForm.reset();
        // Re-check all tool boxes by default
        createAgentForm
          .querySelectorAll('input[name="tools"]')
          .forEach((cb) => (cb.checked = true));
        renderAgents();
      } catch (error) {
        alert("Error creating agent: " + error.message);
      }
    });
  }

  // Edit agent modal
  const editAgentModal = document.getElementById("editAgentModal");
  const editAgentForm = document.getElementById("editAgentForm");
  const closeEditModal = document.querySelector(".close-edit");

  if (closeEditModal) {
    closeEditModal.addEventListener("click", () => {
      editAgentModal.classList.add("hidden");
    });
  }

  // Close edit modal when clicking outside
  if (editAgentModal) {
    editAgentModal.addEventListener("click", (e) => {
      if (e.target === editAgentModal) {
        editAgentModal.classList.add("hidden");
      }
    });
  }

  if (editAgentForm) {
    editAgentForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const formData = new FormData(editAgentForm);
      const originalName = formData.get("original_name");

      // Get selected tools
      const selectedTools = [];
      const toolCheckboxes = editAgentForm.querySelectorAll(
        'input[name="tools"]:checked'
      );
      toolCheckboxes.forEach((checkbox) => {
        selectedTools.push(checkbox.value);
      });

      const agentData = {
        name: formData.get("name"),
        model: formData.get("model"),
        system_prompt: formData.get("system_prompt") || "",
        settings: {
          temperature: parseFloat(formData.get("temperature") || 0.7),
          max_tokens: parseInt(formData.get("max_tokens") || 2048),
        },
        tools: selectedTools,
        avatar_seed: formData.get("avatar_seed") || formData.get("name"),
      };

      try {
        await updateAgent(originalName, agentData);
        editAgentModal.classList.add("hidden");
        editAgentForm.reset();
        renderAgents();
      } catch (error) {
        alert("Error updating agent: " + error.message);
      }
    });
    
    // Update avatar preview when name changes
    const editAgentNameInput = document.getElementById("editAgentName");
    const editAvatarPreview = document.getElementById("editAvatarPreview");
    const editAvatarSeedInput = document.getElementById("editAvatarSeed");
    
    if (editAgentNameInput && editAvatarPreview) {
      editAgentNameInput.addEventListener("input", (e) => {
        const newName = e.target.value.trim();
        if (newName) {
          // Update avatar seed to match the new name
          if (editAvatarSeedInput) {
            editAvatarSeedInput.value = newName;
          }
          // Update avatar preview
          editAvatarPreview.src = `/api/avatar/${encodeURIComponent(newName)}`;
        }
      });
    }
    
    // Regenerate avatar button
    const regenerateAvatarBtn = document.getElementById("regenerateAvatarBtn");
    if (regenerateAvatarBtn && editAvatarPreview && editAvatarSeedInput) {
      regenerateAvatarBtn.addEventListener("click", () => {
        // Generate a random seed by appending a random number to the name
        const baseName = document.getElementById("editAgentName").value || "agent";
        const randomSeed = baseName + "_" + Math.random().toString(36).substring(2, 8);
        editAvatarSeedInput.value = randomSeed;
        // Update preview with the new seed
        editAvatarPreview.src = `/api/avatar/${encodeURIComponent(randomSeed)}?t=${Date.now()}`;
      });
    }
  }

  async function editAgentHandler(agentName) {
    try {
      console.log("[Edit Agent] Fetching details for agent:", agentName);
      const response = await getAgentDetails(agentName);
      console.log("[Edit Agent] Response:", response);
      const agent = response.agent;
      
      if (!agent) {
        throw new Error("Agent data not found in response");
      }
      
      console.log("[Edit Agent] Agent data:", agent);

      // Get form elements
      const originalNameInput = document.getElementById("editAgentOriginalName");
      const nameInput = document.getElementById("editAgentName");
      const modelInput = document.getElementById("editAgentModel");
      const systemPromptInput = document.getElementById("editSystemPrompt");
      const temperatureInput = document.getElementById("editTemperature");
      const maxTokensInput = document.getElementById("editMaxTokens");
      
      // Verify all elements exist
      if (!originalNameInput || !nameInput || !modelInput || !systemPromptInput || !temperatureInput || !maxTokensInput) {
        console.error("[Edit Agent] Missing form elements");
        throw new Error("Form elements not found");
      }

      // Populate the form
      originalNameInput.value = agent.name || "";
      nameInput.value = agent.name || "";
      modelInput.value = agent.model || "";
      systemPromptInput.value = agent.system_prompt || "";
      temperatureInput.value = agent.settings?.temperature ?? 0.7;
      maxTokensInput.value = agent.settings?.max_tokens ?? 2048;
      
      console.log("[Edit Agent] Form populated:", {
        name: nameInput.value,
        model: modelInput.value,
        systemPrompt: systemPromptInput.value.substring(0, 50),
        temperature: temperatureInput.value,
        maxTokens: maxTokensInput.value
      });

      // Populate tool checkboxes
      const allowedTools = agent.allowed_tools || [
        "write_file",
        "read_file",
        "list_directory",
        "web_search",
      ];
      
      const writeFileCheckbox = document.getElementById("edit_tool_write_file");
      const readFileCheckbox = document.getElementById("edit_tool_read_file");
      const listDirCheckbox = document.getElementById("edit_tool_list_directory");
      const webSearchCheckbox = document.getElementById("edit_tool_web_search");
      
      if (writeFileCheckbox) writeFileCheckbox.checked = allowedTools.includes("write_file");
      if (readFileCheckbox) readFileCheckbox.checked = allowedTools.includes("read_file");
      if (listDirCheckbox) listDirCheckbox.checked = allowedTools.includes("list_directory");
      if (webSearchCheckbox) webSearchCheckbox.checked = allowedTools.includes("web_search");
      
      console.log("[Edit Agent] Tools populated:", allowedTools);

      // Update avatar preview
      const avatarPreview = document.getElementById("editAvatarPreview");
      if (avatarPreview) {
        avatarPreview.src = getAgentAvatarUrl(agent.name);
      }
      
      // Store current avatar seed if available
      const avatarSeedInput = document.getElementById("editAvatarSeed");
      if (avatarSeedInput) {
        avatarSeedInput.value = agent.avatar_seed || agent.name;
      }

      // Show the modal
      editAgentModal.classList.remove("hidden");
      console.log("[Edit Agent] Modal shown");
    } catch (error) {
      console.error("[Edit Agent] Error:", error);
      alert("Error loading agent details: " + error.message);
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
      alert("Error deleting agent: " + error.message);
    }
  }

  window.editAgentHandler = editAgentHandler;
  window.deleteAgentHandler = deleteAgentHandler;

  // Load agents on page load
  renderAgents();
}
