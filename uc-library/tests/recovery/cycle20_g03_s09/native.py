"""Replay this original ChannelInfo entry with the shared native fixture harness."""
import importlib.util
from pathlib import Path

path = Path(__file__).parent.parent / "cycle20_g03_s06" / "native.py"
spec = importlib.util.spec_from_file_location("channel_info_native", path)
harness = importlib.util.module_from_spec(spec)
spec.loader.exec_module(harness)
NAME = harness.TARGETS["09"][0]

if __name__ == "__main__":
    harness.main("09")
