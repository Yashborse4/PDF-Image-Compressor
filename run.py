"""
DocuTools Launcher script.
Execute with: python run.py
"""

import sys
from pathlib import Path

# Ensure docutools directory is in sys.path
root_dir = Path(__file__).resolve().parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from docutools.app import main

if __name__ == "__main__":
    sys.exit(main())
