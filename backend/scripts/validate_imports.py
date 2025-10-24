#!/usr/bin/env python3
"""
Validate critical imports are present in the codebase.

This script prevents runtime errors by catching missing imports at build/startup time.
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


def main():
    """Validate critical imports in key files."""
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

    if validation_passed:
        print("\n✅ All import validations passed!")
        return 0
    else:
        print("\n❌ Import validation failed!")
        print("   Please ensure all required imports are present before deploying.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
