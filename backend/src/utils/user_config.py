"""
Single user configuration for the wellness application.

This application is designed for single-user usage (personal health data).
This module provides consistent user ID management across the entire codebase.
"""

import os

# Default user ID that can be overridden by environment variable
DEFAULT_USER_ID = "wellness_user"


def get_user_id() -> str:
    """
    Get the single user ID for the application.

    Returns the user ID from environment variable WELLNESS_USER_ID if set,
    otherwise returns the default user ID.

    Returns:
        str: The user ID to use throughout the application
    """
    return os.getenv("WELLNESS_USER_ID", DEFAULT_USER_ID)


def extract_user_id_from_session(session_id: str) -> str:
    """
    Extract user ID from session ID (for backward compatibility).

    Since this is a single-user application, this always returns
    the configured user ID regardless of the session.

    Args:
        session_id: Session identifier (ignored in single-user mode)

    Returns:
        str: The configured user ID
    """
    return get_user_id()


def validate_user_context(user_id: str | None = None) -> str:
    """
    Validate and normalize user context.

    In single-user mode, this ensures consistency by always returning
    the configured user ID, regardless of what was passed in.

    Args:
        user_id: Optional user ID (ignored in single-user mode)

    Returns:
        str: The normalized user ID
    """
    configured_user_id = get_user_id()

    # Log warning if different user ID was provided
    if user_id and user_id != configured_user_id:
        import logging

        logger = logging.getLogger(__name__)
        logger.warning(
            f"Single-user mode: ignoring provided user_id '{user_id}', using '{configured_user_id}'"
        )

    return configured_user_id


def get_user_redis_key_prefix() -> str:
    """
    Get Redis key prefix for the single user.

    Returns:
        str: Redis key prefix for user data
    """
    return f"user:{get_user_id()}"


def get_user_health_data_key() -> str:
    """
    Get Redis key for user's health data.

    Returns:
        str: Redis key for health data storage
    """
    return f"health:user:{get_user_id()}:data"


def get_user_session_key(session_id: str) -> str:
    """
    Get Redis key for user's session data.

    Args:
        session_id: Session identifier

    Returns:
        str: Redis key for session storage
    """
    return f"session:{get_user_id()}:{session_id}"


def get_user_memory_key_prefix() -> str:
    """
    Get Redis key prefix for user's memory data.

    Returns:
        str: Redis key prefix for memory storage
    """
    return f"memory:{get_user_id()}"


# Convenience function for tools that need user-bound operations
def create_user_bound_operation(operation_name: str) -> str:
    """
    Create a user-bound operation identifier.

    Args:
        operation_name: Name of the operation

    Returns:
        str: User-bound operation identifier
    """
    return f"{get_user_id()}:{operation_name}"


class SingleUserConfig:
    """Configuration class for single-user application settings."""

    def __init__(self):
        self.user_id = get_user_id()
        self.redis_key_prefix = get_user_redis_key_prefix()
        self.health_data_key = get_user_health_data_key()

    def get_session_key(self, session_id: str) -> str:
        """Get session key for the configured user."""
        return get_user_session_key(session_id)

    def get_memory_key(self, memory_type: str) -> str:
        """Get memory key for the configured user."""
        return f"{get_user_memory_key_prefix()}:{memory_type}"

    def __str__(self) -> str:
        return f"SingleUserConfig(user_id='{self.user_id}')"


# Global configuration instance
_user_config = None


def get_user_config() -> SingleUserConfig:
    """
    Get the global single user configuration instance.

    Returns:
        SingleUserConfig: The global user configuration
    """
    global _user_config
    if _user_config is None:
        _user_config = SingleUserConfig()
    return _user_config


# Export commonly used functions
__all__ = [
    "get_user_id",
    "extract_user_id_from_session",
    "validate_user_context",
    "get_user_config",
    "get_user_redis_key_prefix",
    "get_user_health_data_key",
    "get_user_session_key",
    "get_user_memory_key_prefix",
    "SingleUserConfig",
]
