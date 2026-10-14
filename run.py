"""
FlowPilot Primary Entrypoint
Launches the native desktop application.
"""

import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from desktop_app import main

if __name__ == "__main__":
    main()
