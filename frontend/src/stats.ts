/**
 * Stats tracking and management for chat performance metrics
 */

export interface ChatStats {
  messageCount: number;
  toolsUsed: number;
  tokenCount: number;
  totalResponseTime: number;
  avgResponseTime: number;
  lastResponseTime: number;
}

export interface RedisStats extends ChatStats {
  tokenUsagePercent: number;
  semanticMemories: number;
  proceduralPatterns: number;
  isOverThreshold: boolean;
}

/**
 * Stats manager for stateless chat
 */
export class StatelessStatsManager {
  private stats: ChatStats = {
    messageCount: 0,
    toolsUsed: 0,
    tokenCount: 0,
    totalResponseTime: 0,
    avgResponseTime: 0,
    lastResponseTime: 0,
  };

  updateFromResponse(data: {
    tool_calls_made?: number;
    response_time_ms?: number;
  }): void {
    this.stats.messageCount += 2; // User + assistant message
    this.stats.toolsUsed += data.tool_calls_made || 0;

    if (data.response_time_ms !== undefined) {
      this.stats.lastResponseTime = data.response_time_ms;
      this.stats.totalResponseTime += data.response_time_ms;
      const responseCount = this.stats.messageCount / 2;
      this.stats.avgResponseTime = this.stats.totalResponseTime / responseCount;
    }
  }

  getStats(): Readonly<ChatStats> {
    return { ...this.stats };
  }

  reset(): void {
    this.stats = {
      messageCount: 0,
      toolsUsed: 0,
      tokenCount: 0,
      totalResponseTime: 0,
      avgResponseTime: 0,
      lastResponseTime: 0,
    };
  }
}

/**
 * Stats manager for Redis chat with memory tracking
 */
export class RedisStatsManager {
  private stats: RedisStats = {
    messageCount: 0,
    toolsUsed: 0,
    tokenCount: 0,
    tokenUsagePercent: 0,
    semanticMemories: 0,
    proceduralPatterns: 0,
    isOverThreshold: false,
    totalResponseTime: 0,
    avgResponseTime: 0,
    lastResponseTime: 0,
  };

  updateFromResponse(data: {
    tool_calls_made?: number;
    response_time_ms?: number;
    memory_stats?: { semantic_hits: number; procedural_patterns_used: number };
    token_stats?: {
      token_count: number;
      usage_percent: number;
      is_over_threshold: boolean;
    };
  }): void {
    this.stats.messageCount += 2; // User + assistant message
    this.stats.toolsUsed += data.tool_calls_made || 0;
    this.stats.semanticMemories = data.memory_stats?.semantic_hits || 0;
    this.stats.proceduralPatterns = data.memory_stats?.procedural_patterns_used || 0;

    if (data.token_stats) {
      this.stats.tokenCount = data.token_stats.token_count || 0;
      this.stats.tokenUsagePercent = data.token_stats.usage_percent || 0;
      this.stats.isOverThreshold = data.token_stats.is_over_threshold || false;
    }

    if (data.response_time_ms !== undefined) {
      this.stats.lastResponseTime = data.response_time_ms;
      this.stats.totalResponseTime += data.response_time_ms;
      const responseCount = this.stats.messageCount / 2;
      this.stats.avgResponseTime = this.stats.totalResponseTime / responseCount;
    }
  }

  getStats(): Readonly<RedisStats> {
    return { ...this.stats };
  }

  reset(): void {
    this.stats = {
      messageCount: 0,
      toolsUsed: 0,
      tokenCount: 0,
      tokenUsagePercent: 0,
      semanticMemories: 0,
      proceduralPatterns: 0,
      isOverThreshold: false,
      totalResponseTime: 0,
      avgResponseTime: 0,
      lastResponseTime: 0,
    };
  }
}

/**
 * Updates the stats comparison table in the DOM
 */
export function updateStatsTable(
  statelessStats: Readonly<ChatStats>,
  redisStats: Readonly<RedisStats>
): void {
  // Update stateless stats
  const statelessTokensEl = document.getElementById('stat-stateless-tokens');
  const statelessLatencyEl = document.getElementById('stat-stateless-latency');

  if (statelessTokensEl) {
    statelessTokensEl.textContent = String(statelessStats.tokenCount);
  }
  if (statelessLatencyEl) {
    if (statelessStats.avgResponseTime > 0) {
      const responseCount = statelessStats.messageCount / 2;
      statelessLatencyEl.textContent = `${statelessStats.avgResponseTime.toFixed(0)}ms`;
      statelessLatencyEl.title = `Based on ${responseCount} response(s)`;
    } else {
      statelessLatencyEl.textContent = '—';
      statelessLatencyEl.title = 'No responses yet';
    }
  }

  // Update Redis stats
  const redisTokensEl = document.getElementById('stat-redis-tokens');
  const redisSemanticEl = document.getElementById('stat-redis-semantic');
  const redisProceduralEl = document.getElementById('stat-redis-procedural');
  const redisLatencyEl = document.getElementById('stat-redis-latency');

  if (redisTokensEl) {
    redisTokensEl.textContent = String(redisStats.tokenCount);
  }
  if (redisSemanticEl) {
    redisSemanticEl.textContent = String(redisStats.semanticMemories);
  }
  if (redisProceduralEl) {
    redisProceduralEl.textContent = String(redisStats.proceduralPatterns);
  }
  if (redisLatencyEl) {
    if (redisStats.avgResponseTime > 0) {
      const responseCount = redisStats.messageCount / 2;
      redisLatencyEl.textContent = `${redisStats.avgResponseTime.toFixed(0)}ms`;
      redisLatencyEl.title = `Based on ${responseCount} response(s)`;
    } else {
      redisLatencyEl.textContent = '—';
      redisLatencyEl.title = 'No responses yet';
    }
  }
}
