# Frontend Developer Guide

Quick reference for working with the refactored Redis Wellness frontend.

---

## 🏗️ Architecture Overview

The frontend follows a **modular architecture** with clear separation of concerns:

```
User Interaction → main.ts → streaming.ts → api.ts → Backend
                      ↓
                  stats.ts (tracking)
                      ↓
                  utils/ui.ts (rendering)
                      ↓
                  utils/sanitizer.ts (security)
```

---

## 📦 Module Responsibilities

### `main.ts` (Entry Point)
**Purpose**: Application initialization and event handling
**Responsibilities**:
- DOM element references
- Event listener setup
- Health check orchestration
- Cache clearing logic

**Key Functions**:
```typescript
checkHealth()           // Updates system status badges
handleStatsUpdate()     // Refreshes stats table
```

---

### `constants.ts` (Configuration)
**Purpose**: Centralized configuration values

**Available Constants**:
```typescript
HEALTH_CHECK_INTERVAL     // 30000ms
THINKING_ANIMATION_INTERVAL  // 1200ms
SUCCESS_MESSAGE_DURATION  // 2000ms
MAX_MESSAGE_LENGTH        // 4000 characters
THINKING_TEXTS            // Animation phrases
ERROR_MESSAGES            // User-facing error strings
```

**Usage**:
```typescript
import { HEALTH_CHECK_INTERVAL, ERROR_MESSAGES } from './constants';
```

---

### `stats.ts` (State Management)
**Purpose**: Encapsulated stats tracking with type safety

**Classes**:
```typescript
// Stateless chat stats
const statelessStats = new StatelessStatsManager();
statelessStats.updateFromResponse(data);
const current = statelessStats.getStats(); // Readonly
statelessStats.reset();

// Redis chat stats (includes memory tracking)
const redisStats = new RedisStatsManager();
redisStats.updateFromResponse(data);
const current = redisStats.getStats(); // Readonly
redisStats.reset();
```

**Helper Functions**:
```typescript
updateStatsTable(statelessStats, redisStats); // Updates DOM
```

---

### `streaming.ts` (Message Streaming)
**Purpose**: Unified streaming logic with error handling

**Functions**:
```typescript
// Stateless chat
await sendStatelessMessage(message, {
  chatArea: HTMLDivElement,
  messageInput: HTMLInputElement,
  sendButton: HTMLButtonElement,
  statsManager: StatelessStatsManager,
  onStatsUpdate: () => void
});

// Redis chat with memory
await sendRedisMessage(message, sessionId, config);
```

**Features**:
- Input validation (length, empty check)
- Proper error handling (network, service, stream)
- Automatic cleanup (loading indicators)
- Stats updates on completion

---

### `utils/sanitizer.ts` (Security)
**Purpose**: XSS protection and safe HTML rendering

**Core Functions**:
```typescript
// Escape HTML entities
escapeHtml(text: string): string

// Render markdown with sanitization
renderMarkdown(text: string): string

// Safely combine icon HTML with content
createSafeHtmlWithIcon(content: string, iconHtml: string): string

// Sanitize attribute values
sanitizeAttribute(value: string): string
```

**Security Rules**:
1. All content goes through `escapeHtml()` first
2. Icons are validated (only i, img, svg, path, span allowed)
3. Never use raw innerHTML without sanitization
4. Attributes are escaped for injection prevention

---

### `utils/ui.ts` (DOM Utilities)
**Purpose**: UI components and DOM manipulation

**Classes**:
```typescript
// Loading indicator with animated text
const loader = new LoadingIndicator(chatArea);
loader.remove(); // Always clean up!

// Streaming message bubble
const bubble = new StreamingMessageBubble(chatArea, isRedisChat);
bubble.updateContent(text);        // Update incrementally
bubble.addMetadata(metadataHtml);  // Add badges
bubble.remove();                   // Clean up
```

**Helper Functions**:
```typescript
// Add message to chat (with proper sanitization)
addMessage(
  chatArea: HTMLDivElement,
  role: 'user' | 'assistant',
  content: string,
  metadata?: { tools_used, memory_stats },
  isRawHtml?: boolean,  // Only for error messages
  isRedisChat?: boolean
);

// Show error message
showError(chatArea, errorMessage, isRedisChat);
```

---

## 🔄 Common Workflows

### Adding a New Feature

1. **Add constants** (if needed) to `constants.ts`
2. **Create types** in `types.ts`
3. **Add API method** in `api.ts`
4. **Update stats** in `stats.ts` (if tracking needed)
5. **Add UI component** in `utils/ui.ts` (if needed)
6. **Wire up** in `main.ts`

### Modifying Error Messages

Edit `constants.ts`:
```typescript
export const ERROR_MESSAGES = {
  NETWORK: 'Your custom message',
  // ...
} as const;
```

### Adding New Stats

Extend the stats manager:
```typescript
// In stats.ts
export class RedisStatsManager {
  private stats: RedisStats = {
    // ... existing stats
    yourNewStat: 0,  // Add here
  };

  updateFromResponse(data: ResponseData): void {
    // Update logic
    this.stats.yourNewStat = data.yourNewValue;
  }
}
```

### Customizing UI Components

```typescript
// In utils/ui.ts
export class LoadingIndicator {
  constructor(chatArea: HTMLDivElement) {
    // Customize appearance
    this.element.innerHTML = `<div>Your custom loader</div>`;
  }
}
```

---

## 🧪 Testing

### Type Checking
```bash
npm run typecheck
```

### Linting
```bash
npm run lint        # Fix automatically
npm run lint:check  # Check only
```

### Formatting
```bash
npm run format        # Format all files
npm run format:check  # Check only
```

### Build
```bash
npm run build  # Production build
npm run dev    # Development server
```

---

## 🐛 Common Issues

### Issue: TypeScript errors after adding new module
**Solution**: Make sure exports are properly typed:
```typescript
export function myFunction(): ReturnType { }
```

### Issue: XSS vulnerability warning
**Solution**: Never use raw HTML without sanitization:
```typescript
// ❌ BAD
element.innerHTML = userContent;

// ✅ GOOD
import { renderMarkdown } from './utils/sanitizer';
element.innerHTML = renderMarkdown(userContent);
```

### Issue: Memory leak warning
**Solution**: Always clean up in finally blocks:
```typescript
try {
  const loader = new LoadingIndicator(chatArea);
  // ... work ...
} finally {
  loader.remove(); // Always clean up!
}
```

### Issue: Stats not updating
**Solution**: Ensure you call `onStatsUpdate()` callback:
```typescript
statsManager.updateFromResponse(data);
onStatsUpdate(); // Don't forget this!
```

---

## 📚 Best Practices

### 1. Always Sanitize User Input
```typescript
// Use sanitizer utilities
import { renderMarkdown } from './utils/sanitizer';
const safe = renderMarkdown(userInput);
```

### 2. Use Type-Safe Stats
```typescript
// ❌ BAD: Direct mutation
statelessStats.tokenCount = 100;

// ✅ GOOD: Use manager
statelessStatsManager.updateFromResponse({ token_count: 100 });
```

### 3. Handle All Error Cases
```typescript
try {
  await streamMessage();
} catch (error) {
  const message = getErrorMessage(error, isRedisChat);
  showError(chatArea, message, isRedisChat);
}
```

### 4. Clean Up Resources
```typescript
// Always dispose of UI components
const loader = new LoadingIndicator(chatArea);
try {
  // ... work ...
} finally {
  loader.remove();
}
```

### 5. Use Constants, Not Magic Numbers
```typescript
// ❌ BAD
setTimeout(callback, 2000);

// ✅ GOOD
import { SUCCESS_MESSAGE_DURATION } from './constants';
setTimeout(callback, SUCCESS_MESSAGE_DURATION);
```

---

## 🔍 Debugging Tips

### Enable Detailed Logging
```typescript
// In streaming.ts
console.log('Stream chunk:', chunk);
console.log('Stats updated:', statsManager.getStats());
```

### Inspect Sanitization
```typescript
// In utils/sanitizer.ts
const result = renderMarkdown(text);
console.log('Sanitized:', result);
```

### Check DOM State
```typescript
// In main.ts
console.log('Chat area:', chatArea.innerHTML);
console.log('Stats:', statelessStatsManager.getStats());
```

---

## 📖 Additional Resources

- **TypeScript Handbook**: https://www.typescriptlang.org/docs/
- **Vite Documentation**: https://vitejs.dev/
- **ESLint Rules**: See `eslint.config.js`
- **Prettier Config**: See `.prettierrc`

---

**Last Updated**: October 24, 2025
**Version**: 2.0.0 (Refactored)
