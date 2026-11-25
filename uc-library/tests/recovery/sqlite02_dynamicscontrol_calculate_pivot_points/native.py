import json
from pathlib import Path
import sys

task = Path(__file__).parent
sys.path.insert(0, str(task.parent / "sqlite02_dynamicscontrol_complete_construct"))
from native import observe

if __name__ == "__main__":
    print(json.dumps(observe(task.name), indent=2))
