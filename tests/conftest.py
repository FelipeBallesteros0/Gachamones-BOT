import sys
from pathlib import Path

# Los módulos del bot viven en la raíz del proyecto.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
