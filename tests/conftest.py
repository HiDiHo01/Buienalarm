import sys
import os
from pathlib import Path
repo_root = Path(__file__).parent.parent
sys.path.insert(0, str(repo_root))
# Voeg de projectroot toe aan sys.path zodat 'custom_components' geïmporteerd kan worden
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
