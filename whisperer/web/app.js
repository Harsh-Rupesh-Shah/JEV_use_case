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
 * Append assistant response message with JEV upstream routing and downstream guardrail telemetry
 */
function appendAssistantMessage(data) {
  const { chatStream } = getElements();
  if (!chatStream) return;

  const time = formatTime();
  const content = data.content || '';
  const tools = data.tool_invocations || [];
  const policies = data.policy_cited || [];
  const decision = data.action_decision || 'approved';
  const routing = data.routing;
  const jev = data.jev;

  // 1. Upstream JEV Model Router Badge (System One)
  let routingBadgeHtml = '';
  if (routing) {
    const isReasoning = routing.tier === 'reasoning';
    const bgClass = isReasoning
      ? 'bg-purple-50 text-purple-900 border-purple-200'
      : 'bg-emerald-50 text-emerald-900 border-emerald-200';
    const icon = isReasoning ? 'psychology' : 'bolt';
    const tierName = isReasoning ? 'Reasoning Tier' : 'Fast Tier';
    const latency = routing.latency_ms ? `${Math.round(routing.latency_ms)}ms` : '110ms';
    const model = escapeHtml(routing.model_name || (isReasoning ? 'Nemotron 3.5' : 'Gemini Flash-Lite'));
    const comp = routing.complexity_label ? ` · ${escapeHtml(routing.complexity_label)}` : '';

    routingBadgeHtml = `
      <div class="mb-3 pb-2 border-b border-slate-100 flex flex-wrap items-center justify-between gap-1 text-[11px]">
        <div class="inline-flex items-center gap-1.5 ${bgClass} border px-2.5 py-1 rounded-lg font-medium shadow-2xs">
          <span class="material-symbols-outlined text-[15px]">${icon}</span>
          <span><strong>JEV Router (${latency})</strong> ➔ ${model} (${tierName}${comp})</span>
        </div>
        <span class="text-[10px] text-slate-400 font-mono hidden sm:inline">System 1 Upstream Router</span>
      </div>
    `;
  }

  // 2. Build tool badges HTML if tools were executed
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

  // 3. Decision pill
  let decisionBadge = '';
  const isIntercepted = Boolean(data.intercepted || decision === 'intercepted');

  if (isIntercepted) {
    decisionBadge = `
      <span class="inline-flex items-center gap-1 bg-rose-100 text-rose-900 border border-rose-300 text-[10px] font-bold px-2 py-0.5 rounded-full uppercase tracking-wider">
        <span class="material-symbols-outlined text-[13px] text-rose-700">security_update_warning</span>
        Circuit Breaker Intercepted
      </span>
    `;
  } else if (decision === 'declined') {
    decisionBadge = `
      <span class="inline-flex items-center gap-1 bg-rose-50 text-rose-800 border border-rose-200 text-[10px] font-bold px-2 py-0.5 rounded-full uppercase">
        <span class="material-symbols-outlined text-[12px] text-rose-600">block</span>
        Hold Enforced
      </span>
    `;
  }

  // 3b. Circuit Breaker Header Banner if intercepted
  let circuitBreakerHeaderHtml = '';
  if (isIntercepted) {
    const incidentId = data.incident_id || 'ESC-SEC01';
    circuitBreakerHeaderHtml = `
      <div class="mb-3.5 p-3 rounded-lg bg-gradient-to-r from-rose-600 to-rose-700 text-white shadow-xs flex items-center justify-between">
        <div class="flex items-center gap-2.5">
          <span class="material-symbols-outlined text-[20px] text-white">gavel</span>
          <div>
            <span class="text-xs font-bold tracking-wide uppercase">JEV Circuit Breaker: Active Intervention</span>
            <p class="text-[11px] text-rose-100 leading-tight">Session frozen by JEV System One arbiter to prevent unauthorized distribution.</p>
          </div>
        </div>
        <span class="text-[10px] font-mono bg-black/25 px-2 py-1 rounded font-semibold text-rose-100">
          #${escapeHtml(incidentId)}
        </span>
      </div>
    `;
  }

  // 4. Downstream JEV Guardrail Telemetry (System One)
  let jevBadgeHtml = '';
  if (jev) {
    const tactic = escapeHtml(jev.tactic || 'routine_query').replace(/_/g, ' ');
    const riskLabel = escapeHtml(jev.risk_label || 'negligible');
    const fidelity = jev.fidelity === 'holding_firm' ? 'Policy Upheld' : 'Policy Drift';
    const fidColor = jev.fidelity === 'holding_firm' ? 'text-emerald-700 bg-emerald-50 border-emerald-200' : 'text-amber-700 bg-amber-50 border-amber-200';
    const riskColor = (jev.risk_label === 'high' || jev.risk_label === 'critical')
      ? 'text-rose-700 bg-rose-50 border-rose-200 font-bold'
      : 'text-slate-600 bg-slate-50 border-slate-200';

    const breakerBadge = isIntercepted
      ? `<span class="inline-flex items-center gap-1 px-2 py-0.5 rounded border border-rose-300 bg-rose-100 text-rose-800 font-bold">
           <span class="material-symbols-outlined text-[12px] text-rose-700">power_settings_new</span>
           Breaker: INTERCEPTED
         </span>`
      : `<span class="inline-flex items-center gap-1 px-2 py-0.5 rounded border border-emerald-200 bg-emerald-50 text-emerald-800 font-medium">
           <span class="material-symbols-outlined text-[12px] text-emerald-600">check_circle</span>
           Breaker: PASS
         </span>`;

    jevBadgeHtml = `
      <div class="mt-3 pt-2.5 border-t border-slate-100 flex flex-wrap items-center gap-2 text-[10px]">
        <span class="text-slate-400 font-bold uppercase tracking-wider">JEV Arbiter (${Math.round(jev.latency_ms || 180)}ms):</span>
        ${breakerBadge}
        <span class="inline-flex items-center gap-1 px-2 py-0.5 rounded border ${riskColor}">
          <span class="material-symbols-outlined text-[11px]">shield</span>
          Risk: ${riskLabel.toUpperCase()}
        </span>
        <span class="inline-flex items-center gap-1 px-2 py-0.5 rounded border ${fidColor}">
          <span class="material-symbols-outlined text-[11px]">verified_user</span>
          ${fidelity}
        </span>
        <span class="inline-flex items-center gap-1 px-2 py-0.5 rounded border border-slate-200 bg-slate-50 text-slate-600 font-mono">
          Tactic: ${tactic}
        </span>
      </div>
    `;
  }

  const cardBorderClass = isIntercepted
    ? 'border-rose-300 bg-rose-50/20 shadow-md ring-1 ring-rose-200'
    : 'border-slate-200 bg-white shadow-sm';

  const avatarBgClass = isIntercepted ? 'bg-rose-700' : 'bg-[#041459]';

  const wrapper = document.createElement('div');
  wrapper.className = 'flex items-start gap-3 max-w-4xl';
  wrapper.innerHTML = `
    <div class="w-8 h-8 rounded-lg ${avatarBgClass} text-white flex items-center justify-center flex-shrink-0 mt-0.5 shadow-sm">
      <span class="material-symbols-outlined text-[17px]">${isIntercepted ? 'gavel' : 'smart_toy'}</span>
    </div>
    <div class="flex-1 space-y-1">
      <div class="${cardBorderClass} rounded-xl p-4">
        
        ${routingBadgeHtml}
        ${circuitBreakerHeaderHtml}

        <div class="flex items-center justify-between pb-2 mb-2.5 border-b border-slate-100">
          <div class="flex items-center gap-2">
            <span class="text-xs font-bold text-[#041459] flex items-center gap-1.5">
              <span class="material-symbols-outlined text-[15px] ${isIntercepted ? 'text-rose-600' : 'text-[#305AF3]'}">verified</span>
              TIAA Retirement Assistant
            </span>
            ${decisionBadge}
          </div>
          <span class="text-xs text-slate-400">${time}</span>
        </div>
        
        <p class="text-sm ${isIntercepted ? 'text-rose-950 font-medium' : 'text-slate-800'} leading-relaxed whitespace-pre-line">${escapeHtml(content)}</p>
        
        ${toolBadgesHtml}
        ${jevBadgeHtml}
      </div>
      
      ${policies.length > 0 ? `<div class="text-[11px] ${isIntercepted ? 'text-rose-700' : 'text-emerald-700'} font-medium pl-1">Governing Policy: ${escapeHtml(policies.join(', '))}</div>` : ''}
    </div>
  `;
  chatStream.appendChild(wrapper);
  scrollToBottom();

  if (isIntercepted) {
    freezeSessionUI(data);
  }
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

  unfreezeSessionUI();

  const welcome = chatStream.querySelector('.welcome-message');
  chatStream.innerHTML = '';
  if (welcome) chatStream.appendChild(welcome);
  if (userInput) {
    userInput.value = '';
    userInput.focus();
  }
  scrollToBottom();
}

/**
 * Freeze the interactive portal when JEV Circuit Breaker trips
 */
function freezeSessionUI(data) {
  const { userInput, sendBtn } = getElements();
  if (userInput) {
    userInput.disabled = true;
    userInput.value = '';
    userInput.placeholder = "⚠️ Session locked by JEV Circuit Breaker · Click 'New Session' to restart";
    userInput.classList.add('bg-slate-100', 'cursor-not-allowed', 'text-slate-400');
  }
  if (sendBtn) {
    sendBtn.disabled = true;
    sendBtn.classList.add('opacity-50', 'cursor-not-allowed');
  }

  // Update top account status badges
  const accountStatusBadge = document.getElementById('accountStatusBadge');
  const holdsBadge = document.getElementById('holdsBadge');
  if (accountStatusBadge) {
    accountStatusBadge.className = 'inline-flex items-center gap-1.5 bg-rose-100 border border-rose-300 rounded-full px-3 py-0.5 text-rose-900 text-xs font-bold';
    accountStatusBadge.innerHTML = '<span class="w-2 h-2 rounded-full bg-rose-600 animate-pulse"></span> Session Locked · Fraud Review';
  }
  if (holdsBadge) {
    holdsBadge.className = 'inline-flex items-center gap-1 bg-rose-50 border border-rose-300 rounded-full px-3 py-0.5 text-rose-900 text-xs font-semibold';
    holdsBadge.innerHTML = '<span class="material-symbols-outlined text-[13px] text-rose-700">lock</span> Immediate Disbursement Locked';
  }

  // Show lock banner if not already present
  if (!document.getElementById('sessionLockBanner')) {
    const composer = document.querySelector('section.flex-1 > div:last-child');
    if (composer) {
      const banner = document.createElement('div');
      banner.id = 'sessionLockBanner';
      banner.className = 'mb-2 p-3 bg-rose-50 border border-rose-200 rounded-lg flex items-center justify-between text-xs text-rose-900 shadow-2xs';
      banner.innerHTML = `
        <div class="flex items-center gap-2">
          <span class="material-symbols-outlined text-[18px] text-rose-600">lock_person</span>
          <span><strong>Session Locked:</strong> JEV Circuit Breaker halted transaction loop under POL-001/POL-005.</span>
        </div>
        <button id="bannerResetBtn" type="button" class="bg-rose-600 hover:bg-rose-700 text-white font-semibold px-3 py-1.5 rounded-md text-xs transition-all shadow-xs cursor-pointer flex items-center gap-1">
          <span class="material-symbols-outlined text-[14px]">restart_alt</span>
          <span>Unlock & Restart</span>
        </button>
      `;
      composer.insertBefore(banner, composer.firstChild);
      
      const bannerBtn = document.getElementById('bannerResetBtn');
      if (bannerBtn) {
        bannerBtn.addEventListener('click', () => {
          const { resetBtn } = getElements();
          if (resetBtn) resetBtn.click();
        });
      }
    }
  }
}

/**
 * Restore normal interactive portal UI
 */
function unfreezeSessionUI() {
  const { userInput, sendBtn } = getElements();
  if (userInput) {
    userInput.disabled = false;
    userInput.value = '';
    userInput.placeholder = "Type your message to the TIAA Retirement Assistant...";
    userInput.classList.remove('bg-slate-100', 'cursor-not-allowed', 'text-slate-400');
  }
  if (sendBtn) {
    sendBtn.disabled = false;
    sendBtn.classList.remove('opacity-50', 'cursor-not-allowed');
  }

  const banner = document.getElementById('sessionLockBanner');
  if (banner) banner.remove();

  const accountStatusBadge = document.getElementById('accountStatusBadge');
  const holdsBadge = document.getElementById('holdsBadge');
  if (accountStatusBadge) {
    accountStatusBadge.className = 'inline-flex items-center gap-1 bg-emerald-50 border border-emerald-200 rounded-full px-3 py-0.5 text-emerald-800 text-xs font-medium';
    accountStatusBadge.innerHTML = '<span class="w-1.5 h-1.5 rounded-full bg-emerald-600"></span> Account Active';
  }
  if (holdsBadge) {
    holdsBadge.className = 'inline-flex items-center gap-1 bg-amber-50 border border-amber-300 rounded-full px-3 py-0.5 text-amber-900 text-xs font-semibold';
    holdsBadge.innerHTML = '<span class="material-symbols-outlined text-[13px] text-amber-700">lock</span> 72h Security Hold Active';
  }
}

/**
 * Send user message to backend
 */
function sendMessage(text) {
  if (document.getElementById('sessionLockBanner')) {
    alert("Session is frozen by JEV Circuit Breaker. Please click 'Unlock & Restart' or 'New Session' to begin a new test.");
    return;
  }

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
