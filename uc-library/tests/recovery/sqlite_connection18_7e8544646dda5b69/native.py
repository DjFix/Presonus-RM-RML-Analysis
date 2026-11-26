import runpy,pathlib,sys
p=pathlib.Path(__file__).resolve()
runpy.run_path(str(p.parent.parent/"connection_transport_eighteen/run_all.py"))["native"](p.parent.name,"--verify" in sys.argv)
