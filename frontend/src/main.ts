import './style.css';
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
  }
): void {
  const messageDiv = document.createElement('div');
  messageDiv.className = `message ${role}`;

  let metadataHtml = '';

  // Add memory stats for Redis chat
  if (role === 'assistant' && metadata?.memory_stats) {
    const stats = metadata.memory_stats;
    const memoryIndicators = [];

    if (stats.short_term_available) {
      memoryIndicators.push('<span class="memory-badge">📝 Short-term memory</span>');
    }
    if (stats.semantic_hits > 0) {
      memoryIndicators.push(
        `<span class="memory-badge semantic">🧠 ${stats.semantic_hits} semantic memories</span>`
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
      .map(tool => `<span class="tool-badge">🔧 ${tool.name}</span>`)
      .join(' ');
    metadataHtml += `<div class="message-metadata tools-used">${toolsList}</div>`;
  }

  messageDiv.innerHTML = `
    <div class="message-content">${renderMarkdown(content)}</div>
    ${metadataHtml}
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
  const statelessMsgEl = document.getElementById('stat-stateless-msg');
  const statelessTokensEl = document.getElementById('stat-stateless-tokens');
  const statelessUsageEl = document.getElementById('stat-stateless-usage');
  const statelessToolsEl = document.getElementById('stat-stateless-tools');
  const statelessLatencyEl = document.getElementById('stat-stateless-latency');

  if (statelessMsgEl) statelessMsgEl.textContent = String(statelessStats.messageCount);
  if (statelessTokensEl)
    statelessTokensEl.textContent = String(statelessStats.tokenCount);
  if (statelessUsageEl) statelessUsageEl.textContent = 'N/A';
  if (statelessToolsEl) statelessToolsEl.textContent = String(statelessStats.toolsUsed);
  if (statelessLatencyEl) {
    statelessLatencyEl.textContent =
      statelessStats.avgResponseTime > 0
        ? `${statelessStats.avgResponseTime.toFixed(0)}ms`
        : 'N/A';
  }

  // Update Redis stats
  const redisMsgEl = document.getElementById('stat-redis-msg');
  const redisTokensEl = document.getElementById('stat-redis-tokens');
  const redisUsageEl = document.getElementById('stat-redis-usage');
  const redisToolsEl = document.getElementById('stat-redis-tools');
  const redisSemanticEl = document.getElementById('stat-redis-semantic');
  const redisTrimmingEl = document.getElementById('stat-redis-trimming');
  const redisLatencyEl = document.getElementById('stat-redis-latency');

  if (redisMsgEl) redisMsgEl.textContent = String(redisStats.messageCount);
  if (redisTokensEl) redisTokensEl.textContent = String(redisStats.tokenCount);
  if (redisUsageEl)
    redisUsageEl.textContent =
      redisStats.tokenUsagePercent > 0
        ? `${redisStats.tokenUsagePercent.toFixed(1)}%`
        : 'N/A';
  if (redisToolsEl) redisToolsEl.textContent = String(redisStats.toolsUsed);
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

// Show loading indicator
function showLoading(chatArea: HTMLDivElement): HTMLDivElement {
  const loadingDiv = document.createElement('div');
  loadingDiv.className = 'loading';
  loadingDiv.textContent = '💭 Thinking...';
  chatArea.appendChild(loadingDiv);
  chatArea.scrollTop = chatArea.scrollHeight;
  return loadingDiv;
}

// Remove loading indicator
function removeLoading(chatArea: HTMLDivElement, loadingDiv: HTMLDivElement): void {
  if (chatArea.contains(loadingDiv)) {
    chatArea.removeChild(loadingDiv);
  }
}

// Send stateless message
async function sendStatelessMessage(message: string): Promise<void> {
  addMessage(statelessChatArea, 'user', message);
  statelessMessageInput.value = '';
  statelessSendButton.disabled = true;

  const loadingDiv = showLoading(statelessChatArea);

  try {
    const data = await api.sendStatelessMessage({ message });

    removeLoading(statelessChatArea, loadingDiv);
    addMessage(statelessChatArea, 'assistant', data.response);

    // Update stats - use ACTUAL data from agent response
    statelessStats.messageCount += 2; // user + assistant
    statelessStats.toolsUsed += data.tool_calls_made || 0; // Actual tool calls
    // Note: Stateless has no token tracking (no memory to accumulate)
    // We could estimate ~1200 tokens per message but that's not accurate
    statelessStats.tokenCount = 0; // No context accumulation

    // Update response time metrics (if available)
    if (data.response_time_ms !== undefined) {
      statelessStats.lastResponseTime = data.response_time_ms;
      statelessStats.totalResponseTime += data.response_time_ms;
      const responseCount = statelessStats.messageCount / 2; // Divide by 2 since we count user+assistant
      statelessStats.avgResponseTime = statelessStats.totalResponseTime / responseCount;
    }

    updateStatsTable();
  } catch (error) {
    console.error('Error sending stateless message:', error);
    removeLoading(statelessChatArea, loadingDiv);
    addMessage(
      statelessChatArea,
      'assistant',
      '❌ Sorry, I encountered an error. Please make sure Ollama is running.'
    );
  } finally {
    statelessSendButton.disabled = false;
    statelessMessageInput.focus();
  }
}

// Send Redis message
async function sendRedisMessage(message: string): Promise<void> {
  addMessage(redisChatArea, 'user', message);
  redisMessageInput.value = '';
  redisSendButton.disabled = true;

  const loadingDiv = showLoading(redisChatArea);

  try {
    const data = await api.sendRedisMessage({
      message,
      session_id: redisSessionId,
    });

    removeLoading(redisChatArea, loadingDiv);
    addMessage(redisChatArea, 'assistant', data.response, {
      tools_used: data.tools_used,
      memory_stats: data.memory_stats,
    });

    // Update stats - Redis with memory and tokens
    redisStats.messageCount += 2; // user + assistant
    redisStats.toolsUsed += data.tool_calls_made;
    redisStats.semanticMemories = data.memory_stats.semantic_hits;

    // Update token stats from response
    if (data.token_stats && data.token_stats.token_count !== undefined) {
      redisStats.tokenCount = data.token_stats.token_count;
      redisStats.tokenUsagePercent = data.token_stats.usage_percent;
      redisStats.isOverThreshold = data.token_stats.is_over_threshold;
    }

    // Update response time metrics (if available)
    if (data.response_time_ms !== undefined) {
      redisStats.lastResponseTime = data.response_time_ms;
      redisStats.totalResponseTime += data.response_time_ms;
      const responseCount = redisStats.messageCount / 2; // Divide by 2 since we count user+assistant
      redisStats.avgResponseTime = redisStats.totalResponseTime / responseCount;
    }

    updateStatsTable();
  } catch (error) {
    console.error('Error sending Redis message:', error);
    removeLoading(redisChatArea, loadingDiv);
    addMessage(
      redisChatArea,
      'assistant',
      '❌ Sorry, I encountered an error. Please make sure Ollama and Redis are running.'
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

// Initialize
checkHealth();
setInterval(checkHealth, 30000); // Check every 30 seconds
