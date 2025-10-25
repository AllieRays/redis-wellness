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
  tools_used: ToolUsed[];
  tool_calls_made: number;
  validation: Record<string, unknown>;
  type: 'stateless';
  response_time_ms?: number;
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
  procedural_patterns_used: number;
  memory_type?: 'episodic' | 'procedural' | 'semantic' | 'none'; // NEW: Which memory type was actually used
}

export interface TokenStats {
  message_count: number;
  token_count: number;
  max_tokens: number;
  usage_percent: number;
  threshold_percent: number;
  is_over_threshold: boolean;
}

export interface RedisChatResponse {
  response: string;
  session_id: string;
  tools_used: ToolUsed[];
  tool_calls_made: number;
  memory_stats: MemoryStats;
  token_stats?: TokenStats;
  type: 'redis_with_memory';
  response_time_ms?: number;
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
