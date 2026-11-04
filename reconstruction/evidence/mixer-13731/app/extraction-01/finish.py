"""Append the extraction-only tracker checkpoint without replacing existing content."""
from pathlib import Path
import hashlib
import sys

root = Path(sys.argv[1]).resolve()
evidence = root/'evidence/recovery/2026-10-27/xmen-stm32'
tracker = root/('uc-library/SYMBOLS.md' if (root/'uc-library/SYMBOLS.md').exists()
                else 'temp/recovery-package/uc-library/SYMBOLS.md')
fragment = (evidence/'tracker-fragment.md').read_text()
text = tracker.read_text()
marker = '## XMEN STM32 image extraction — 2026-10-27'
if marker not in text:
    backup = evidence/('SYMBOLS-before-linux.md' if sys.platform.startswith('linux') else 'SYMBOLS-before-mac.md')
    backup.write_text(text)
    tracker.write_text(text.rstrip()+'\n'+fragment)
print('tracker', tracker, 'sha256', hashlib.sha256(tracker.read_bytes()).hexdigest())
