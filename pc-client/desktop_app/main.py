"""Desktop client entry point for the shrimp monitor application."""

from __future__ import annotations

import pathlib
import sys

CURRENT_DIR = pathlib.Path(__file__).resolve().parent
PARENT_DIR = CURRENT_DIR.parent
if str(PARENT_DIR) not in sys.path:
    sys.path.insert(0, str(PARENT_DIR))

from desktop_app.ui.main_window import run


if __name__ == "__main__":
    run()
