/**
 * Application-wide constants and configuration values
 */

// Timing intervals (milliseconds)
export const HEALTH_CHECK_INTERVAL = 30000; // 30 seconds
export const THINKING_ANIMATION_INTERVAL = 1200; // 1.2 seconds
export const SUCCESS_MESSAGE_DURATION = 2000; // 2 seconds

// UI constraints
export const MESSAGE_MAX_WIDTH = '80%';
export const MAX_MESSAGE_LENGTH = 4000; // Characters

// Thinking animation texts
export const THINKING_TEXTS = [
  'Thinking',
  'Analyzing',
  'Processing',
  'Retrieving data',
  'Computing',
] as const;

// Icons
export const REDIS_ICON = '/redis-chat-icon.svg';

// Error messages
export const ERROR_MESSAGES = {
  NETWORK: 'Network error. Please check your connection.',
  OLLAMA_DOWN: 'Ollama is not running. Please start Ollama and try again.',
  REDIS_DOWN: 'Redis is not connected. Please check Redis status.',
  GENERIC: 'An unexpected error occurred. Please try again.',
  STREAM_INTERRUPTED: 'Connection interrupted. Please try again.',
} as const;
