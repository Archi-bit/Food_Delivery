"""Check real Gunicorn and Vite preview against isolated existing E2E data."""
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import time
import urllib.request

root = Path(__file__).resolve().parent.parent
node = os.environ.get('NODE_BINARY', 'node')
env = os.environ.copy()
env.update(DJANGO_DEBUG='0', DEMO_MODE='0', DJANGO_SECRET_KEY=secrets.token_urlsafe(48), DJANGO_SSL_REDIRECT='0', SQLITE_PATH=str(root/'backend/.test-data/e2e.sqlite3'))
processes=[]
try:
    processes.append(subprocess.Popen([str(root/'.venv/bin/gunicorn'), 'config.wsgi:application', '--bind', '127.0.0.1:18081', '--workers', '1'],cwd=root/'backend',env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL))
    processes.append(subprocess.Popen([node, 'node_modules/vite/bin/vite.js', 'preview', '--host', '127.0.0.1', '--port', '15174', '--strictPort'],cwd=root/'frontend',stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL))
    for port,path in [(18081,'/api/health/'),(15174,'/')]:
        for attempt in range(50):
            try:
                with urllib.request.urlopen(f'http://127.0.0.1:{port}{path}',timeout=1) as r:
                    assert r.status==200
                break
            except OSError:
                time.sleep(.1)
        else:
            raise RuntimeError(f'Server failed on {port}')
    with urllib.request.urlopen('http://127.0.0.1:18081/api/health/') as r:
        assert json.load(r)['demo_mode'] is False
    for path in ['/api/restaurants/','/api/schema/','/admin/login/']:
        with urllib.request.urlopen('http://127.0.0.1:18081'+path) as r:
            assert r.status==200
    for path in ['/','/restaurants/1','/profile']:
        with urllib.request.urlopen('http://127.0.0.1:15174'+path) as r:
            assert b'<div id="root"></div>' in r.read()
    print('Gunicorn production settings: health, restaurants, schema, admin OK')
    print('React production preview: home and SPA deep links OK')
finally:
    for process in processes:
        process.terminate()
    for process in processes:
        process.wait(timeout=10)
