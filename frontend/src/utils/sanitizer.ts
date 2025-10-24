/**
 * HTML sanitization utilities to prevent XSS attacks
 */

/**
 * Escapes HTML special characters to prevent XSS
 */
export function escapeHtml(text: string): string {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

/**
 * Renders markdown-like text with proper HTML escaping
 * Supports: **bold**, *bold*, numbered lists, bullet points, line breaks
 */
export function renderMarkdown(text: string): string {
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

/**
 * Safely creates HTML with icon prefix and sanitized content
 * This ensures icon HTML doesn't break sanitization
 */
export function createSafeHtmlWithIcon(content: string, iconHtml: string): string {
  // Sanitize the content first
  const safeContent = renderMarkdown(content);

  // Create a temporary container to validate icon HTML
  const tempDiv = document.createElement('div');
  tempDiv.innerHTML = iconHtml;

  // Only allow simple icon elements (i, img, svg)
  const allowedTags = ['I', 'IMG', 'SVG', 'PATH', 'SPAN'];
  const firstChild = tempDiv.firstElementChild;

  if (!firstChild || !allowedTags.includes(firstChild.tagName)) {
    // If icon HTML is suspicious, skip it
    return safeContent;
  }

  return iconHtml + safeContent;
}

/**
 * Validates that a string is safe for use as HTML attribute value
 */
export function sanitizeAttribute(value: string): string {
  return value.replace(/['"<>&]/g, char => {
    const entities: Record<string, string> = {
      "'": '&#39;',
      '"': '&quot;',
      '<': '&lt;',
      '>': '&gt;',
      '&': '&amp;',
    };
    return entities[char] || char;
  });
}
