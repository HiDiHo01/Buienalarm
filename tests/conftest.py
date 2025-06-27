import sys
import os
# Voeg de projectroot toe aan sys.path zodat 'custom_components' geïmporteerd kan worden
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
