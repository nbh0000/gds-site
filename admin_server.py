#!/usr/bin/env python3
"""GDS site admin server.

Serves the static site and provides a small JSON API used by admin.html:
  POST /api/login            {password}              -> {token}
  POST /api/logout
  GET  /api/content                                  -> content.json (public; also used by index.html)
  POST /api/content          {text,plain,img,href,src}  (auth)
  POST /api/upload           {name, data(base64)}    (auth) -> {path}
  POST /api/inquiry          {company,name,...}      (public, from the site form)
  GET  /api/inquiries                                (auth)
  POST /api/inquiries/update {id, read} | {id, delete:true}  (auth)
  POST /api/password         {current, new}          (auth)

Run:  python admin_server.py [port]      (default 8765)
Admin page: http://localhost:8765/admin.html   (initial password: gds1234)
"""
import base64, hashlib, hmac, json, os, re, secrets, sys, threading, time
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

ROOT = os.path.dirname(os.path.abspath(__file__))
CONTENT = os.path.join(ROOT, 'content.json')
INQUIRIES = os.path.join(ROOT, 'inquiries.json')
CONFIG = os.path.join(ROOT, 'admin_config.json')
ASSETS = os.path.join(ROOT, 'assets')
DEFAULT_PASSWORD = 'gds1234'
TOKENS = {}
LOCK = threading.Lock()


def _hash(pw, salt):
    return hashlib.pbkdf2_hmac('sha256', pw.encode('utf-8'), bytes.fromhex(salt), 120000).hex()


def load_config():
    if not os.path.exists(CONFIG):
        salt = secrets.token_hex(16)
        cfg = {'salt': salt, 'hash': _hash(DEFAULT_PASSWORD, salt)}
        save_json(CONFIG, cfg)
        print(f'[admin] created {CONFIG} with initial password "{DEFAULT_PASSWORD}" - change it in admin.html > 설정')
    with open(CONFIG, encoding='utf-8') as f:
        return json.load(f)


def load_json(path, default):
    if not os.path.exists(path):
        return default
    with open(path, encoding='utf-8') as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return default


def save_json(path, data):
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=ROOT, **kw)

    def log_message(self, fmt, *args):
        sys.stdout.write('[%s] %s\n' % (time.strftime('%H:%M:%S'), fmt % args))

    # ---- helpers
    def _json(self, code, obj):
        body = json.dumps(obj, ensure_ascii=False).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _body(self, limit=25 * 1024 * 1024):
        n = int(self.headers.get('Content-Length') or 0)
        if n > limit:
            raise ValueError('too large')
        raw = self.rfile.read(n) if n else b''
        return json.loads(raw.decode('utf-8')) if raw else {}

    def _auth(self):
        tok = self.headers.get('X-Auth-Token', '')
        with LOCK:
            exp = TOKENS.get(tok)
            if exp and exp > time.time():
                TOKENS[tok] = time.time() + 12 * 3600
                return True
            TOKENS.pop(tok, None)
        return False

    def end_headers(self):
        p = self.path.split('?')[0]
        if p.endswith(('.html', '.json', '.js', '.css')) or p in ('/', ''):
            self.send_header('Cache-Control', 'no-store')
        super().end_headers()

    # ---- routes
    def do_GET(self):
        p = urlparse(self.path).path
        if p == '/api/content':
            return self._json(200, load_json(CONTENT, {}))
        if p == '/api/inquiries':
            if not self._auth():
                return self._json(401, {'error': 'unauthorized'})
            return self._json(200, load_json(INQUIRIES, []))
        if p in ('/admin_config.json', '/inquiries.json', '/admin_server.py'):
            return self._json(403, {'error': 'forbidden'})
        return super().do_GET()

    def do_POST(self):
        p = urlparse(self.path).path
        try:
            data = self._body()
        except Exception as e:
            return self._json(400, {'error': str(e)})

        if p == '/api/login':
            cfg = load_config()
            ok = hmac.compare_digest(_hash(str(data.get('password', '')), cfg['salt']), cfg['hash'])
            if not ok:
                time.sleep(0.8)
                return self._json(401, {'error': 'wrong password'})
            tok = secrets.token_urlsafe(32)
            with LOCK:
                TOKENS[tok] = time.time() + 12 * 3600
            return self._json(200, {'token': tok})

        if p == '/api/inquiry':
            fields = {k: str(data.get(k, '')).strip()[:2000] for k in ('company', 'name', 'region', 'phone', 'email', 'message')}
            items = data.get('items') or []
            fields['items'] = [str(i)[:100] for i in items][:20] if isinstance(items, list) else []
            fields['lang'] = str(data.get('lang', 'ko'))[:5]
            if not fields['company'] or not fields['name'] or not fields['email']:
                return self._json(400, {'error': 'company, name and email are required'})
            with LOCK:
                lst = load_json(INQUIRIES, [])
                rec = {'id': secrets.token_hex(6), 'at': time.strftime('%Y-%m-%d %H:%M:%S'), 'read': False, **fields}
                lst.append(rec)
                save_json(INQUIRIES, lst)
            return self._json(200, {'ok': True, 'id': rec['id']})

        if not self._auth():
            return self._json(401, {'error': 'unauthorized'})

        if p == '/api/logout':
            with LOCK:
                TOKENS.pop(self.headers.get('X-Auth-Token', ''), None)
            return self._json(200, {'ok': True})

        if p == '/api/content':
            clean = {}
            for group in ('text', 'plain', 'img', 'href', 'src'):
                g = data.get(group) or {}
                if isinstance(g, dict):
                    clean[group] = g
            with LOCK:
                save_json(CONTENT, clean)
            return self._json(200, {'ok': True})

        if p == '/api/upload':
            name = re.sub(r'[^A-Za-z0-9._-]+', '_', str(data.get('name', 'image')))
            ext = os.path.splitext(name)[1].lower()
            if ext not in ('.webp', '.png', '.jpg', '.jpeg', '.gif', '.svg'):
                return self._json(400, {'error': 'unsupported file type'})
            try:
                blob = base64.b64decode(str(data.get('data', '')).split(',')[-1])
            except Exception:
                return self._json(400, {'error': 'bad data'})
            if len(blob) > 15 * 1024 * 1024:
                return self._json(400, {'error': 'file too large'})
            os.makedirs(ASSETS, exist_ok=True)
            base, ext = os.path.splitext(name)
            target = os.path.join(ASSETS, name)
            n = 1
            while os.path.exists(target):
                target = os.path.join(ASSETS, f'{base}_{n}{ext}')
                n += 1
            with open(target, 'wb') as f:
                f.write(blob)
            return self._json(200, {'ok': True, 'path': 'assets/' + os.path.basename(target)})

        if p == '/api/inquiries/update':
            with LOCK:
                lst = load_json(INQUIRIES, [])
                if data.get('delete'):
                    lst = [r for r in lst if r.get('id') != data.get('id')]
                else:
                    for r in lst:
                        if r.get('id') == data.get('id'):
                            r['read'] = bool(data.get('read', True))
                save_json(INQUIRIES, lst)
            return self._json(200, {'ok': True})

        if p == '/api/password':
            cfg = load_config()
            if not hmac.compare_digest(_hash(str(data.get('current', '')), cfg['salt']), cfg['hash']):
                return self._json(401, {'error': 'current password is wrong'})
            new = str(data.get('new', ''))
            if len(new) < 6:
                return self._json(400, {'error': 'password must be at least 6 characters'})
            salt = secrets.token_hex(16)
            save_json(CONFIG, {'salt': salt, 'hash': _hash(new, salt)})
            return self._json(200, {'ok': True})

        return self._json(404, {'error': 'not found'})


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
    load_config()
    if not os.path.exists(CONTENT):
        save_json(CONTENT, {})
    if not os.path.exists(INQUIRIES):
        save_json(INQUIRIES, [])
    srv = ThreadingHTTPServer(('0.0.0.0', port), Handler)
    print(f'[admin] site:  http://localhost:{port}/index.html')
    print(f'[admin] admin: http://localhost:{port}/admin.html')
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()
