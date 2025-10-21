export interface ChatRequest {
  message: string;
  session_id?: string;
}

export interface ChatResponse {
  response: string;
  session_id?: string;
  type?: 'stateless' | 'redis';
}

export interface StatelessChatRequest {
  message: string;
}

export interface StatelessChatResponse {
  response: string;
  type: 'stateless';
}

export interface RedisChatRequest {
  message: string;
  session_id?: string;
}

export interface ToolUsed {
  name: string;
  args: Record<string, unknown>;
}

export interface MemoryStats {
  short_term_available: boolean;
  semantic_hits: number;
  long_term_available: boolean;
}

export interface RedisChatResponse {
  response: string;
  session_id: string;
  tools_used: ToolUsed[];
  tool_calls_made: number;
  memory_stats: MemoryStats;
  type: 'redis_with_memory';
}

export interface HealthCheckResponse {
  status: string;
  redis_connected: boolean;
  ollama_connected: boolean;
}

export interface Message {
  role: 'user' | 'assistant';
  content: string;
}
