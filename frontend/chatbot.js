document.addEventListener('DOMContentLoaded', () => {
  const chatBtn = document.getElementById('aiChatBtn');
  const chatPopup = document.getElementById('aiChatPopup');
  const closeBtn = document.getElementById('closeChatBtn');
  const chatMessages = document.getElementById('chatMessages');
  const chatInput = document.getElementById('chatInput');
  const sendBtn = document.getElementById('sendChatBtn');

  // Conversation state
  let conversationId = sessionStorage.getItem('ai_conversation_id');
  if (!conversationId) {
    conversationId = crypto.randomUUID ? crypto.randomUUID() : Math.random().toString(36).substring(2);
    sessionStorage.setItem('ai_conversation_id', conversationId);
  }

  // Toggle Popup
  chatBtn.addEventListener('click', () => {
    chatPopup.classList.toggle('active');
    if (chatPopup.classList.contains('active')) {
      if (chatMessages.children.length === 0) {
        showWelcomeMessage();
      }
      chatInput.focus();
    }
  });

  closeBtn.addEventListener('click', () => {
    chatPopup.classList.remove('active');
  });

  // Input Handling
  chatInput.addEventListener('input', () => {
    chatInput.style.height = 'auto';
    chatInput.style.height = (chatInput.scrollHeight) + 'px';
    sendBtn.disabled = chatInput.value.trim().length === 0;
  });

  chatInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (!sendBtn.disabled) sendChat();
    }
  });

  sendBtn.addEventListener('click', sendChat);

  function showWelcomeMessage() {
    const msg = "Hello! I can help you analyze thermal anomalies, hotspots, persistence, risk and alerts.";
    appendMessage(msg, 'ai');
    
    // Quick Actions
    const actions = [
      "🔥 Latest Hotspots",
      "⚠️ High-Risk Events",
      "🚨 Active Alerts",
      "🏭 Industrial Events",
      "📈 Persistent Sources",
      "🛰️ Satellite Status"
    ];
    
    const actionsDiv = document.createElement('div');
    actionsDiv.className = 'chat-quick-actions';
    
    actions.forEach(action => {
      const chip = document.createElement('button');
      chip.className = 'action-chip';
      chip.textContent = action;
      chip.onclick = () => {
        chatInput.value = action.split(' ').slice(1).join(' '); // remove emoji
        sendBtn.disabled = false;
        sendChat();
      };
      actionsDiv.appendChild(chip);
    });
    
    chatMessages.appendChild(actionsDiv);
    scrollToBottom();
  }

  function appendMessage(text, sender, data = null) {
    const bubble = document.createElement('div');
    bubble.className = `message-bubble ${sender}`;
    bubble.textContent = text;
    chatMessages.appendChild(bubble);
    
    if (data && data.items && data.items.length > 0) {
      data.items.forEach(item => {
        const card = document.createElement('div');
        card.className = 'chat-result-card';
        card.innerHTML = `
          <div class="chat-result-card-header">
            ${item.icon || '🔥'} ${item.title || item.id}
          </div>
          <div class="chat-result-card-body">
            ${item.description || ''}
          </div>
          <div class="chat-result-card-actions">
            ${item.action ? `<button class="chat-action-btn" onclick="window.location.hash='${item.action}'">View Details</button>` : ''}
          </div>
        `;
        chatMessages.appendChild(card);
      });
    }

    scrollToBottom();
  }

  function showTypingIndicator() {
    const indicator = document.createElement('div');
    indicator.className = 'typing-indicator';
    indicator.id = 'typingIndicator';
    indicator.innerHTML = `Thermal AI is analyzing <span></span><span></span><span></span>`;
    chatMessages.appendChild(indicator);
    scrollToBottom();
  }

  function removeTypingIndicator() {
    const indicator = document.getElementById('typingIndicator');
    if (indicator) indicator.remove();
  }

  function scrollToBottom() {
    chatMessages.scrollTop = chatMessages.scrollHeight;
  }

  async function sendChat() {
    const text = chatInput.value.trim();
    if (!text) return;

    appendMessage(text, 'user');
    chatInput.value = '';
    chatInput.style.height = 'auto';
    sendBtn.disabled = true;

    showTypingIndicator();

    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text, conversation_id: conversationId })
      });

      removeTypingIndicator();

      if (!response.ok) {
        throw new Error('Server error');
      }

      const result = await response.json();
      appendMessage(result.message, 'ai', result.data);

    } catch (err) {
      console.error(err);
      removeTypingIndicator();
      appendMessage("⚠️\n\nI'm unable to access the AI service right now.\nPlease try again in a moment.", 'ai');
    }
  }
});
