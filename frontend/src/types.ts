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

export interface RedisChatResponse {
  response: string;
  session_id: string;
  type: 'redis';
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
