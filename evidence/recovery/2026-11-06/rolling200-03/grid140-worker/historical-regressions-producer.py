import importlib.util,json,subprocess
from pathlib import Path
R=Path.cwd();T=R/'uc-library/tests/recovery/grid_painter';sp=importlib.util.spec_from_file_location('gridcheck',T/'check.py');m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m)
argv=[s.replace('uc-library/tests/recovery/GridPainterReplay.cpp','uc-library/tests/recovery/rank20cycle01/rank20c01_w06/driver.cpp').replace(str(m.EXE),str(m.OUT/'orientation')) for s in m.COMPILE]
m.run(argv)
print(m.run(['uc-library/.venv/bin/python','uc-library/tests/recovery/rank20cycle01/rank20c01_w06/replay.py','--executable',str(m.OUT/'orientation'),'--fixtures','uc-library/tests/recovery/rank20cycle01/rank20c01_w06/fixtures.json']).stdout)
for mode in ['compile','symbols','native','replay']:
 print(m.run(['uc-library/.venv/bin/python','uc-library/tests/recovery/eq_draw/check.py',mode]).stdout)
