"""Adapt identical exported CSV rows to Neo4j offline import headers."""
import argparse
import pathlib
import shutil

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--run', required=True)
args = parser.parse_args()
run = pathlib.Path(args.run)
for name, header in [('nodes', 'id:ID,kind,label,metadata\n'),
                     ('edges', ':START_ID,:END_ID,:TYPE,evidence\n')]:
    with (run / (name + '.csv')).open('rb') as source:
        source.readline()
        with (run / ('neo4j-' + name + '.csv')).open('xb') as target:
            target.write(header.encode())
            shutil.copyfileobj(source, target)
