# Single User Configuration Implementation

## Overview

This application has been updated to enforce single-user mode throughout the codebase. The system now uses a consistent user ID configuration that eliminates hardcoded user references and provides flexibility through environment variables.

## Key Changes

### 1. **New Single User Configuration Module**
**File**: `src/utils/user_config.py`

- ✅ **Centralized user ID management** - Single source of truth for user configuration
- ✅ **Environment variable support** - Configurable via `WELLNESS_USER_ID` environment variable
- ✅ **Default user ID** - Falls back to `wellness_user` if no environment variable set
- ✅ **Validation and normalization** - Warns if different user IDs are provided
- ✅ **Redis key generation** - Consistent key patterns for health data and sessions

### 2. **Updated Core Services**

#### **Redis Chat Service** (`src/services/redis_chat.py`)
- ✅ Uses `extract_user_id_from_session()` for single-user mode
- ✅ Session keys now use `get_user_session_key()` for consistency
- ✅ Eliminates hardcoded `"your_user"` references

#### **Stateless Chat Service** (`src/services/stateless_chat.py`)
- ✅ Uses `get_user_id()` instead of hardcoded `"your_user"`
- ✅ Consistent user ID across stateless operations

#### **Memory Manager** (`src/services/memory_manager.py`)
- ✅ Updated session key generation to use single user configuration
- ✅ User ID validation before memory operations

### 3. **Updated Agent Tools** (`src/tools/agent_tools.py`)
- ✅ **User context validation** - All tools normalize user IDs on creation
- ✅ **Consistent Redis keys** - Uses `get_user_health_data_key()` throughout
- ✅ **Single user binding** - Tools bound to validated single user context

### 4. **Updated API Routes**
- ✅ **Chat routes** use `get_user_id()` for token usage checks
- ✅ **Health routes** include single user mode indicators
- ✅ **Consistent user context** across all endpoints

## Configuration Options

### Environment Variable Setup
```bash
# Set custom user ID (optional)
export WELLNESS_USER_ID="my_personal_health_user"

# Use default if not set
# Default: "wellness_user"
```

### Redis Key Patterns
The system now generates consistent Redis keys:

```
# Health data
health:user:{user_id}:data

# Session data
session:{user_id}:{session_id}

# Memory data
memory:{user_id}:{memory_type}
```

## Benefits

### 1. **Consistency**
- ✅ Single source of truth for user configuration
- ✅ No more mixed `"your_user"`, `"demo_user"`, `"test_user"` references
- ✅ Consistent Redis key patterns throughout

### 2. **Flexibility**
- ✅ Configurable via environment variables
- ✅ Easy to customize for different deployment scenarios
- ✅ Maintains single-user constraint while allowing personalization

### 3. **Maintainability**
- ✅ Centralized user management reduces code duplication
- ✅ Clear separation between single-user logic and application logic
- ✅ Easier to extend if multi-user support is needed in the future

### 4. **Production Readiness**
- ✅ No hardcoded user IDs in production code
- ✅ Environment-based configuration
- ✅ Proper validation and error handling

## Usage Examples

### Basic Usage
```python
from src.utils.user_config import get_user_id, get_user_health_data_key

# Get the configured user ID
user_id = get_user_id()  # Returns: "wellness_user" or env value

# Get Redis keys
health_key = get_user_health_data_key()  # Returns: "health:user:wellness_user:data"
```

### Tool Creation (automatically validates user)
```python
from src.tools.agent_tools import create_user_bound_tools

# User ID is automatically validated and normalized
tools = create_user_bound_tools("any_user_id_here")  # Uses configured single user
```

### Service Integration
```python
from src.utils.user_config import validate_user_context

# Ensures single user consistency
def process_user_data(provided_user_id: str):
    # Always returns the configured single user ID
    actual_user_id = validate_user_context(provided_user_id)
    # ... process with normalized user ID
```

## Migration Notes

### Before (Inconsistent)
```python
# Multiple hardcoded references throughout codebase
user_id = "wellness_user"    # In some files
user_id = "demo_user"        # In other files
user_id = "test_user"        # In test files
redis_key = f"health:user:{user_id}:data"  # Manual key construction
```

### After (Consistent)
```python
# Single source of truth
from src.utils.user_config import get_user_id, get_user_health_data_key

user_id = get_user_id()                    # Centralized configuration
redis_key = get_user_health_data_key()     # Standardized key generation
```

## Testing

The single user configuration has been tested to ensure:

- ✅ **Default behavior** - Returns `"wellness_user"` when no environment variable set
- ✅ **Environment override** - Respects `WELLNESS_USER_ID` environment variable
- ✅ **User validation** - Warns when different user IDs provided but maintains consistency
- ✅ **Redis key generation** - Produces consistent, properly formatted keys
- ✅ **Import compatibility** - All existing imports continue to work

## Health Check Integration

The health check endpoints now include single user mode indicators:

```json
{
  "status": "healthy",
  "user_mode": "single_user",
  "user_id": "wellness_user",
  "configured_user_id": "wellness_user"
}
```

## Future Considerations

This implementation provides a clean foundation that:

1. **Maintains single-user constraint** while eliminating hardcoded values
2. **Provides configuration flexibility** for different deployment scenarios
3. **Establishes patterns** that could support multi-user extension if needed
4. **Ensures production readiness** with proper error handling and validation

The system successfully eliminates all hardcoded user references while maintaining the single-user design principle and adding production-grade configuration management.
