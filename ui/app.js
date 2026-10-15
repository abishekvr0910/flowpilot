// FlowPilot Frontend State & WebSocket Controller

let ws = null;
let currentConfig = {};
let audioWaveformInterval = null;

// DOM Elements
const hudPill = document.getElementById("hudPill");
const hudStateLabel = document.getElementById("hudStateLabel");
const hudContextTag = document.getElementById("hudContextTag");
const hudIndicator = document.getElementById("hudIndicator");
const hudMicBtn = document.getElementById("hudMicBtn");
const hudWaveformBars = document.querySelectorAll("#hudWaveform .bar");

const wsStatusChip = document.getElementById("wsStatusChip");
const wsStatusText = document.getElementById("wsStatusText");

const toneCards = document.querySelectorAll(".tone-card");
const cloudProviderSelect = document.getElementById("cloudProviderSelect");
const groqApiKeyInput = document.getElementById("groqApiKeyInput");
const openaiApiKeyInput = document.getElementById("openaiApiKeyInput");
const localModelSizeSelect = document.getElementById("localModelSizeSelect");
const languageSelect = document.getElementById("languageSelect");
const codeSwitchingToggle = document.getElementById("codeSwitchingToggle");
const engineModeTag = document.getElementById("engineModeTag");

const newVocabInput = document.getElementById("newVocabInput");
const addVocabBtn = document.getElementById("addVocabBtn");
const vocabTagsContainer = document.getElementById("vocabTagsContainer");

const historyList = document.getElementById("historyList");
const clearHistoryBtn = document.getElementById("clearHistoryBtn");
const saveSettingsBtn = document.getElementById("saveSettingsBtn");

// Initialize WebSocket
function connectWebSocket() {
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const wsUrl = `${protocol}//${window.location.host}/ws`;

  ws = new WebSocket(wsUrl);

  ws.onopen = () => {
    wsStatusChip.classList.add("connected");
    wsStatusText.textContent = "Engine Connected";
  };

  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      handleServerEvent(data);
    } catch (e) {
      console.error("Failed to parse message:", e);
    }
  };

  ws.onclose = () => {
    wsStatusChip.classList.remove("connected");
    wsStatusText.textContent = "Disconnected (Reconnecting...)";
    setTimeout(connectWebSocket, 2000);
  };
}

function handleServerEvent(data) {
  const state = data.state;

  if (state === "connected") {
    currentConfig = data.config || {};
    populateUIWithConfig(currentConfig);
    renderHistory(currentConfig.history || []);
  } else if (state === "listening") {
    setHudState("listening", "Listening...", data.target_app ? `Target: ${data.target_app}` : "Speak now");
  } else if (state === "audio_level") {
    animateWaveform(data.level || 0);
  } else if (state === "processing") {
    setHudState("processing", "Transcribing...", "Speech-to-Text");
    resetWaveform();
  } else if (state === "formatting") {
    setHudState("processing", "Formatting...", "Context Cleanup");
  } else if (state === "pasted") {
    setHudState("pasted", "Pasted!", `Injected in ${data.total_duration || 0}s`);
    if (data.history_entry) {
      prependHistoryItem(data.history_entry);
    }
  } else if (state === "idle") {
    setHudState("idle", "FlowPilot Idle", "Press F9 (Hold) or Ctrl + Shift + Space");
    resetWaveform();
  } else if (state === "error") {
    setHudState("error", "Error", data.message || "Failed");
    setTimeout(() => {
      setHudState("idle", "FlowPilot Idle", "Press F9 (Hold) or Ctrl + Shift + Space");
    }, 3000);
  }
}

function setHudState(stateClass, label, tag) {
  hudPill.className = `hud-pill ${stateClass}`;
  hudStateLabel.textContent = label;
  hudContextTag.textContent = tag;
}

function animateWaveform(level) {
  hudWaveformBars.forEach((bar, idx) => {
    const factor = Math.sin(Date.now() / 150 + idx) * 0.5 + 0.5;
    const height = Math.max(4, Math.min(22, level * 26 * factor));
    bar.style.height = `${height}px`;
  });
}

function resetWaveform() {
  hudWaveformBars.forEach((bar) => {
    bar.style.height = "6px";
  });
}

// Populate UI Controls from Server Config
function populateUIWithConfig(config) {
  // Tone Mode
  const mode = config.active_tone_mode || "developer";
  toneCards.forEach(card => {
    card.classList.toggle("active", card.dataset.mode === mode);
  });

  // Engine Mode
  const engineMode = config.engine_mode || "cloud";
  switchEngineTab(engineMode);

  // Cloud API Keys
  if (config.groq_api_key) groqApiKeyInput.value = config.groq_api_key;
  if (config.openai_api_key) openaiApiKeyInput.value = config.openai_api_key;
  if (config.cloud_provider) cloudProviderSelect.value = config.cloud_provider;

  // Local Model Size
  if (config.local_model_size) localModelSizeSelect.value = config.local_model_size;

  // Language & Code Switching
  if (config.language) languageSelect.value = config.language;
  codeSwitchingToggle.checked = config.enable_code_switching !== false;

  // Vocabulary
  renderVocabTags(config.custom_vocabulary || []);
}

// Engine Tab Switcher (Cloud vs Local)
window.switchEngineTab = function(mode) {
  currentConfig.engine_mode = mode;
  document.getElementById("tabCloud").classList.toggle("active", mode === "cloud");
  document.getElementById("tabLocal").classList.toggle("active", mode === "local");
  document.getElementById("cloudSettingsPanel").style.display = mode === "cloud" ? "block" : "none";
  document.getElementById("localSettingsPanel").style.display = mode === "local" ? "block" : "none";
  engineModeTag.textContent = mode === "cloud" ? "Cloud BYOK" : "100% Offline";
};

// Tone Mode Click Handler
toneCards.forEach(card => {
  card.addEventListener("click", () => {
    toneCards.forEach(c => c.classList.remove("active"));
    card.classList.add("active");
    currentConfig.active_tone_mode = card.dataset.mode;
    saveConfigToServer();
  });
});

// Custom Vocabulary Management
function renderVocabTags(tags) {
  vocabTagsContainer.textContent = "";
  tags.forEach(tag => {
    const chip = document.createElement("div");
    chip.className = "tag-chip";
    const tagSpan = document.createElement("span");
    tagSpan.textContent = tag;
    const removeBtn = document.createElement("span");
    removeBtn.className = "remove-btn";
    removeBtn.textContent = "×";
    removeBtn.addEventListener("click", () => removeVocabTag(tag));
    chip.appendChild(tagSpan);
    chip.appendChild(removeBtn);
    vocabTagsContainer.appendChild(chip);
  });
}

window.removeVocabTag = function(tagToRemove) {
  currentConfig.custom_vocabulary = (currentConfig.custom_vocabulary || []).filter(t => t !== tagToRemove);
  renderVocabTags(currentConfig.custom_vocabulary);
  saveConfigToServer();
};

addVocabBtn.addEventListener("click", addVocab);
newVocabInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter") addVocab();
});

function addVocab() {
  const val = newVocabInput.value.trim();
  if (val && !currentConfig.custom_vocabulary?.includes(val)) {
    currentConfig.custom_vocabulary = currentConfig.custom_vocabulary || [];
    currentConfig.custom_vocabulary.push(val);
    renderVocabTags(currentConfig.custom_vocabulary);
    newVocabInput.value = "";
    saveConfigToServer();
  }
}

function createEmptyHistoryElement() {
  const empty = document.createElement("div");
  empty.className = "history-empty";
  const icon = document.createElement("span");
  icon.textContent = "🎙️";
  const p = document.createElement("p");
  p.appendChild(document.createTextNode("No dictations recorded yet.\nPress "));
  const strong = document.createElement("strong");
  strong.textContent = "Ctrl + Shift + Space";
  p.appendChild(strong);
  p.appendChild(document.createTextNode(" anywhere to start!"));
  empty.appendChild(icon);
  empty.appendChild(p);
  return empty;
}

// History List Rendering
function renderHistory(history) {
  historyList.textContent = "";
  if (!history || history.length === 0) {
    historyList.appendChild(createEmptyHistoryElement());
    return;
  }

  history.forEach(item => prependHistoryItem(item, false));
}

function prependHistoryItem(item, isNew = true) {
  const empty = historyList.querySelector(".history-empty");
  if (empty) empty.remove();

  const el = document.createElement("div");
  el.className = "history-item";

  const header = document.createElement("div");
  header.className = "history-item-header";

  const badge = document.createElement("span");
  badge.className = "history-app-badge";
  badge.textContent = item.target_app || "system";

  const timeSpan = document.createElement("span");
  timeSpan.textContent = `${item.timestamp || ""} (${item.duration_sec || 0}s)`;

  header.appendChild(badge);
  header.appendChild(timeSpan);

  const textDiv = document.createElement("div");
  textDiv.className = "history-text";
  const contentText = item.formatted_text || item.raw_text || "";
  textDiv.textContent = contentText;

  const copyBtn = document.createElement("button");
  copyBtn.className = "history-copy-btn";
  copyBtn.textContent = "Copy";
  copyBtn.addEventListener("click", () => {
    navigator.clipboard.writeText(contentText);
    copyBtn.textContent = "Copied!";
    setTimeout(() => { copyBtn.textContent = "Copy"; }, 1500);
  });

  el.appendChild(header);
  el.appendChild(textDiv);
  el.appendChild(copyBtn);

  if (isNew) {
    historyList.prepend(el);
  } else {
    historyList.appendChild(el);
  }
}

clearHistoryBtn.addEventListener("click", async () => {
  await fetch("/api/history", { method: "DELETE" });
  historyList.textContent = "";
  historyList.appendChild(createEmptyHistoryElement());
});

// Mic Button in HUD
hudMicBtn.addEventListener("click", () => {
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ action: "toggle" }));
  }
});

// Save Settings Button
saveSettingsBtn.addEventListener("click", () => {
  currentConfig.cloud_provider = cloudProviderSelect.value;
  currentConfig.groq_api_key = groqApiKeyInput.value.trim();
  currentConfig.openai_api_key = openaiApiKeyInput.value.trim();
  currentConfig.local_model_size = localModelSizeSelect.value;
  currentConfig.language = languageSelect.value;
  currentConfig.enable_code_switching = codeSwitchingToggle.checked;
  saveConfigToServer();

  saveSettingsBtn.textContent = "Saved ✓";
  setTimeout(() => {
    saveSettingsBtn.textContent = "Save Configuration";
  }, 1500);
});

async function saveConfigToServer() {
  try {
    await fetch("/api/config", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(currentConfig)
    });
  } catch (e) {
    console.error("Failed to save config:", e);
  }
}


window.copyToClipboard = function(text) {
  navigator.clipboard.writeText(text);
};

// Start WS connection
connectWebSocket();
