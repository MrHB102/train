#!/usr/bin/env python3
"""Explicit portable installation for Claude Code/Codex; never changes MCP settings automatically."""
import argparse
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time

HERE=Path(__file__).resolve().parent; SKILL=HERE.parent


def copy_skill(client, scope='user', project=None, dest=None, replace=False):
    if client not in ('claude','codex'): raise ValueError('client must be claude or codex')
    hidden='.claude' if client=='claude' else '.agents'
    if dest: parent=Path(dest).expanduser().resolve()
    elif scope=='project':
        if not project: raise ValueError('--project is required for project scope')
        parent=Path(project).expanduser().resolve()/hidden/'skills'
    else: parent=Path.home()/hidden/'skills'
    target=parent/'r6-animator'
    if target.resolve()==SKILL: return {'status':'already-present','path':str(target)}
    if target.exists() and not replace: raise ValueError('Skill already exists; explicit --replace is required (creates a backup)')
    if target.is_symlink(): raise ValueError('Refuse to replace a symbolic link; choose another destination')
    parent.mkdir(parents=True,exist_ok=True)
    staging=Path(tempfile.mkdtemp(prefix='r6-install-',dir=parent)); backup=None
    try:
        shutil.copytree(SKILL,staging/'r6-animator',ignore=shutil.ignore_patterns('__pycache__','*.pyc','.git'))
        if target.exists():
            backup=parent/f'r6-animator.backup-{time.time_ns()}';target.rename(backup)
        try: (staging/'r6-animator').rename(target)
        except Exception:
            if backup and not target.exists(): backup.rename(target)
            raise
    finally: shutil.rmtree(staging)
    return {'status':'installed','client':client,'path':str(target),'backup':str(backup) if backup else None}


def check():
    import r6,db,rbx
    results=[]
    def test(name,fn):
        try: fn();results.append({'check':name,'passed':True})
        except Exception as e:results.append({'check':name,'passed':False,'detail':str(e)})
    def fk(): assert abs(r6.fk({})['Head'][0][1]-4.5)<1e-9
    def database():
        assert db.db()['anims']
        assert all(not any(k in v for k in ('keys','raw','ext')) for v in db.db()['anims'].values())
    def mcp():
        p=subprocess.run([sys.executable,str(HERE/'mcp_server.py')],input='{"jsonrpc":"2.0","id":1,"method":"tools/list"}\n',capture_output=True,text=True,timeout=15)
        assert p.returncode==0 and json.loads(p.stdout)['result']['tools']
    test('canonical FK',fk);test('reference-only database',database);test('MCP stdio discovery',mcp)
    result={'passed':all(r['passed'] for r in results),'checks':results,
            'optional':{k:bool(shutil.which(k)) for k in ('blender','ffmpeg','ffprobe','yt-dlp')},
            'python_optional':{k:importlib.util.find_spec(k) is not None for k in ('PIL','numpy','matplotlib')},
            'blender_execution':'not-tested'}
    print(json.dumps(result,indent=2));return 0 if result['passed'] else 1


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--client',choices=['claude','codex']);ap.add_argument('--scope',choices=['user','project'],default='user')
    ap.add_argument('--project');ap.add_argument('--dest');ap.add_argument('--replace',action='store_true')
    group=ap.add_mutually_exclusive_group();group.add_argument('--check',action='store_true');group.add_argument('--boot',action='store_true');group.add_argument('--mcp-config',action='store_true')
    a=ap.parse_args()
    try:
        if a.check:return check()
        if a.boot: print('import sys; sys.path.insert(0, '+repr(str(HERE))+'); import r6');return 0
        if a.mcp_config:
            print(json.dumps({'command':sys.executable,'args':[str(HERE/'mcp_server.py')]},indent=2));return 0
        if a.client:print(json.dumps(copy_skill(a.client,a.scope,a.project,a.dest,a.replace),indent=2));return 0
        ap.print_help();return 0
    except (ValueError,OSError) as e:print(f'{type(e).__name__}: {e}',file=sys.stderr);return 1

if __name__=='__main__':sys.exit(main())
