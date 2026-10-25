/**
 * TIAA Retirement Assistant - End-User Portal Controller
 * Real-time WebSocket interactive participant chat with live fiduciary defense
 */

let ws = null;
let messageQueue = [];

function formatTime() {
  const now = new Date();
  return now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text || '';
  return div.innerHTML;
}

function getElements() {
  return {
    chatStream: document.getElementById('chatStream'),
    chatForm: document.getElementById('chatForm'),
    userInput: document.getElementById('userInput'),
    sendBtn: document.getElementById('sendBtn'),
    resetBtn: document.getElementById('resetBtn'),
    connStatus: document.getElementById('connStatus'),
    quickChips: document.querySelectorAll('.quick-chip'),
  };
}

/**
 * Connect to backend WebSocket
 */
function initWebSocket() {
  const { connStatus } = getElements();
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const wsUrl = `${protocol}//${window.location.host}/ws/chat`;

  console.log('[TIAA Portal] Connecting to WebSocket:', wsUrl);
  ws = new WebSocket(wsUrl);

  ws.onopen = () => {
    console.log('[TIAA Portal] Connected to WebSocket');
    if (connStatus) {
      connStatus.textContent = 'Active';
      connStatus.className = 'text-emerald-400 font-semibold';
    }
    // Flush any queued messages
    while (messageQueue.length > 0 && ws.readyState === WebSocket.OPEN) {
      const msg = messageQueue.shift();
      console.log('[TIAA Portal] Sending queued message:', msg);
      ws.send(JSON.stringify(msg));
    }
  };

  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      console.log('[TIAA Portal] Received message:', data);
      handleMessage(data);
    } catch (e) {
      console.error('[TIAA Portal] Failed to parse message:', e);
    }
  };

  ws.onerror = (err) => {
    console.warn('[TIAA Portal] WebSocket connection error:', err);
    if (connStatus) {
      connStatus.textContent = 'Disconnected';
      connStatus.className = 'text-rose-400 font-semibold';
    }
  };

  ws.onclose = () => {
    console.log('[TIAA Portal] WebSocket closed, retrying in 2s...');
    if (connStatus) {
      connStatus.textContent = 'Reconnecting...';
      connStatus.className = 'text-amber-400 font-semibold';
    }
    setTimeout(initWebSocket, 2000);
  };
}

/**
 * Handle incoming event
 */
function handleMessage(data) {
  removeTypingIndicator();

  if (data.event === 'ASSISTANT_REPLY') {
    appendAssistantMessage(data);
    setLoadingState(false);
  } else if (data.event === 'SESSION_RESET') {
    resetChatUI();
    setLoadingState(false);
  }
}

/**
 * Append user message bubble
 */
function appendUserMessage(content) {
  const { chatStream } = getElements();
  if (!chatStream) return;

  const time = formatTime();
  const wrapper = document.createElement('div');
  wrapper.className = 'flex items-start justify-end gap-3 max-w-3xl ml-auto';
  wrapper.innerHTML = `
    <div class="flex-1 flex flex-col items-end space-y-1">
      <div class="bg-[#305AF3] text-white rounded-xl rounded-tr-none px-4 py-3 shadow-sm text-left max-w-2xl">
        <p class="text-sm leading-relaxed text-white">${escapeHtml(content)}</p>
      </div>
      <div class="flex items-center gap-1.5 text-[11px] text-slate-400 pr-1">
        <span>${time}</span>
        <span>·</span>
        <span class="text-[#305AF3] font-medium">You</span>
      </div>
    </div>
    <div class="w-8 h-8 rounded-full bg-[#041459] text-white flex items-center justify-center flex-shrink-0 mt-0.5 text-xs font-bold shadow-sm">
      EV
    </div>
  `;
  chatStream.appendChild(wrapper);
  scrollToBottom();
}

/**
 * Append assistant response message
 */
function appendAssistantMessage(data) {
  const { chatStream } = getElements();
  if (!chatStream) return;

  const time = formatTime();
  const content = data.content || '';
  const tools = data.tool_invocations || [];
  const policies = data.policy_cited || [];
  const decision = data.action_decision || 'approved';

  // Build tool badges HTML if tools were executed
  let toolBadgesHtml = '';
  if (tools.length > 0) {
    const badges = tools.map((inv) => {
      const isOverride = inv.tool_name === 'attempt_hold_override';
      const isMFA = inv.tool_name === 'update_beneficiary';
      const badgeColor = (isOverride || isMFA) ? 'bg-amber-50 text-amber-900 border-amber-200' : 'bg-slate-100 text-slate-700 border-slate-200';
      const icon = isOverride ? 'lock' : (isMFA ? 'security' : 'manage_search');
      return `
        <span class="inline-flex items-center gap-1 ${badgeColor} border px-2 py-0.5 rounded text-[11px] font-mono">
          <span class="material-symbols-outlined text-[13px]">${icon}</span>
          <span>${escapeHtml(inv.tool_name)}</span>
        </span>
      `;
    }).join(' ');

    toolBadgesHtml = `
      <div class="mt-3 pt-2.5 border-t border-slate-100 flex flex-wrap items-center gap-1.5">
        <span class="text-[10px] uppercase font-bold text-slate-400">Action:</span>
        ${badges}
      </div>
    `;
  }

  // Decision pill
  let decisionBadge = '';
  if (decision === 'declined') {
    decisionBadge = `
      <span class="inline-flex items-center gap-1 bg-rose-50 text-rose-800 border border-rose-200 text-[10px] font-bold px-2 py-0.5 rounded-full uppercase">
        <span class="material-symbols-outlined text-[12px] text-rose-600">block</span>
        Hold Enforced
      </span>
    `;
  }

  const wrapper = document.createElement('div');
  wrapper.className = 'flex items-start gap-3 max-w-4xl';
  wrapper.innerHTML = `
    <div class="w-8 h-8 rounded-lg bg-[#041459] text-white flex items-center justify-center flex-shrink-0 mt-0.5 shadow-sm">
      <span class="material-symbols-outlined text-[17px]">smart_toy</span>
    </div>
    <div class="flex-1 space-y-1">
      <div class="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
        <div class="flex items-center justify-between pb-2 mb-2.5 border-b border-slate-100">
          <div class="flex items-center gap-2">
            <span class="text-xs font-bold text-[#041459] flex items-center gap-1.5">
              <span class="material-symbols-outlined text-[15px] text-[#305AF3]">verified</span>
              TIAA Retirement Assistant
            </span>
            ${decisionBadge}
          </div>
          <span class="text-xs text-slate-400">${time}</span>
        </div>
        
        <p class="text-sm text-slate-800 leading-relaxed whitespace-pre-line">${escapeHtml(content)}</p>
        
        ${toolBadgesHtml}
      </div>
      
      ${policies.length > 0 ? `<div class="text-[11px] text-emerald-700 font-medium pl-1">Policy: ${escapeHtml(policies.join(', '))}</div>` : ''}
    </div>
  `;
  chatStream.appendChild(wrapper);
  scrollToBottom();
}

/**
 * Show temporary typing indicator
 */
function showTypingIndicator() {
  removeTypingIndicator();
  const { chatStream } = getElements();
  if (!chatStream) return;

  const wrapper = document.createElement('div');
  wrapper.id = 'typingIndicator';
  wrapper.className = 'flex items-start gap-3 max-w-md';
  wrapper.innerHTML = `
    <div class="w-8 h-8 rounded-lg bg-[#041459] text-white flex items-center justify-center flex-shrink-0 mt-0.5 shadow-sm">
      <span class="material-symbols-outlined text-[17px]">smart_toy</span>
    </div>
    <div class="bg-white border border-slate-200 rounded-xl px-4 py-3 shadow-sm flex items-center gap-2 text-xs text-slate-500">
      <span class="w-2 h-2 rounded-full bg-[#305AF3] animate-bounce"></span>
      <span class="w-2 h-2 rounded-full bg-[#305AF3] animate-bounce [animation-delay:0.2s]"></span>
      <span class="w-2 h-2 rounded-full bg-[#305AF3] animate-bounce [animation-delay:0.4s]"></span>
      <span class="ml-1 font-medium">Assistant is evaluating plan rules...</span>
    </div>
  `;
  chatStream.appendChild(wrapper);
  scrollToBottom();
}

function removeTypingIndicator() {
  const indicator = document.getElementById('typingIndicator');
  if (indicator) indicator.remove();
}

function setLoadingState(isLoading) {
  const { userInput, sendBtn } = getElements();
  if (userInput) userInput.disabled = isLoading;
  if (sendBtn) {
    sendBtn.disabled = isLoading;
    if (isLoading) {
      sendBtn.classList.add('opacity-50', 'cursor-not-allowed');
    } else {
      sendBtn.classList.remove('opacity-50', 'cursor-not-allowed');
      userInput.focus();
    }
  }
}

function scrollToBottom() {
  const { chatStream } = getElements();
  if (chatStream) {
    chatStream.scrollTop = chatStream.scrollHeight;
  }
}

function resetChatUI() {
  const { chatStream, userInput } = getElements();
  if (!chatStream) return;

  const welcome = chatStream.querySelector('.welcome-message');
  chatStream.innerHTML = '';
  if (welcome) chatStream.appendChild(welcome);
  if (userInput) userInput.value = '';
  scrollToBottom();
}

/**
 * Send user message to backend
 */
function sendMessage(text) {
  const cleanText = (text || '').trim();
  if (!cleanText) return;

  console.log('[TIAA Portal] Submitting user message:', cleanText);
  appendUserMessage(cleanText);
  
  const { userInput } = getElements();
  if (userInput) userInput.value = '';
  
  setLoadingState(true);
  showTypingIndicator();

  const payload = {
    action: 'user_message',
    content: cleanText,
    account_id: 'act_tiaa_403b_9918',
  };

  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify(payload));
  } else {
    console.log('[TIAA Portal] WebSocket not ready, queueing and reconnecting...');
    messageQueue.push(payload);
    initWebSocket();
  }
}

/**
 * Setup event listeners
 */
function setupListeners() {
  const { chatForm, userInput, sendBtn, resetBtn, quickChips } = getElements();

  if (chatForm) {
    chatForm.addEventListener('submit', (e) => {
      e.preventDefault();
      const text = userInput ? userInput.value : '';
      sendMessage(text);
    });
  }

  if (sendBtn) {
    sendBtn.addEventListener('click', (e) => {
      e.preventDefault();
      const text = userInput ? userInput.value : '';
      sendMessage(text);
    });
  }

  if (userInput) {
    userInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage(userInput.value);
      }
    });
  }

  quickChips.forEach((chip) => {
    chip.addEventListener('click', () => {
      const prompt = chip.getAttribute('data-prompt');
      if (prompt) {
        sendMessage(prompt);
      }
    });
  });

  if (resetBtn) {
    resetBtn.addEventListener('click', () => {
      if (confirm('Start a fresh conversation?')) {
        if (ws && ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ action: 'reset' }));
        } else {
          resetChatUI();
        }
      }
    });
  }
}

/**
 * Fetch mock participant account data from backend REST API and bind to UI
 */
async function loadAccountData() {
  try {
    const res = await fetch('/api/accounts');
    if (!res.ok) return;
    const accounts = await res.json();
    const account = accounts['act_tiaa_403b_9918'];
    if (!account) return;

    const participantNameEl = document.getElementById('participantName');
    const participantPlanEl = document.getElementById('participantPlan');
    const participantInitialsEl = document.getElementById('participantInitials');
    const totalBalanceEl = document.getElementById('totalBalance');
    const vestedBalanceEl = document.getElementById('vestedBalance');
    const planBadgeEl = document.getElementById('planBadge');
    const holdsBadgeEl = document.getElementById('holdsBadge');

    if (participantNameEl && account.participant_name) {
      participantNameEl.textContent = account.participant_name;
    }
    if (participantPlanEl && account.plan_type) {
      participantPlanEl.textContent = account.plan_type;
    }
    if (participantInitialsEl && account.participant_name) {
      const parts = account.participant_name.split(' ');
      participantInitialsEl.textContent = parts.map((p) => p[0]).join('').substring(0, 2).toUpperCase();
    }
    if (totalBalanceEl && typeof account.total_balance === 'number') {
      totalBalanceEl.textContent = `$${account.total_balance.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
    }
    if (vestedBalanceEl && typeof account.vested_balance === 'number') {
      vestedBalanceEl.textContent = `$${account.vested_balance.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
    }
    if (planBadgeEl && account.account_id) {
      planBadgeEl.textContent = `Account #${account.account_id}`;
    }
    if (holdsBadgeEl) {
      if (account.active_holds && account.active_holds.length > 0) {
        holdsBadgeEl.style.display = 'inline-flex';
        holdsBadgeEl.innerHTML = `<span class="material-symbols-outlined text-[13px] text-amber-700">lock</span> ${account.active_holds.join(', ')}`;
      } else {
        holdsBadgeEl.style.display = 'none';
      }
    }
  } catch (err) {
    console.warn('[TIAA Portal] Could not load accounts from /api/accounts:', err);
  }
}

// Initialize on DOM load
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    setupListeners();
    initWebSocket();
    loadAccountData();
  });
} else {
  setupListeners();
  initWebSocket();
  loadAccountData();
}
