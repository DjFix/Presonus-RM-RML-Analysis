"""List only the new classification journals for a bounded evidence transfer."""
import json
from pathlib import Path

repo = Path('/home/rs/projects/opencs/ai-line-analysis')
library = repo / 'uc-library'
records = {str(p.relative_to(library)): json.loads(p.read_text())
           for p in sorted((library / 'validation/history').glob('classification-*.json'))}
print(json.dumps(records, indent=2))
