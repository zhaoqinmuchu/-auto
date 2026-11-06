import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from App.ashare_bsp_scanner_gui import get_tradable_stocks

df = get_tradable_stocks()
print("total stocks:", len(df))
print("columns:", list(df.columns))
print(df.head(10))
