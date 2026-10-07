import sys
from pathlib import Path

RACINE_PROJET = Path(__file__).resolve().parents[1]

if str(RACINE_PROJET) not in sys.path:
    sys.path.insert(0, str(RACINE_PROJET))