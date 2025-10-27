# Production-Grade Error Handling Strategy

## Overview

This strategy establishes comprehensive error handling standards for the Redis wellness backend to achieve production-quality reliability, observability, and user experience.

## Core Principles

1. **Fail Fast, Fail Safe** - Detect errors early, provide safe fallbacks
2. **Consistent Interface** - Uniform error response format across all layers
3. **Client-Friendly** - Clear, actionable error messages for API consumers
4. **Observable** - Comprehensive logging and metrics for operations
5. **Secure** - No sensitive data exposure in error responses
6. **Resilient** - Circuit breakers and graceful degradation for dependencies

## Error Classification System

### Error Categories

#### **A. Infrastructure Errors (5xx)**
- Redis connection failures
- Database timeouts
- File system errors
- Network connectivity issues
- External service failures

#### **B. Business Logic Errors (422)**
- Invalid health data formats
- Missing required health records
- Tool execution failures
- Validation rule violations

#### **C. Client Errors (4xx)**
- Invalid input parameters (400)
- Authentication required (401)
- Forbidden access (403)
- Resource not found (404)
- Rate limiting (429)

#### **D. Critical System Errors (503)**
- Circuit breakers open
- Service unavailable
- Maintenance mode
- Resource exhaustion

## Standardized Error Response Format

### API Response Structure
```python
{
    "success": false,
    "data": null,
    "error": {
        "code": "HEALTH_DATA_NOT_FOUND",
        "message": "No health data found for the requested time period",
        "details": {
            "time_period": "last_30_days",
            "available_periods": ["last_7_days", "last_90_days"]
        },
        "correlation_id": "req_7f8a9b2c",
        "timestamp": "2025-10-21T23:15:00Z"
    }
}
```

### Error Code Naming Convention
Format: `{DOMAIN}_{RESOURCE}_{ISSUE}`

Examples:
- `HEALTH_DATA_NOT_FOUND`
- `REDIS_CONNECTION_FAILED`
- `TOOL_EXECUTION_TIMEOUT`
- `VALIDATION_INVALID_INPUT`
- `AUTH_TOKEN_EXPIRED`

## Layer-Specific Standards

### 1. API Layer (`/api/`)

**Responsibilities:**
- HTTP status code mapping
- Request validation
- Response formatting
- Rate limiting
- Authentication/authorization

**Pattern:**
```python
@router.post("/endpoint")
async def endpoint(request: RequestModel):
    try:
        # Input validation
        validate_request(request)

        # Business logic delegation
        result = await service.process(request)

        return SuccessResponse(data=result)

    except ValidationError as e:
        raise create_api_error(
            code="VALIDATION_INVALID_INPUT",
            message=str(e),
            status_code=400,
            details={"field": e.field, "value": e.value}
        )
    except BusinessLogicError as e:
        raise create_api_error(
            code=e.error_code,
            message=e.message,
            status_code=422,
            details=e.details
        )
    except InfrastructureError as e:
        raise create_api_error(
            code=e.error_code,
            message="Service temporarily unavailable",  # Don't expose internals
            status_code=503,
            correlation_id=e.correlation_id
        )
```

### 2. Service Layer (`/services/`)

**Responsibilities:**
- Business logic error handling
- Dependency coordination
- Graceful degradation
- Retry logic for transient failures

**Pattern:**
```python
class HealthDataService:
    async def get_health_data(self, user_id: str, time_period: str) -> HealthData:
        try:
            # Try primary source
            return await self._get_from_redis(user_id, time_period)

        except RedisConnectionError as e:
            logger.warning(f"Redis unavailable, falling back to cache: {e}")

            # Graceful degradation
            cached_data = await self._get_from_cache(user_id)
            if cached_data:
                return cached_data

            # If all sources fail, raise business error
            raise BusinessLogicError(
                code="HEALTH_DATA_UNAVAILABLE",
                message="Health data temporarily unavailable",
                details={"user_id": sanitize_user_id(user_id)}
            )
```

### 3. Agent Layer (`/agents/`)

**Responsibilities:**
- LLM error handling
- Tool execution failures
- Memory system failures
- Response validation

**Pattern:**
```python
class StatefulRAGAgent:
    async def chat(self, message: str, user_id: str) -> AgentResponse:
        correlation_id = generate_correlation_id()

        try:
            # Memory retrieval with degradation
            memory_context = await self._get_memory_with_fallback(
                user_id, correlation_id
            )

            # Agent execution
            result = await self._execute_agent(message, memory_context)

            return AgentResponse(
                response=result.response,
                tools_used=result.tools_used,
                memory_stats=memory_context.stats
            )

        except LLMError as e:
            # LLM failures are critical
            raise InfrastructureError(
                code="LLM_SERVICE_FAILED",
                message="AI service unavailable",
                correlation_id=correlation_id,
                original_error=e
            )
        except MemoryError as e:
            # Memory failures allow degraded mode
            logger.warning(f"Memory system degraded: {e}")
            return await self._chat_without_memory(message, correlation_id)
```

### 4. Tool Layer (`/tools/`)

**Responsibilities:**
- Tool execution errors
- Data validation
- Timeout handling
- Resource constraints

**Pattern:**
```python
@tool
def search_health_records(metric_types: list[str], time_period: str) -> ToolResult:
    try:
        # Input validation
        validate_metric_types(metric_types)
        validate_time_period(time_period)

        # Tool execution with timeout
        with timeout(30):  # 30-second timeout
            records = fetch_health_records(metric_types, time_period)

        return ToolResult(
            success=True,
            data={"records": records, "count": len(records)},
            execution_time_ms=get_execution_time()
        )

    except ValidationError as e:
        return ToolResult(
            success=False,
            error_code="TOOL_INVALID_INPUT",
            message=f"Invalid input: {e.message}",
            details={"invalid_field": e.field}
        )
    except TimeoutError:
        return ToolResult(
            success=False,
            error_code="TOOL_EXECUTION_TIMEOUT",
            message="Operation timed out after 30 seconds"
        )
    except Exception as e:
        return ToolResult(
            success=False,
            error_code="TOOL_EXECUTION_FAILED",
            message="Tool execution failed",
            correlation_id=get_current_correlation_id()
        )
```

## Exception Hierarchy

```python
# Base exception classes
class WellnessError(Exception):
    """Base exception for all wellness app errors."""
    def __init__(self, message: str, error_code: str, details: dict = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        self.timestamp = datetime.utcnow()
        self.correlation_id = get_current_correlation_id()

class BusinessLogicError(WellnessError):
    """Business logic and validation errors."""
    pass

class InfrastructureError(WellnessError):
    """Infrastructure and external service errors."""
    pass

class AuthenticationError(WellnessError):
    """Authentication and authorization errors."""
    pass

# Specific exceptions
class HealthDataNotFoundError(BusinessLogicError):
    def __init__(self, user_id: str, time_period: str):
        super().__init__(
            message=f"No health data found for time period: {time_period}",
            error_code="HEALTH_DATA_NOT_FOUND",
            details={"time_period": time_period, "user_id": sanitize_user_id(user_id)}
        )

class RedisConnectionError(InfrastructureError):
    def __init__(self, operation: str, original_error: Exception):
        super().__init__(
            message=f"Redis connection failed during {operation}",
            error_code="REDIS_CONNECTION_FAILED",
            details={"operation": operation}
        )
```

## Circuit Breaker Strategy

### Redis Circuit Breaker Enhancement
```python
class ProductionRedisCircuitBreaker:
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 30):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED
        self.metrics = CircuitBreakerMetrics()

    def execute_with_fallback(self, operation: callable, fallback: callable):
        """Execute operation with circuit breaker and fallback."""
        if not self.can_execute():
            logger.warning("Circuit breaker OPEN, using fallback")
            self.metrics.record_fallback()
            return fallback()

        try:
            result = operation()
            self.record_success()
            return result
        except Exception as e:
            self.record_failure()
            logger.error(f"Operation failed, circuit breaker state: {self.state}")

            if self.state == CircuitState.OPEN:
                self.metrics.record_fallback()
                return fallback()
            raise
```

### LLM Circuit Breaker
```python
class LLMCircuitBreaker:
    """Circuit breaker specifically for LLM API calls."""

    def __init__(self):
        self.failure_threshold = 3  # Fail faster for LLM
        self.recovery_timeout = 60  # Longer recovery for LLM
        # ... similar pattern to Redis CB

    async def call_llm_with_fallback(self, prompt: str, fallback_response: str = None):
        """Call LLM with circuit breaker and fallback response."""
        if not self.can_execute():
            if fallback_response:
                return fallback_response
            raise LLMServiceUnavailableError("LLM service circuit breaker is OPEN")

        # Execute with proper error handling...
```

## Retry Policies

```python
class RetryPolicy:
    """Configurable retry policy with exponential backoff."""

    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        backoff_factor: float = 2.0
    ):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.backoff_factor = backoff_factor

    async def execute(self, operation: callable, retryable_exceptions: tuple):
        """Execute operation with retry policy."""
        last_exception = None

        for attempt in range(self.max_retries + 1):
            try:
                return await operation()
            except retryable_exceptions as e:
                last_exception = e

                if attempt == self.max_retries:
                    break

                delay = min(
                    self.base_delay * (self.backoff_factor ** attempt),
                    self.max_delay
                )

                logger.info(f"Retry attempt {attempt + 1}, waiting {delay}s")
                await asyncio.sleep(delay)

        raise last_exception

# Usage example
retry_policy = RetryPolicy(max_retries=3, base_delay=1.0)

async def fetch_with_retry():
    return await retry_policy.execute(
        operation=lambda: redis_client.get(key),
        retryable_exceptions=(redis.ConnectionError, redis.TimeoutError)
    )
```

## Logging and Observability

### Structured Logging Format
```python
import structlog

logger = structlog.get_logger()

# Example usage
logger.info(
    "health_data_retrieved",
    user_id=sanitize_user_id(user_id),
    metric_count=len(records),
    time_period=time_period,
    execution_time_ms=execution_time,
    correlation_id=correlation_id
)

logger.error(
    "redis_connection_failed",
    error_code="REDIS_CONNECTION_FAILED",
    operation="get_health_data",
    retry_count=3,
    correlation_id=correlation_id,
    exc_info=True  # Include stack trace for errors
)
```

### Health Check Endpoints
```python
@router.get("/health")
async def health_check():
    """Comprehensive health check for all dependencies."""
    health_status = {}
    overall_healthy = True

    # Redis health
    try:
        await redis_manager.health_check()
        health_status["redis"] = {"status": "healthy", "latency_ms": 2.3}
    except Exception as e:
        health_status["redis"] = {"status": "unhealthy", "error": str(e)}
        overall_healthy = False

    # LLM health
    try:
        await llm_service.health_check()
        health_status["llm"] = {"status": "healthy", "model": "qwen2.5:7b"}
    except Exception as e:
        health_status["llm"] = {"status": "unhealthy", "error": str(e)}
        overall_healthy = False

    status_code = 200 if overall_healthy else 503
    return JSONResponse(
        status_code=status_code,
        content={
            "status": "healthy" if overall_healthy else "unhealthy",
            "timestamp": datetime.utcnow().isoformat(),
            "components": health_status
        }
    )
```

## Implementation Priority

### Phase 1: Foundation (High Priority)
1. **Exception hierarchy and base classes**
2. **API error response standardization**
3. **Structured logging setup**
4. **Health check endpoints**

### Phase 2: Resilience (Medium Priority)
1. **Circuit breaker enhancements**
2. **Retry policies implementation**
3. **Graceful degradation patterns**
4. **Error correlation IDs**

### Phase 3: Observability (Lower Priority)
1. **Error metrics and alerting**
2. **Distributed tracing**
3. **Error rate limiting**
4. **Performance monitoring**

This strategy provides a comprehensive foundation for production-quality error handling while maintaining the existing functionality and user experience.
