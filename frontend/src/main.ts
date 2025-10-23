import './style.css';
import '@fortawesome/fontawesome-free/css/all.css';
import { api } from './api';
import type { Message } from './types';

const redisSessionId: string = `real-health-${Date.now()}`;

// Stats tracking
const statelessStats = {
  messageCount: 0,
  toolsUsed: 0,
  tokenCount: 0,
  totalResponseTime: 0,
  avgResponseTime: 0,
  lastResponseTime: 0,
};

const redisStats = {
  messageCount: 0,
  toolsUsed: 0,
  tokenCount: 0,
  tokenUsagePercent: 0,
  semanticMemories: 0,
  isOverThreshold: false,
  totalResponseTime: 0,
  avgResponseTime: 0,
  lastResponseTime: 0,
};

// DOM Elements
const statelessChatArea = document.getElementById(
  'stateless-chat-area'
) as HTMLDivElement;
const redisChatArea = document.getElementById('redis-chat-area') as HTMLDivElement;

const statelessChatForm = document.getElementById(
  'stateless-chat-form'
) as HTMLFormElement;
const redisChatForm = document.getElementById('redis-chat-form') as HTMLFormElement;

const statelessMessageInput = document.getElementById(
  'stateless-message-input'
) as HTMLInputElement;
const redisMessageInput = document.getElementById(
  'redis-message-input'
) as HTMLInputElement;

const statelessSendButton = document.getElementById(
  'stateless-send-button'
) as HTMLButtonElement;
const redisSendButton = document.getElementById(
  'redis-send-button'
) as HTMLButtonElement;

const redisStatus = document.getElementById('redis-status') as HTMLSpanElement;
const ollamaStatus = document.getElementById('ollama-status') as HTMLSpanElement;

// Check system health
async function checkHealth(): Promise<void> {
  try {
    const data = await api.healthCheck();

    redisStatus.className = `status-badge ${
      data.redis_connected ? 'connected' : 'disconnected'
    }`;
    redisStatus.textContent = `Redis: ${
      data.redis_connected ? 'Connected' : 'Disconnected'
    }`;

    ollamaStatus.className = `status-badge ${
      data.ollama_connected ? 'connected' : 'disconnected'
    }`;
    ollamaStatus.textContent = `Ollama: ${
      data.ollama_connected ? 'Connected' : 'Disconnected'
    }`;
  } catch (error) {
    console.error('Health check failed:', error);
  }
}

// Add message to specific chat area
function addMessage(
  chatArea: HTMLDivElement,
  role: Message['role'],
  content: string,
  metadata?: {
    tools_used?: Array<{ name: string; args: Record<string, unknown> }>;
    memory_stats?: {
      short_term_available: boolean;
      semantic_hits: number;
      long_term_available: boolean;
    };
  },
  isRawHtml: boolean = false
): void {
  const messageDiv = document.createElement('div');
  messageDiv.className = role === 'user' ? 'message-user' : 'message-assistant';

  // Determine if this is Redis chat by checking if it has memory_stats
  const isRedisChat = role === 'assistant' && metadata?.memory_stats !== undefined;

  let metadataHtml = '';

  // Add memory stats for Redis chat
  if (role === 'assistant' && metadata?.memory_stats) {
    const stats = metadata.memory_stats;
    const memoryIndicators = [];

    if (stats.short_term_available) {
      memoryIndicators.push(
        '<span class="memory-badge"><i class="fas fa-file-lines"></i> Short-term memory</span>'
      );
    }
    if (stats.semantic_hits > 0) {
      memoryIndicators.push(
        `<span class="memory-badge semantic"><i class="fas fa-brain"></i> ${stats.semantic_hits} semantic memories</span>`
      );
    }

    if (memoryIndicators.length > 0) {
      metadataHtml = `<div class="message-metadata">${memoryIndicators.join(
        ' '
      )}</div>`;
    }
  }

  // Add tools used for Redis chat
  if (role === 'assistant' && metadata?.tools_used && metadata.tools_used.length > 0) {
    const toolsList = metadata.tools_used
      .map(
        tool =>
          `<span class="tool-badge"><i class="fas fa-wrench"></i> ${tool.name}</span>`
      )
      .join(' ');
    metadataHtml += `<div class="message-metadata tools-used">${toolsList}</div>`;
  }

  // Add Redis icon prefix for Redis assistant messages
  const iconPrefix = isRedisChat
    ? '<img src="/redis-chat-icon.svg" alt="Redis" class="inline-block w-4 h-4 mr-1 align-text-bottom" />'
    : '';

  // Use raw HTML for error messages, otherwise render markdown
  const renderedContent = isRawHtml ? content : renderMarkdown(content);

  messageDiv.innerHTML = `
    <div class="message-bubble ${role}">${iconPrefix}${renderedContent}${metadataHtml}</div>
  `;

  chatArea.appendChild(messageDiv);
  chatArea.scrollTop = chatArea.scrollHeight;
}

// Escape HTML to prevent XSS
function escapeHtml(text: string): string {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

// Simple markdown renderer for chat messages
function renderMarkdown(text: string): string {
  // First escape HTML to prevent XSS
  let html = escapeHtml(text);

  // Convert markdown formatting
  // Bold text: *text* or **text**
  html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
  html = html.replace(/\*([^*]+)\*/g, '<strong>$1</strong>');

  // Convert numbered lists - put each number on its own line
  html = html.replace(/(\d+)\. /g, '<br>$1. ');

  // Convert bullet points
  html = html.replace(/• /g, '<br>• ');
  html = html.replace(/- /g, '<br>• ');

  // Convert line breaks
  html = html.replace(/\n\n/g, '<br><br>');
  html = html.replace(/\n/g, '<br>');

  // Clean up extra breaks at the beginning
  html = html.replace(/^<br>/, '');

  return html;
}

// Update stats comparison table
function updateStatsTable(): void {
  // Update stateless stats
  const statelessTokensEl = document.getElementById('stat-stateless-tokens');
  const statelessUsageEl = document.getElementById('stat-stateless-usage');
  const statelessLatencyEl = document.getElementById('stat-stateless-latency');

  if (statelessTokensEl)
    statelessTokensEl.textContent = String(statelessStats.tokenCount);
  if (statelessUsageEl) statelessUsageEl.textContent = 'N/A';
  if (statelessLatencyEl) {
    statelessLatencyEl.textContent =
      statelessStats.avgResponseTime > 0
        ? `${statelessStats.avgResponseTime.toFixed(0)}ms`
        : 'N/A';
  }

  // Update Redis stats
  const redisTokensEl = document.getElementById('stat-redis-tokens');
  const redisUsageEl = document.getElementById('stat-redis-usage');
  const redisSemanticEl = document.getElementById('stat-redis-semantic');
  const redisTrimmingEl = document.getElementById('stat-redis-trimming');
  const redisLatencyEl = document.getElementById('stat-redis-latency');

  if (redisTokensEl) redisTokensEl.textContent = String(redisStats.tokenCount);
  if (redisUsageEl)
    redisUsageEl.textContent =
      redisStats.tokenUsagePercent > 0
        ? `${redisStats.tokenUsagePercent.toFixed(1)}%`
        : 'N/A';
  if (redisSemanticEl)
    redisSemanticEl.textContent = String(redisStats.semanticMemories);
  if (redisTrimmingEl) {
    redisTrimmingEl.textContent = redisStats.isOverThreshold ? '✂️ Active' : 'Inactive';
    redisTrimmingEl.style.color = redisStats.isOverThreshold ? '#ff6b6b' : '#51cf66';
  }
  if (redisLatencyEl) {
    redisLatencyEl.textContent =
      redisStats.avgResponseTime > 0
        ? `${redisStats.avgResponseTime.toFixed(0)}ms`
        : 'N/A';
  }
}

// Show skeleton loading indicator with animated text
function showLoading(chatArea: HTMLDivElement): HTMLDivElement {
  const loadingDiv = document.createElement('div');
  loadingDiv.className = 'message-assistant';
  loadingDiv.innerHTML = `
    <div class="message-bubble assistant">
      <span class="thinking-text">Thinking</span>
    </div>
  `;
  chatArea.appendChild(loadingDiv);
  chatArea.scrollTop = chatArea.scrollHeight;

  // Animate thinking text
  const thinkingTexts = [
    'Thinking',
    'Analyzing',
    'Processing',
    'Retrieving data',
    'Computing',
  ];
  let textIndex = 0;
  const thinkingSpan = loadingDiv.querySelector('.thinking-text') as HTMLElement;

  const interval = setInterval(() => {
    textIndex = (textIndex + 1) % thinkingTexts.length;
    if (thinkingSpan) {
      thinkingSpan.textContent = thinkingTexts[textIndex] + '...';
    }
  }, 1200);

  // Store interval ID so we can clear it later
  (loadingDiv as any).__thinkingInterval = interval;

  return loadingDiv;
}

// Remove loading indicator
function removeLoading(chatArea: HTMLDivElement, loadingDiv: HTMLDivElement): void {
  // Clear thinking animation interval
  if ((loadingDiv as any).__thinkingInterval) {
    clearInterval((loadingDiv as any).__thinkingInterval);
  }

  if (chatArea.contains(loadingDiv)) {
    chatArea.removeChild(loadingDiv);
  }
}

// Send stateless message with streaming
async function sendStatelessMessage(message: string): Promise<void> {
  addMessage(statelessChatArea, 'user', message);
  statelessMessageInput.value = '';
  statelessSendButton.disabled = true;

  const loadingDiv = showLoading(statelessChatArea);
  let responseText = '';
  let messageDiv: HTMLDivElement | null = null;
  let firstTokenReceived = false;

  try {
    // Create message div for streaming
    messageDiv = document.createElement('div');
    messageDiv.className = 'message-assistant';
    messageDiv.innerHTML = '<div class="message-bubble assistant"></div>';
    const bubbleEl = messageDiv.querySelector('.message-bubble') as HTMLElement;

    for await (const chunk of api.streamStatelessMessage({ message })) {
      if (chunk.type === 'token' && chunk.content) {
        // Remove loading indicator on first token
        if (!firstTokenReceived) {
          removeLoading(statelessChatArea, loadingDiv);
          statelessChatArea.appendChild(messageDiv);
          firstTokenReceived = true;
        }
        responseText += chunk.content;
        const iconPrefix =
          '<i class="fas fa-comment-dots" style="margin-right: 0.25rem;"></i>';
        bubbleEl.innerHTML = iconPrefix + renderMarkdown(responseText);
        statelessChatArea.scrollTop = statelessChatArea.scrollHeight;
      } else if (chunk.type === 'done' && chunk.data) {
        // Update stats
        const data = chunk.data;
        statelessStats.messageCount += 2;
        statelessStats.toolsUsed += data.tool_calls_made || 0;
        statelessStats.tokenCount = 0;

        if (data.response_time_ms !== undefined) {
          statelessStats.lastResponseTime = data.response_time_ms;
          statelessStats.totalResponseTime += data.response_time_ms;
          const responseCount = statelessStats.messageCount / 2;
          statelessStats.avgResponseTime =
            statelessStats.totalResponseTime / responseCount;
        }
        updateStatsTable();
      }
    }
  } catch (error) {
    console.error('Error sending stateless message:', error);
    if (messageDiv) statelessChatArea.removeChild(messageDiv);
    removeLoading(statelessChatArea, loadingDiv);
    addMessage(
      statelessChatArea,
      'assistant',
      '<i class="fas fa-exclamation-triangle"></i> Sorry, I encountered an error. Please make sure Ollama is running.',
      undefined,
      true
    );
  } finally {
    statelessSendButton.disabled = false;
    statelessMessageInput.focus();
  }
}

// Send Redis message with streaming
async function sendRedisMessage(message: string): Promise<void> {
  addMessage(redisChatArea, 'user', message);
  redisMessageInput.value = '';
  redisSendButton.disabled = true;

  const loadingDiv = showLoading(redisChatArea);
  let responseText = '';
  let messageDiv: HTMLDivElement | null = null;
  let firstTokenReceived = false;

  try {
    // Create message div for streaming
    messageDiv = document.createElement('div');
    messageDiv.className = 'message-assistant';
    messageDiv.innerHTML =
      '<div class="message-bubble assistant"><img src="/redis-chat-icon.svg" alt="Redis" class="inline-block w-4 h-4 mr-1 align-text-bottom" /></div>';
    const bubbleEl = messageDiv.querySelector('.message-bubble') as HTMLElement;

    for await (const chunk of api.streamRedisMessage({
      message,
      session_id: redisSessionId,
    })) {
      if (chunk.type === 'token' && chunk.content) {
        // Remove loading indicator on first token
        if (!firstTokenReceived) {
          removeLoading(redisChatArea, loadingDiv);
          redisChatArea.appendChild(messageDiv);
          firstTokenReceived = true;
        }
        responseText += chunk.content;
        const iconPrefix =
          '<img src="/redis-chat-icon.svg" alt="Redis" class="inline-block w-4 h-4 mr-1 align-text-bottom" />';
        bubbleEl.innerHTML = iconPrefix + renderMarkdown(responseText);
        redisChatArea.scrollTop = redisChatArea.scrollHeight;
      } else if (chunk.type === 'done' && chunk.data) {
        // Add metadata after streaming completes
        const data = chunk.data;
        console.log('Done event received:', data);
        let metadataHtml = '';

        if (data.memory_stats) {
          const stats = data.memory_stats;
          const memoryIndicators = [];
          if (stats.short_term_available) {
            memoryIndicators.push(
              '<span class="memory-badge"><i class="fas fa-file-lines"></i> Short-term memory</span>'
            );
          }
          if (stats.semantic_hits > 0) {
            memoryIndicators.push(
              `<span class="memory-badge semantic"><i class="fas fa-brain"></i> ${stats.semantic_hits} semantic memories</span>`
            );
          }
          if (memoryIndicators.length > 0) {
            metadataHtml = `<div class="message-metadata">${memoryIndicators.join(
              ' '
            )}</div>`;
          }
        }

        if (data.tools_used && data.tools_used.length > 0) {
          const toolsList = data.tools_used
            .map(
              (tool: any) =>
                `<span class="tool-badge"><i class="fas fa-wrench"></i> ${
                  tool.name || tool
                }</span>`
            )
            .join(' ');
          metadataHtml += `<div class="message-metadata tools-used">${toolsList}</div>`;
        }

        const iconPrefix =
          '<img src="/redis-chat-icon.svg" alt="Redis" class="inline-block w-4 h-4 mr-1 align-text-bottom" />';
        bubbleEl.innerHTML = iconPrefix + renderMarkdown(responseText) + metadataHtml;

        // Update stats
        redisStats.messageCount += 2;
        redisStats.toolsUsed += data.tool_calls_made || 0;
        redisStats.semanticMemories = data.memory_stats?.semantic_hits || 0;

        if (data.token_stats) {
          console.log('Token stats received:', data.token_stats);
          redisStats.tokenCount = data.token_stats.token_count || 0;
          redisStats.tokenUsagePercent = data.token_stats.usage_percent || 0;
          redisStats.isOverThreshold = data.token_stats.is_over_threshold || false;
        }

        if (data.response_time_ms !== undefined) {
          redisStats.lastResponseTime = data.response_time_ms;
          redisStats.totalResponseTime += data.response_time_ms;
          const responseCount = redisStats.messageCount / 2;
          redisStats.avgResponseTime = redisStats.totalResponseTime / responseCount;
        }
        updateStatsTable();
      }
    }
  } catch (error) {
    console.error('Error sending Redis message:', error);
    if (messageDiv) redisChatArea.removeChild(messageDiv);
    removeLoading(redisChatArea, loadingDiv);
    addMessage(
      redisChatArea,
      'assistant',
      '<i class="fas fa-exclamation-triangle"></i> Sorry, I encountered an error. Please make sure Ollama and Redis are running.',
      undefined,
      true
    );
  } finally {
    redisSendButton.disabled = false;
    redisMessageInput.focus();
  }
}

// Handle stateless form submission
statelessChatForm.addEventListener('submit', (e: Event) => {
  e.preventDefault();
  const message = statelessMessageInput.value.trim();
  if (message) {
    sendStatelessMessage(message);
  }
});

// Handle Redis form submission
redisChatForm.addEventListener('submit', (e: Event) => {
  e.preventDefault();
  const message = redisMessageInput.value.trim();
  if (message) {
    sendRedisMessage(message);
  }
});

// Clear cache button handler
const clearCacheButton = document.getElementById(
  'clear-cache-button'
) as HTMLButtonElement;
clearCacheButton.addEventListener('click', async () => {
  if (
    confirm(
      'Clear Redis conversation cache? This will erase all conversation history but keep your health data.'
    )
  ) {
    try {
      clearCacheButton.disabled = true;
      clearCacheButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Clearing...';

      await api.clearCache(redisSessionId);

      // Clear chat areas
      redisChatArea.innerHTML = `
        <div class="message-assistant">
          <div class="message-bubble assistant">
            <i class="fas fa-hand-wave"></i> Cache cleared! I'm ready for a fresh conversation.
          </div>
        </div>
      `;

      // Reset stats
      redisStats.messageCount = 0;
      redisStats.toolsUsed = 0;
      redisStats.tokenCount = 0;
      redisStats.semanticMemories = 0;
      updateStatsTable();

      clearCacheButton.innerHTML = '<i class="fas fa-check"></i> Cleared!';
      setTimeout(() => {
        clearCacheButton.innerHTML = '<i class="fas fa-trash-alt"></i> Clear Cache';
        clearCacheButton.disabled = false;
      }, 2000);
    } catch (error) {
      console.error('Failed to clear cache:', error);
      alert('Failed to clear cache. Please try again.');
      clearCacheButton.innerHTML = '<i class="fas fa-trash-alt"></i> Clear Cache';
      clearCacheButton.disabled = false;
    }
  }
});

// Toggle control buttons visibility
const toggleControlsButton = document.getElementById(
  'toggle-controls'
) as HTMLButtonElement;
const controlButtonsContainer = document.getElementById(
  'control-buttons'
) as HTMLDivElement;

if (toggleControlsButton && controlButtonsContainer) {
  toggleControlsButton.addEventListener('click', () => {
    const isHidden = controlButtonsContainer.style.display === 'none';
    controlButtonsContainer.style.display = isHidden ? 'flex' : 'none';

    // Update icon (eye = visible, eye-slash = hidden)
    const icon = toggleControlsButton.querySelector('i');
    if (icon) {
      icon.className = isHidden ? 'fas fa-eye' : 'fas fa-eye-slash';
    }
  });
}

// Initialize
checkHealth();
setInterval(checkHealth, 30000); // Check every 30 seconds
