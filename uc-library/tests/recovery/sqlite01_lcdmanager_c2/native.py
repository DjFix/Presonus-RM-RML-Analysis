"""Use the same LCDManager native oracle with the separately sealed C2 context."""

import runpy
from pathlib import Path

if __name__ == "__main__":
    runpy.run_path(
        str(Path(__file__).resolve().parents[1] / "sqlite01_lcdmanager_c1/native.py"),
        run_name="__main__",
    )
