#!/usr/bin/env python
"""Django's command-line utility for the ecosystem demo project."""

from __future__ import annotations

import os
import sys
from pathlib import Path


def main() -> None:
    """Run administrative tasks against the local ecosystem package."""
    demo_root = Path(__file__).resolve().parent
    repo_root = demo_root.parent

    # Make ``config`` and ``demoapp`` importable.
    demo_path = str(demo_root)
    if demo_path not in sys.path:
        sys.path.insert(0, demo_path)

    # Repository root is the importable ``ecosystem`` package directory.
    # Its parent must be on ``sys.path`` so ``import ecosystem`` resolves
    # to this checkout without requiring an editable install.
    parent = str(repo_root.parent)
    if parent not in sys.path:
        sys.path.insert(0, parent)

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Install dependencies from the repository "
            "root (pip install -e .) and try again."
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
