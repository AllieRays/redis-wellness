/**
 * UI utilities for DOM manipulation and visual feedback
 */

import { THINKING_TEXTS, THINKING_ANIMATION_INTERVAL, REDIS_ICON } from '../constants';
import { createSafeHtmlWithIcon, renderMarkdown } from './sanitizer';
import type { ToolUsed, MemoryStats } from '../types';

/**
 * Loading indicator with animated thinking text
 */
export class LoadingIndicator {
  private element: HTMLDivElement;
  private intervalId: number | null = null;
  private textIndex = 0;
  private thinkingSpan: HTMLElement | null = null;

  constructor(chatArea: HTMLDivElement) {
    this.element = document.createElement('div');
    this.element.className = 'message-assistant';
    this.element.innerHTML = `
      <div class="message-bubble assistant">
        <i class="fas fa-spinner fa-spin" style="margin-right: 0.5rem;"></i>
        <span class="thinking-text">Thinking...</span>
      </div>
    `;
    chatArea.appendChild(this.element);
    chatArea.scrollTop = chatArea.scrollHeight;

    this.thinkingSpan = this.element.querySelector('.thinking-text');
    this.startAnimation();
  }

  private startAnimation(): void {
    this.intervalId = window.setInterval(() => {
      this.textIndex = (this.textIndex + 1) % THINKING_TEXTS.length;
      if (this.thinkingSpan) {
        this.thinkingSpan.textContent = THINKING_TEXTS[this.textIndex] + '...';
      }
    }, THINKING_ANIMATION_INTERVAL);
  }

  remove(): void {
    if (this.intervalId !== null) {
      clearInterval(this.intervalId);
      this.intervalId = null;
    }
    if (this.element.parentElement) {
      this.element.parentElement.removeChild(this.element);
    }
  }

  getElement(): HTMLDivElement {
    return this.element;
  }
}

/**
 * Creates metadata HTML for memory stats and tools
 */
function createMetadataHtml(toolsUsed?: ToolUsed[], memoryStats?: MemoryStats): string {
  let metadataHtml = '';

  // Add memory stats badges
  if (memoryStats) {
    const memoryIndicators: string[] = [];

    if (memoryStats.short_term_available) {
      memoryIndicators.push(
        '<span class="memory-badge"><i class="fas fa-file-lines"></i> Short-term memory</span>'
      );
    }
    if (memoryStats.semantic_hits > 0) {
      memoryIndicators.push(
        `<span class="memory-badge semantic"><i class="fas fa-brain"></i> ${memoryStats.semantic_hits} semantic memories</span>`
      );
    }

    if (memoryIndicators.length > 0) {
      metadataHtml = `<div class="message-metadata">${memoryIndicators.join(
        ' '
      )}</div>`;
    }
  }

  // Add tools used badges
  if (toolsUsed && toolsUsed.length > 0) {
    const toolsList = toolsUsed
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
 * Adds a message to the chat area with proper sanitization
 */
export function addMessage(
  chatArea: HTMLDivElement,
  role: 'user' | 'assistant',
  content: string,
  metadata?: {
    tools_used?: ToolUsed[];
    memory_stats?: MemoryStats;
  },
  isRawHtml = false,
  isRedisChat = false
): void {
  const messageDiv = document.createElement('div');
  messageDiv.className = role === 'user' ? 'message-user' : 'message-assistant';

  const metadataHtml = metadata
    ? createMetadataHtml(metadata.tools_used, metadata.memory_stats)
    : '';

  // Add Redis icon for Redis assistant messages
  const iconPrefix = isRedisChat
    ? `<img src="${REDIS_ICON}" alt="Redis" class="inline-block w-4 h-4 mr-1 align-text-bottom" />`
    : '';

  // Use raw HTML for error messages, otherwise render with sanitization
  const renderedContent = isRawHtml ? content : renderMarkdown(content);

  messageDiv.innerHTML = `
    <div class="message-bubble ${role}">${iconPrefix}${renderedContent}${metadataHtml}</div>
  `;

  chatArea.appendChild(messageDiv);
  chatArea.scrollTop = chatArea.scrollHeight;
}

/**
 * Streaming message bubble that updates incrementally
 */
export class StreamingMessageBubble {
  private element: HTMLDivElement;
  private bubbleEl: HTMLElement;
  private iconHtml: string;
  private contentEl: HTMLElement;

  constructor(chatArea: HTMLDivElement, isRedisChat: boolean) {
    this.element = document.createElement('div');
    this.element.className = 'message-assistant';

    this.iconHtml = isRedisChat
      ? `<img src="${REDIS_ICON}" alt="Redis" class="inline-block w-4 h-4 mr-1 align-text-bottom" />`
      : '<i class="fas fa-comment-dots" style="margin-right: 0.25rem;"></i>';

    this.element.innerHTML = `<div class="message-bubble assistant">${this.iconHtml}<span class="streaming-content"></span></div>`;
    this.bubbleEl = this.element.querySelector('.message-bubble') as HTMLElement;
    this.contentEl = this.bubbleEl.querySelector('.streaming-content') as HTMLElement;

    chatArea.appendChild(this.element);
    chatArea.scrollTop = chatArea.scrollHeight;
  }

  updateContent(content: string): void {
    const safeContent = createSafeHtmlWithIcon(content, '');
    this.contentEl.innerHTML = safeContent;

    // Scroll to bottom
    const chatArea = this.element.parentElement;
    if (chatArea) {
      chatArea.scrollTop = chatArea.scrollHeight;
    }
  }

  addMetadata(metadataHtml: string): void {
    this.bubbleEl.innerHTML += metadataHtml;
  }

  remove(): void {
    if (this.element.parentElement) {
      this.element.parentElement.removeChild(this.element);
    }
  }

  getElement(): HTMLDivElement {
    return this.element;
  }
}

/**
 * Shows an error message in the chat
 */
export function showError(
  chatArea: HTMLDivElement,
  errorMessage: string,
  isRedisChat = false
): void {
  const iconHtml = '<i class="fas fa-exclamation-triangle"></i>';
  addMessage(
    chatArea,
    'assistant',
    `${iconHtml} ${errorMessage}`,
    undefined,
    true,
    isRedisChat
  );
}
