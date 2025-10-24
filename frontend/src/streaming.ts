/**
 * Unified streaming message handler with proper error handling and cleanup
 */

import { api } from './api';
import {
  LoadingIndicator,
  StreamingMessageBubble,
  showError,
  addMessage,
} from './utils/ui';
import { ERROR_MESSAGES, MAX_MESSAGE_LENGTH } from './constants';
import type { StatelessStatsManager, RedisStatsManager } from './stats';
import type { ToolUsed, MemoryStats } from './types';

interface StreamingConfig {
  chatArea: HTMLDivElement;
  messageInput: HTMLInputElement;
  sendButton: HTMLButtonElement;
  statsManager: StatelessStatsManager | RedisStatsManager;
  onStatsUpdate: () => void;
}

interface StreamMetadata {
  tools_used?: ToolUsed[];
  memory_stats?: MemoryStats;
  tool_calls_made?: number;
  response_time_ms?: number;
  token_stats?: {
    token_count: number;
    usage_percent: number;
    is_over_threshold: boolean;
  };
}

/**
 * Validates user message input
 */
function validateMessage(message: string): string | null {
  const trimmed = message.trim();

  if (!trimmed) {
    return 'Please enter a message';
  }

  if (trimmed.length > MAX_MESSAGE_LENGTH) {
    return `Message is too long (max ${MAX_MESSAGE_LENGTH} characters)`;
  }

  return null;
}

/**
 * Determines the specific error message based on error type
 */
function getErrorMessage(error: unknown, isRedisChat: boolean): string {
  if (error instanceof TypeError && error.message.includes('fetch')) {
    return ERROR_MESSAGES.NETWORK;
  }

  if (error instanceof Error) {
    const message = error.message.toLowerCase();

    if (message.includes('ollama')) {
      return ERROR_MESSAGES.OLLAMA_DOWN;
    }

    if (message.includes('redis') && isRedisChat) {
      return ERROR_MESSAGES.REDIS_DOWN;
    }

    if (message.includes('stream') || message.includes('interrupted')) {
      return ERROR_MESSAGES.STREAM_INTERRUPTED;
    }
  }

  return ERROR_MESSAGES.GENERIC;
}

/**
 * Creates metadata HTML for Redis chat messages
 */
function createMetadataHtml(metadata: StreamMetadata): string {
  let metadataHtml = '';

  if (metadata.memory_stats) {
    const stats = metadata.memory_stats;
    const memoryIndicators: string[] = [];

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

  if (metadata.tools_used && metadata.tools_used.length > 0) {
    const toolsList = metadata.tools_used
      .map(
        tool =>
          `<span class="tool-badge"><i class="fas fa-wrench"></i> ${tool.name}</span>`
      )
      .join(' ');
    metadataHtml += `<div class="message-metadata tools-used">${toolsList}</div>`;
  }

  return metadataHtml;
}

/**
 * Handles streaming for stateless chat
 */
export async function sendStatelessMessage(
  message: string,
  config: StreamingConfig
): Promise<void> {
  const validationError = validateMessage(message);
  if (validationError) {
    showError(config.chatArea, validationError, false);
    return;
  }

  addMessage(config.chatArea, 'user', message);
  config.messageInput.value = '';
  config.sendButton.disabled = true;

  const loadingIndicator = new LoadingIndicator(config.chatArea);
  let streamingBubble: StreamingMessageBubble | null = null;
  let responseText = '';
  let firstTokenReceived = false;

  try {
    for await (const chunk of api.streamStatelessMessage({ message })) {
      if (chunk.type === 'token' && chunk.content) {
        // Remove loading indicator and create streaming bubble on first token
        if (!firstTokenReceived) {
          loadingIndicator.remove();
          streamingBubble = new StreamingMessageBubble(config.chatArea, false);
          firstTokenReceived = true;
        }

        responseText += chunk.content;
        streamingBubble!.updateContent(responseText);
      } else if (chunk.type === 'done' && chunk.data) {
        // Update stats
        config.statsManager.updateFromResponse(chunk.data);
        config.onStatsUpdate();
      }
    }
  } catch (error) {
    console.error('Stateless streaming error:', error);

    if (streamingBubble && firstTokenReceived) {
      streamingBubble.remove();
    }

    loadingIndicator.remove();

    const errorMessage = getErrorMessage(error, false);
    showError(config.chatArea, errorMessage, false);
  } finally {
    config.sendButton.disabled = false;
    config.messageInput.focus();
  }
}

/**
 * Handles streaming for Redis chat with memory
 */
export async function sendRedisMessage(
  message: string,
  sessionId: string,
  config: StreamingConfig
): Promise<void> {
  const validationError = validateMessage(message);
  if (validationError) {
    showError(config.chatArea, validationError, true);
    return;
  }

  addMessage(config.chatArea, 'user', message);
  config.messageInput.value = '';
  config.sendButton.disabled = true;

  const loadingIndicator = new LoadingIndicator(config.chatArea);
  let streamingBubble: StreamingMessageBubble | null = null;
  let responseText = '';
  let firstTokenReceived = false;

  try {
    for await (const chunk of api.streamRedisMessage({
      message,
      session_id: sessionId,
    })) {
      if (chunk.type === 'token' && chunk.content) {
        // Remove loading indicator and create streaming bubble on first token
        if (!firstTokenReceived) {
          loadingIndicator.remove();
          streamingBubble = new StreamingMessageBubble(config.chatArea, true);
          firstTokenReceived = true;
        }

        responseText += chunk.content;
        streamingBubble!.updateContent(responseText);
      } else if (chunk.type === 'done' && chunk.data) {
        // Add metadata after streaming completes
        const metadataHtml = createMetadataHtml(chunk.data);
        if (metadataHtml && streamingBubble) {
          streamingBubble.addMetadata(metadataHtml);
        }

        // Update stats
        config.statsManager.updateFromResponse(chunk.data);
        config.onStatsUpdate();
      }
    }
  } catch (error) {
    console.error('Redis streaming error:', error);

    if (streamingBubble && firstTokenReceived) {
      streamingBubble.remove();
    }

    loadingIndicator.remove();

    const errorMessage = getErrorMessage(error, true);
    showError(config.chatArea, errorMessage, true);
  } finally {
    config.sendButton.disabled = false;
    config.messageInput.focus();
  }
}
