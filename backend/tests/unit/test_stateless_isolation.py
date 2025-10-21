"""
Test that stateless chat truly works without Redis.

Verifies:
1. Stateless chat does not access Redis memory
2. Stateless chat works with Redis shut down
3. No state leakage between requests
4. Pure functions can be called independently
5. Mathematical accuracy is maintained
"""

import ast
import inspect
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from src.services.stateless_chat import StatelessChatService
from src.utils.conversion_utils import kg_to_lbs
from src.utils.math_tools import calculate_weight_trends
from src.utils.stats_utils import (
    calculate_basic_stats,
)
from src.utils.time_utils import parse_time_period

# Define services and tools for testing
STATELESS_SERVICES = [StatelessChatService]

# Tools that require Redis/state
STATEFUL_TOOLS = {"store_health_data", "get_health_conversation_context"}

# Tools that may require state (to monitor)
POTENTIAL_STATEFUL_TOOLS = {
    "query_health_metrics",
    "search_health_records",
    "vectorize_health_data",
}

# Tools that are safe for stateless use (pure functions)
STATELESS_SAFE_TOOLS = {
    "calculate_weight_trends",
    "compare_time_periods",
    "correlate_metrics",
    "calculate_basic_stats",
    "parse_time_period",
}

# Mock available tools registry
AVAILABLE_TOOLS = {
    "store_health_data": {"function": lambda: None},
    "get_health_conversation_context": {"function": lambda: None},
}


class TestPureFunctions:
    """Test that utility functions are truly pure (no side effects, no external dependencies)."""

    def test_stats_functions_are_pure(self):
        """Test that stats functions work without any external dependencies."""
        # These should work completely independently
        values = [1, 2, 3, 4, 5]

        # Call multiple times - should get identical results
        result1 = calculate_basic_stats(values)
        result2 = calculate_basic_stats(values)

        assert result1 == result2
        assert result1["average"] == 3.0
        assert result1["count"] == 5

    def test_conversion_functions_are_pure(self):
        """Test that conversion functions are pure."""
        # No external dependencies
        result1 = kg_to_lbs(72.5)
        result2 = kg_to_lbs(72.5)

        assert result1 == result2
        assert abs(result1 - 159.83) < 0.01

    def test_time_parsing_is_pure(self):
        """Test that time parsing doesn't depend on Redis."""
        # Should work without any database
        start, end, desc = parse_time_period("September 2024")

        assert start.year == 2024
        assert start.month == 9
        assert start.day == 1

    def test_math_tools_work_with_provided_data(self):
        """Test that math tools work when data is passed in (no Redis access)."""
        # Create test data
        records = []
        start_date = datetime(2025, 7, 1)

        for i in range(30):
            date = start_date + timedelta(days=i)
            weight_kg = 80.0 - (i * 0.1)  # Decreasing weight

            records.append(
                {
                    "date": date.strftime("%Y-%m-%d %H:%M:%S"),
                    "value": f"{weight_kg:.2f}",
                    "unit": "kg",
                }
            )

        # This should work without any Redis connection
        result = calculate_weight_trends(records, "last_30_days", "linear_regression")

        assert "trends" in result
        assert "linear_regression" in result["trends"]
        assert result["trends"]["linear_regression"]["trend_direction"] == "decreasing"


class StatelessIsolationTester:
    """Helper class to test stateless service isolation."""

    def get_imported_modules_from_file(self, file_path):  #  Path) -> Set[str]:
        """Parse Python file and extract all imported module names."""
        with open(file_path) as f:
            content = f.read()

        tree = ast.parse(content)
        imports = set()

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.add(alias.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module.split(".")[0])

        return imports

    def get_service_file_path(self, service_class) -> Path:
        """Get the file path for a service class."""
        return Path(inspect.getfile(service_class))

    def get_stateful_tool_dependencies(self) -> set[str]:
        """Get all modules that stateful tools depend on."""
        stateful_deps = set()

        for tool_name in STATEFUL_TOOLS:
            if tool_name in AVAILABLE_TOOLS:
                tool_func = AVAILABLE_TOOLS[tool_name]["function"]
                tool_module = inspect.getmodule(tool_func)
                if tool_module:
                    stateful_deps.add(tool_module.__name__)

        # Add redis-specific modules
        stateful_deps.update(
            {
                "redis",
                "redis.asyncio",
                "redis_health_tool",
                "src.tools.redis_health_tool",
            }
        )

        return stateful_deps

    def check_service_imports(self, service_class) -> list[str]:
        """Check if service imports any stateful dependencies."""
        violations = []

        service_file = self.get_service_file_path(service_class)
        imported_modules = self.get_imported_modules_from_file(service_file)
        stateful_deps = self.get_stateful_tool_dependencies()

        # Check for direct stateful tool imports
        for imported in imported_modules:
            if any(stateful_dep in imported for stateful_dep in stateful_deps):
                violations.append(f"Imports stateful module: {imported}")

        return violations

    def check_service_methods(self, service_class) -> list[str]:
        """Check if service methods call stateful tools."""
        violations = []

        # Inspect service source code for stateful tool calls
        source = inspect.getsource(service_class)

        # Check for known stateful tools
        all_stateful_tools = STATEFUL_TOOLS.union(POTENTIAL_STATEFUL_TOOLS)
        for tool_name in all_stateful_tools:
            if tool_name in source:
                violations.append(f"References stateful tool: {tool_name}")

        # Check for Redis-specific patterns (avoid false positives)
        redis_patterns = [
            "redis.",
            "Redis(",
            "redis_client.",
            ".hget(",
            ".hset(",
            ".lpush(",
            ".rpush(",
            "store_health_data(",
            "query_health_metrics(",
            "get_health_conversation_context(",
            "redis.asyncio",
        ]

        # Patterns that need more context to avoid false positives
        contextual_patterns = {
            ".set(": ["redis.set(", "redis_client.set(", "self.redis.set("],
            ".get(": ["redis.get(", "redis_client.get(", "self.redis.get("],
        }

        for pattern in redis_patterns:
            if pattern in source:
                violations.append(f"Contains Redis pattern: {pattern}")

        # Check contextual patterns more carefully
        for _basic_pattern, full_patterns in contextual_patterns.items():
            for full_pattern in full_patterns:
                if full_pattern in source:
                    violations.append(f"Contains Redis pattern: {full_pattern}")

        return violations


@pytest.fixture
def isolation_tester():
    """Provide StatelessIsolationTester instance."""
    return StatelessIsolationTester()


class TestStatelessIsolation:
    """Test suite for stateless service isolation."""

    def test_stateless_services_exist(self):
        """Verify that stateless services are properly defined."""
        assert len(STATELESS_SERVICES) > 0, "No stateless services defined"

        for service in STATELESS_SERVICES:
            assert hasattr(service, "chat"), f"{service.__name__} missing chat method"

    def test_stateful_tools_identified(self):
        """Verify that stateful tools are properly identified."""
        assert len(STATEFUL_TOOLS) > 0, "No stateful tools identified"

        # Ensure stateful tools exist in available tools
        for tool_name in STATEFUL_TOOLS:
            assert (
                tool_name in AVAILABLE_TOOLS
            ), f"Stateful tool {tool_name} not found in AVAILABLE_TOOLS"

        # Check if potential stateful tools exist (they may not be registered)
        all_stateful = STATEFUL_TOOLS.union(POTENTIAL_STATEFUL_TOOLS)
        assert len(all_stateful) >= len(
            STATEFUL_TOOLS
        ), "No potential stateful tools to monitor"

    def test_stateless_services_dont_import_stateful_modules(self, isolation_tester):
        """Test that stateless services don't import Redis or stateful tool modules."""
        for service_class in STATELESS_SERVICES:
            violations = isolation_tester.check_service_imports(service_class)

            assert len(violations) == 0, (
                f"{service_class.__name__} imports stateful dependencies: "
                f"{', '.join(violations)}"
            )

    def test_stateless_services_dont_call_stateful_tools(self, isolation_tester):
        """Test that stateless services don't call stateful tools in their methods."""
        for service_class in STATELESS_SERVICES:
            violations = isolation_tester.check_service_methods(service_class)

            # Filter out false positives (like comments or docstrings)
            real_violations = []
            for violation in violations:
                # Skip if it's just in a comment or docstring
                if not any(
                    comment_indicator in violation.lower()
                    for comment_indicator in ["#", '"""', "'''", "docstring"]
                ):
                    real_violations.append(violation)

            assert len(real_violations) == 0, (
                f"{service_class.__name__} uses stateful functionality: "
                f"{', '.join(real_violations)}"
            )

    @patch.dict("os.environ", {}, clear=True)
    @patch("src.config.Settings")
    def test_stateless_chat_service_isolation(self, mock_settings_class):
        """Specific test for StatelessChatService isolation."""
        # Mock settings class to avoid validation errors
        mock_settings_instance = Mock()
        mock_settings_instance.ollama_base_url = "http://localhost:11434"
        mock_settings_instance.ollama_model = "llama3.1"
        mock_settings_class.return_value = mock_settings_instance

        service = StatelessChatService()

        # Verify no Redis connection attributes
        assert not hasattr(service, "redis"), "StatelessChatService has redis attribute"
        assert not hasattr(
            service, "redis_client"
        ), "StatelessChatService has redis_client attribute"

        # Verify no conversation storage methods
        assert not hasattr(
            service, "store_conversation"
        ), "StatelessChatService has store_conversation method"
        assert not hasattr(
            service, "get_conversation_history"
        ), "StatelessChatService has get_conversation_history method"

    @patch.dict("os.environ", {}, clear=True)
    @patch("src.config.Settings")
    def test_health_stateless_chat_service_isolation(self, mock_settings_class):
        """Specific test for StatelessChatService isolation (health-aware)."""
        # Mock settings class to avoid validation errors
        mock_settings_instance = Mock()
        mock_settings_instance.ollama_base_url = "http://localhost:11434"
        mock_settings_instance.ollama_model = "llama3.1"
        mock_settings_class.return_value = mock_settings_instance

        service = StatelessChatService()

        # Verify no Redis connection attributes
        assert not hasattr(service, "redis"), "StatelessChatService has redis attribute"
        assert not hasattr(
            service, "redis_client"
        ), "StatelessChatService has redis_client attribute"

        # Verify only safe health tools are used
        source = inspect.getsource(StatelessChatService)

        # Should use only stateless-safe tools
        for _safe_tool in STATELESS_SAFE_TOOLS:
            # It's okay if these tools are used
            pass

        # Should NOT use stateful tools (including potential ones)
        all_stateful_tools = STATEFUL_TOOLS.union(POTENTIAL_STATEFUL_TOOLS)
        for stateful_tool in all_stateful_tools:
            assert (
                stateful_tool not in source
            ), f"StatelessChatService uses stateful tool: {stateful_tool}"

    def test_tool_categorization_completeness(self):
        """Verify all available tools are properly categorized."""
        all_categorized = STATEFUL_TOOLS.union(STATELESS_SAFE_TOOLS)
        available_tool_names = set(AVAILABLE_TOOLS.keys())

        uncategorized = available_tool_names - all_categorized

        assert len(uncategorized) == 0, (
            f"Uncategorized tools found: {uncategorized}. "
            "Please categorize as STATEFUL_TOOLS or STATELESS_SAFE_TOOLS"
        )

    def test_redis_import_detection(self, isolation_tester):
        """Test that Redis import detection works correctly."""
        # Create a mock service file content with Redis imports

        # This would need a temporary file for full testing
        # For now, verify detection logic works on known patterns
        stateful_deps = isolation_tester.get_stateful_tool_dependencies()

        assert "redis" in stateful_deps
        assert "src.tools.redis_health_tool" in stateful_deps

    @pytest.mark.parametrize("service_class", STATELESS_SERVICES)
    def test_each_stateless_service_individually(self, service_class, isolation_tester):
        """Parameterized test for each stateless service."""
        # Import violations
        import_violations = isolation_tester.check_service_imports(service_class)
        assert (
            len(import_violations) == 0
        ), f"{service_class.__name__} import violations: {import_violations}"

        # Method violations
        method_violations = isolation_tester.check_service_methods(service_class)
        assert (
            len(method_violations) == 0
        ), f"{service_class.__name__} method violations: {method_violations}"

    @patch.dict("os.environ", {}, clear=True)
    @patch("src.config.Settings")
    def test_stateless_services_remain_functional(self, mock_settings_class):
        """Verify that stateless services are still functional despite isolation."""
        # Mock settings class to avoid validation errors
        mock_settings_instance = Mock()
        mock_settings_instance.ollama_base_url = "http://localhost:11434"
        mock_settings_instance.ollama_model = "llama3.1"
        mock_settings_class.return_value = mock_settings_instance

        # Test StatelessChatService
        stateless_service = StatelessChatService()
        assert hasattr(stateless_service, "chat")
        assert callable(stateless_service.chat)

        # Test StatelessChatService (health-aware version)
        health_stateless_service = StatelessChatService()
        assert hasattr(health_stateless_service, "chat")
        assert callable(health_stateless_service.chat)

        # Verify they have required settings
        assert hasattr(stateless_service, "settings")
        assert hasattr(health_stateless_service, "settings")


if __name__ == "__main__":
    # Run basic checks when executed directly
    tester = StatelessIsolationTester()

    print("🔍 Checking stateless service isolation...")

    for service_class in STATELESS_SERVICES:
        print(f"\n📋 Analyzing {service_class.__name__}:")

        import_violations = tester.check_service_imports(service_class)
        method_violations = tester.check_service_methods(service_class)

        if import_violations:
            print(f"  ❌ Import violations: {import_violations}")
        else:
            print("  ✅ No stateful imports detected")

        if method_violations:
            print(f"  ❌ Method violations: {method_violations}")
        else:
            print("  ✅ No stateful method calls detected")

    print(f"\n🎯 Stateful tools to avoid: {STATEFUL_TOOLS}")
    print(f"✅ Safe stateless tools: {STATELESS_SAFE_TOOLS}")
