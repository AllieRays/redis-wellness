import './style.css';
import '@fortawesome/fontawesome-free/css/all.css';
import { api } from './api';
import { StatelessStatsManager, RedisStatsManager, updateStatsTable } from './stats';
import { sendStatelessMessage, sendRedisMessage } from './streaming';
import { HEALTH_CHECK_INTERVAL, SUCCESS_MESSAGE_DURATION } from './constants';

// Session management - persist across page reloads
function getOrCreateSessionId(): string {
  const storageKey = 'redis-session-id';
  let sessionId = localStorage.getItem(storageKey);

  if (!sessionId) {
    sessionId = `real-health-${Date.now()}`;
    localStorage.setItem(storageKey, sessionId);
  }

  return sessionId;
}

const redisSessionId: string = getOrCreateSessionId();

// Stats managers
const statelessStatsManager = new StatelessStatsManager();
const redisStatsManager = new RedisStatsManager();

// DOM element references
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

/**
 * Checks system health and updates status badges
 */
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
    // Update badges to show disconnected state
    redisStatus.className = 'status-badge disconnected';
    redisStatus.textContent = 'Redis: Unknown';
    ollamaStatus.className = 'status-badge disconnected';
    ollamaStatus.textContent = 'Ollama: Unknown';
  }
}

/**
 * Updates stats table with current values from managers
 */
function handleStatsUpdate(): void {
  updateStatsTable(statelessStatsManager.getStats(), redisStatsManager.getStats());
}

// Handle stateless form submission
statelessChatForm.addEventListener('submit', (e: Event) => {
  e.preventDefault();
  const message = statelessMessageInput.value.trim();
  if (message) {
    sendStatelessMessage(message, {
      chatArea: statelessChatArea,
      messageInput: statelessMessageInput,
      sendButton: statelessSendButton,
      statsManager: statelessStatsManager,
      onStatsUpdate: handleStatsUpdate,
    });
  }
});

// Handle Redis form submission
redisChatForm.addEventListener('submit', (e: Event) => {
  e.preventDefault();
  const message = redisMessageInput.value.trim();
  if (message) {
    sendRedisMessage(message, redisSessionId, {
      chatArea: redisChatArea,
      messageInput: redisMessageInput,
      sendButton: redisSendButton,
      statsManager: redisStatsManager,
      onStatsUpdate: handleStatsUpdate,
    });
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

      // Clear chat area
      redisChatArea.innerHTML = `
        <div class="message-assistant">
          <div class="message-bubble assistant">
            <i class="fas fa-hand-wave"></i> Cache cleared! I'm ready for a fresh conversation.
          </div>
        </div>
      `;

      // Clear localStorage session
      localStorage.removeItem('redis-session-id');

      // Reset stats manager
      redisStatsManager.reset();
      handleStatsUpdate();

      clearCacheButton.innerHTML = '<i class="fas fa-check"></i> Cleared!';
      setTimeout(() => {
        clearCacheButton.innerHTML = '<i class="fas fa-trash-alt"></i> Clear Cache';
        clearCacheButton.disabled = false;
      }, SUCCESS_MESSAGE_DURATION);
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

// Global error handler for unhandled promise rejections
window.addEventListener('unhandledrejection', (event: PromiseRejectionEvent) => {
  console.error('Unhandled promise rejection:', event.reason);
  // Optionally show user-facing error notification
  event.preventDefault(); // Prevent default browser behavior
});

// Initialize application
checkHealth();
const healthCheckInterval = setInterval(checkHealth, HEALTH_CHECK_INTERVAL);

// Cleanup on page unload (though browser typically handles this)
window.addEventListener('beforeunload', () => {
  clearInterval(healthCheckInterval);
});
