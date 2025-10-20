import type {
  ChatRequest,
  ChatResponse,
  StatelessChatRequest,
  StatelessChatResponse,
  RedisChatRequest,
  RedisChatResponse,
  HealthCheckResponse,
} from './types';

const API_BASE_URL = import.meta.env.DEV ? 'http://localhost:8000' : '';

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
    return this.request<StatelessChatResponse>('/api/chat/stateless/', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async sendRedisMessage(data: RedisChatRequest): Promise<RedisChatResponse> {
    return this.request<RedisChatResponse>('/api/chat/redis/', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async healthCheck(): Promise<HealthCheckResponse> {
    return this.request<HealthCheckResponse>('/api/health/check');
  }
}

export const api = new ApiClient();
