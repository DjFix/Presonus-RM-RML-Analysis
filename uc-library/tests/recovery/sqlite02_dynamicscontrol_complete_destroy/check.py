from pathlib import Path
import sys

task = Path(__file__).parent
sys.path.insert(0, str(task.parent / "sqlite02_dynamicscontrol_complete_construct"))
from check import main

if __name__ == "__main__":
    main(task.name)
