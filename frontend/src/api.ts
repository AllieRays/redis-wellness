import type {
  ChatRequest,
  ChatResponse,
  StatelessChatRequest,
  StatelessChatResponse,
  RedisChatRequest,
  RedisChatResponse,
  HealthCheckResponse,
} from './types';

// In development: use explicit localhost URL
// In production: use relative URLs (same origin, proxied by nginx)
const API_BASE_URL = import.meta.env.DEV
  ? 'http://localhost:8000'
  : import.meta.env.VITE_API_BASE_URL || '';

class ApiClient {
  private async request<T>(endpoint: string, options?: RequestInit): Promise<T> {
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
      ...options,
    });

    if (!response.ok) {
      throw new Error(`API error: ${response.statusText}`);
    }

    return response.json();
  }

  async sendMessage(data: ChatRequest): Promise<ChatResponse> {
    return this.request<ChatResponse>('/api/chat', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async sendStatelessMessage(
    data: StatelessChatRequest
  ): Promise<StatelessChatResponse> {
    return this.request<StatelessChatResponse>('/api/chat/stateless', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async *streamStatelessMessage(data: StatelessChatRequest): AsyncGenerator<{
    type: string;
    content?: string;
    data?: Partial<StatelessChatResponse>;
  }> {
    const response = await fetch(`${API_BASE_URL}/api/chat/stateless/stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });

    if (!response.ok) throw new Error(`Stream error: ${response.statusText}`);
    if (!response.body) throw new Error('No response body');

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = JSON.parse(line.slice(6));
          yield data;
        }
      }
    }
  }

  async sendRedisMessage(data: RedisChatRequest): Promise<RedisChatResponse> {
    return this.request<RedisChatResponse>('/api/chat/stateful', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async *streamRedisMessage(data: RedisChatRequest): AsyncGenerator<{
    type: string;
    content?: string;
    data?: Partial<RedisChatResponse>;
  }> {
    const response = await fetch(`${API_BASE_URL}/api/chat/stateful/stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });

    if (!response.ok) throw new Error(`Stream error: ${response.statusText}`);
    if (!response.body) throw new Error('No response body');

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = JSON.parse(line.slice(6));
          yield data;
        }
      }
    }
  }

  async healthCheck(): Promise<HealthCheckResponse> {
    return this.request<HealthCheckResponse>('/api/health/check');
  }

  async clearCache(sessionId: string): Promise<{ success: boolean; message: string }> {
    return this.request(`/api/chat/session/${sessionId}`, {
      method: 'DELETE',
    });
  }
}

export const api = new ApiClient();
