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
 * Creates metadata HTML for tools
 * Memory retrieval now happens via tools (get_my_goals, get_tool_suggestions)
 */
function createMetadataHtml(toolsUsed?: ToolUsed[]): string {
  let metadataHtml = '';

  // Add tools used badges (includes both health tools AND memory tools)
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

  const metadataHtml = metadata ? createMetadataHtml(metadata.tools_used) : '';

  // Add Redis icon for Redis assistant messages
  const iconPrefix = isRedisChat
    ? `<img src="${REDIS_ICON}" alt="Redis" class="inline-block w-4 h-4 mr-1 align-text-bottom" />`
    : '';

  // Use raw HTML for error messages, otherwise render with sanitization
  const renderedContent = isRawHtml ? content : renderMarkdown(content);

  // Build the message structure with metadata inside the bubble
  messageDiv.innerHTML = `
    <div class="message-bubble ${role}">
      <div class="message-content">${iconPrefix}${renderedContent}</div>
      ${metadataHtml}
    </div>
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
  private lastScrollTime = 0;
  private scrollThrottle = 50; // ms

  constructor(chatArea: HTMLDivElement, isRedisChat: boolean) {
    this.element = document.createElement('div');
    this.element.className = 'message-assistant';

    this.iconHtml = isRedisChat
      ? `<img src="${REDIS_ICON}" alt="Redis" class="inline-block w-4 h-4 mr-1 align-text-bottom" />`
      : '<i class="fas fa-comment-dots" style="margin-right: 0.25rem;"></i>';

    this.element.innerHTML = `
      <div class="message-bubble assistant">
        <div class="message-content">${this.iconHtml}<span class="streaming-content"></span></div>
      </div>
    `;
    this.bubbleEl = this.element.querySelector('.message-bubble') as HTMLElement;
    this.contentEl = this.bubbleEl.querySelector('.streaming-content') as HTMLElement;

    chatArea.appendChild(this.element);
    chatArea.scrollTop = chatArea.scrollHeight;
  }

  updateContent(content: string): void {
    // Use textContent for plain text streaming (no formatting until done)
    this.contentEl.textContent = content;

    // Throttle scroll updates to reduce reflows
    const now = Date.now();
    const chatArea = this.element.parentElement;
    if (chatArea && now - this.lastScrollTime > this.scrollThrottle) {
      const isNearBottom =
        chatArea.scrollHeight - chatArea.scrollTop - chatArea.clientHeight < 100;
      if (isNearBottom) {
        chatArea.scrollTop = chatArea.scrollHeight;
      }
      this.lastScrollTime = now;
    }
  }

  finalizeContent(content: string): void {
    // Apply markdown formatting when streaming is complete
    const safeContent = createSafeHtmlWithIcon(content, '');
    this.contentEl.innerHTML = safeContent;

    // Final scroll to ensure visibility
    const chatArea = this.element.parentElement;
    if (chatArea) {
      chatArea.scrollTop = chatArea.scrollHeight;
    }
  }

  addMetadata(metadataHtml: string): void {
    // Insert metadata inside the bubble at the bottom
    if (metadataHtml) {
      this.bubbleEl.innerHTML += metadataHtml;
    }
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
