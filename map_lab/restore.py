"""Restore the analysis-only database snapshot; never overwrite a database."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import sqlite3

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,default=ROOT/'data'/'map-lab-pool.sqlite3')
    args=parser.parse_args()
    if args.output.exists():raise SystemExit(f'Refusing to overwrite existing file: {args.output}')
    report=json.loads((ROOT/'map-showcase'/'validation-report.json').read_text())
    with gzip.open(ROOT/'map-showcase'/'map-pool.sqlite3.gz','rb') as stream:raw=stream.read()
    if hashlib.sha256(raw).hexdigest()!=report['sqlite_sha256']:raise SystemExit('Snapshot checksum mismatch')
    check=sqlite3.connect(':memory:');check.deserialize(raw)
    assert check.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
    assert check.execute('SELECT COUNT(*) FROM maps').fetchone()[0]==report['records']
    assert {r[0] for r in check.execute("SELECT name FROM sqlite_master WHERE type='table'")}=={'maps','progress','metadata'}
    check.close()
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open('xb') as stream:stream.write(raw)
    print(f'Restored {report["records"]:,} analysed maps to {args.output}')


if __name__=='__main__':main()
