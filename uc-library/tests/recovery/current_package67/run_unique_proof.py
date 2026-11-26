"""Attributed output management only; approved adapter protocol is unchanged."""
import argparse,datetime,os,pathlib,subprocess,sys,tempfile

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--adapter',type=pathlib.Path,required=True)
    parser.add_argument('--out-root',type=pathlib.Path,required=True)
    parser.add_argument('--exe',type=pathlib.Path,required=True)
    parser.add_argument('--link-maps',type=pathlib.Path,required=True)
    args=parser.parse_args()
    root=pathlib.Path.cwd().resolve()
    output_root=args.out_root.resolve()
    assert output_root.is_relative_to(root/'temp'), 'Proof outputs must stay under project temp/'
    output_root.mkdir(parents=True,exist_ok=True)
    prefix=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')+'-'+str(os.getpid())+'-'
    directory=pathlib.Path(tempfile.mkdtemp(prefix=prefix,dir=output_root))
    output=directory/'canonical-proof.json'
    assert not output.exists()
    argv=[sys.executable,str(args.adapter.resolve()),'--exe',str(args.exe.resolve()),'--link-maps',str(args.link_maps.resolve()),'--out',str(output)]
    print('Canonical proof output: '+str(output),flush=True)
    result=subprocess.run(argv,cwd=root)
    print('Canonical proof output: '+str(output)+'; adapter exit: '+str(result.returncode),flush=True)
    if result.returncode<0:
        os.kill(os.getpid(),-result.returncode)
    return result.returncode

if __name__=='__main__':
    raise SystemExit(main())
