"""Run the shared DAW mapping replay checker for the meter selection."""
from pathlib import Path
import sys

FOLDER = Path(__file__).resolve().parent
sys.path.insert(0, str(FOLDER.parent / 'rolling_next_daw_mix'))
from check import main

if __name__ == '__main__':
    main(FOLDER.name)
