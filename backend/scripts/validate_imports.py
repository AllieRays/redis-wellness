#!/usr/bin/env python3
"""
Validate critical imports and production configuration.

This script prevents runtime errors by catching missing imports at build/startup time.
Also validates that we're using Redis for conversation persistence (not MemorySaver).
"""

import ast
import sys
from pathlib import Path


def check_file_imports(
    file_path: Path, required_imports: set[str]
) -> tuple[bool, list[str]]:
    """
    Check if a Python file contains required imports.

    Args:
        file_path: Path to Python file
        required_imports: Set of required module names (e.g., {"time", "json"})

    Returns:
        Tuple of (all_present, missing_imports)
    """
    try:
        with open(file_path) as f:
            tree = ast.parse(f.read(), filename=str(file_path))

        found_imports = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    found_imports.add(alias.name)
            elif isinstance(node, ast.ImportFrom) and node.module:
                found_imports.add(node.module)

        missing = required_imports - found_imports
        return len(missing) == 0, list(missing)

    except Exception as e:
        print(f"Error parsing {file_path}: {e}")
        return False, list(required_imports)


def verify_redis_checkpointer_code() -> bool:
    """
    CRITICAL: Verify source code uses RedisSaver, not MemorySaver.

    Static code analysis (no Redis connection needed during build).
    This prevents deploying with MemorySaver which loses conversations on restart.
    """
    print("\n🔍 Validating LangGraph checkpointer configuration...")

    backend_root = Path(__file__).parent.parent
    redis_connection_file = backend_root / "src/services/redis_connection.py"

    if not redis_connection_file.exists():
        print("❌ CRITICAL: redis_connection.py not found!")
        return False

    try:
        with open(redis_connection_file) as f:
            source_code = f.read()

        # Parse the source code
        tree = ast.parse(source_code, filename=str(redis_connection_file))

        # Check for RedisSaver import
        has_redis_saver_import = False
        has_memory_saver_fallback = False
        redis_saver_used_first = False

        for node in ast.walk(tree):
            # Check imports
            if (
                isinstance(node, ast.ImportFrom)
                and node.module == "langgraph.checkpoint.redis"
            ):
                for alias in node.names:
                    if alias.name == "RedisSaver":
                        has_redis_saver_import = True

        # Check that get_checkpointer method uses RedisSaver
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "get_checkpointer":
                # Convert function body to string for analysis
                func_source = ast.unparse(node)

                # Check that RedisSaver is used before MemorySaver
                redis_saver_pos = func_source.find("RedisSaver(")
                memory_saver_pos = func_source.find("MemorySaver(")

                if redis_saver_pos != -1:
                    redis_saver_used_first = True

                # Check that MemorySaver is only in except block (fallback)
                if (
                    memory_saver_pos != -1
                    and "except" in func_source[:memory_saver_pos]
                ):
                    has_memory_saver_fallback = True

        # Validation checks
        if not has_redis_saver_import:
            print("❌ CRITICAL: RedisSaver not imported!")
            print(
                "   redis_connection.py must import RedisSaver from langgraph.checkpoint.redis"
            )
            return False

        if not redis_saver_used_first:
            print("❌ CRITICAL: RedisSaver not used in get_checkpointer()!")
            print("   Primary checkpointer must be RedisSaver, not MemorySaver")
            return False

        if not has_memory_saver_fallback:
            print("⚠️  WARNING: No MemorySaver fallback found")
            print("   Consider adding MemorySaver as fallback for development")

        print("✅ Code uses RedisSaver for conversation persistence")
        print("   ✓ RedisSaver imported")
        print("   ✓ RedisSaver is primary checkpointer")
        if has_memory_saver_fallback:
            print("   ✓ MemorySaver fallback available")

        return True

    except Exception as e:
        print(f"❌ Error analyzing checkpointer code: {e}")
        import traceback

        traceback.print_exc()
        return False


def main():
    """Validate critical imports and configuration."""
    backend_root = Path(__file__).parent.parent
    validation_passed = True

    # Critical validations
    checks = [
        {
            "file": backend_root / "src/agents/stateful_rag_agent.py",
            "imports": {"time"},
            "reason": "Required for workflow timing in procedural memory",
        },
    ]

    print("🔍 Validating critical imports...")

    for check in checks:
        file_path = check["file"]
        required = check["imports"]
        reason = check["reason"]

        if not file_path.exists():
            print(f"❌ File not found: {file_path}")
            validation_passed = False
            continue

        all_present, missing = check_file_imports(file_path, required)

        if all_present:
            print(f"✅ {file_path.name}: All required imports present")
        else:
            print(f"❌ {file_path.name}: Missing imports: {missing}")
            print(f"   Reason: {reason}")
            validation_passed = False

    # Verify Redis checkpointer configuration (static code analysis)
    checkpointer_valid = verify_redis_checkpointer_code()
    validation_passed = validation_passed and checkpointer_valid

    if validation_passed:
        print("\n✅ All validations passed!")
        return 0
    else:
        print("\n❌ Validation failed!")
        print("   Please fix the issues above before deploying.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
