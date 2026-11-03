"""Vercel Python API. Shared event storage uses Supabase; no third-party packages."""
import base64
import csv
import hashlib
import hmac
import io
import json
import os
import secrets
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from zoneinfo import ZoneInfo

SUPABASE = os.environ.get('SUPABASE_URL', '').rstrip('/')
KEY = os.environ.get('SUPABASE_SERVICE_ROLE_KEY', '')
EVENT_CODE = os.environ.get('EVENT_ACCESS_CODE', '')
SESSION_SECRET = os.environ.get('SESSION_SECRET', '')
LIVE = all([SUPABASE, KEY, EVENT_CODE, SESSION_SECRET])
DATES = {'2027-01-11', '2027-01-12', '2027-01-13'}
CONTENT = Path(__file__).resolve().parent.parent / 'backend' / 'content.json'


def remote(path, method='GET', data=None, raw=False):
    headers = {'apikey': KEY, 'Authorization': 'Bearer ' + KEY}
    if data is not None:
        headers['Content-Type'] = 'image/jpeg' if raw else 'application/json'
    req = urllib.request.Request(SUPABASE + path, data=data if raw else json.dumps(data).encode() if data is not None else None, method=method, headers=headers)
    with urllib.request.urlopen(req, timeout=12) as res:
        value = res.read()
        return json.loads(value) if value else None


def totals():
    return remote('/rest/v1/rpc/drink_totals', 'POST', {})


class handler(BaseHTTPRequestHandler):
    def respond(self, code, body, cookie=None):
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        if cookie:
            self.send_header('Set-Cookie', cookie)
        self.end_headers()
        self.wfile.write(json.dumps(body).encode())

    def session(self):
        try:
            cookies = SimpleCookie(self.headers.get('Cookie', ''))
            token = cookies['gp27_session'].value
            sid, expiry, signature = token.split('.')
            expected = hmac.new(SESSION_SECRET.encode(), (sid + '.' + expiry).encode(), hashlib.sha256).hexdigest()
            if int(expiry) > time.time() and hmac.compare_digest(signature, expected):
                return sid
        except (KeyError, ValueError):
            pass
        return None

    def do_GET(self):
        self.dispatch(False)

    def do_POST(self):
        self.dispatch(True)

    def dispatch(self, posting):
        try:
            q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            action = q.get('action', [''])[0]
            sid = self.session() if LIVE else None
            data = {}
            if posting:
                # Reject cross-origin form and fetch mutations. Same-origin browsers send Origin.
                origin = urllib.parse.urlparse(self.headers.get('Origin', ''))
                if origin.netloc and origin.netloc != self.headers.get('Host'):
                    return self.respond(403, {'error': 'This request is not allowed.'})
                if not self.headers.get('Content-Type', '').startswith('application/json'):
                    return self.respond(415, {'error': 'JSON is required.'})
                size = int(self.headers.get('Content-Length', '0'))
                if size > 3_500_000:
                    return self.respond(413, {'error': 'Please choose a smaller photo.'})
                data = json.loads(self.rfile.read(size) or '{}')
                if not isinstance(data, dict):
                    raise ValueError('Invalid request')
            if action == 'status' and not posting:
                return self.respond(200, {'mode': 'live' if LIVE else 'demo', 'authenticated': bool(sid)})
            if action == 'agenda' and not posting:
                return self.agenda()
            if not LIVE:
                return self.respond(503, {'error': 'Shared summit features are not connected yet.'})
            if action == 'login' and posting:
                return self.login(data)
            if not sid:
                return self.respond(401, {'error': 'Please enter your summit event code.'})
            if action == 'shared' and not posting:
                rows = remote('/rest/v1/photos?select=id,name,path,owner_id,created_at&order=created_at.desc&limit=100')
                paths = [row['path'] for row in rows]
                signed = remote('/storage/v1/object/sign/summit-photos', 'POST', {'expiresIn': 3600, 'paths': paths}) if paths else []
                links = {x['path']: SUPABASE + '/storage/v1' + x['signedURL'] for x in signed if x.get('signedURL')}
                photos = [{'id': r['id'], 'name': r['name'], 'url': links[r['path']], 'mine': hmac.compare_digest(r['owner_id'], sid)} for r in rows if r['path'] in links]
                content = json.loads(CONTENT.read_text())
                videos = []
                for video in content.get('videos', []):
                    release = video.get('release_at')
                    released = bool(release and video.get('url') and datetime.fromisoformat(release.replace('Z', '+00:00')) <= datetime.now(timezone.utc))
                    videos.append({'team_id': video['team_id'], 'title': video['title'], 'released': released, **({'url': video['url']} if released else {})})
                return self.respond(200, {'photos': photos, 'videos': videos, 'totals': totals()})
            if action == 'drink' and posting:
                kind = data.get('type')
                if kind not in ('coffee', 'beer', 'wine'):
                    raise ValueError('Choose coffee, beer or wine.')
                now = datetime.now(ZoneInfo('Europe/Berlin'))
                if now.date().isoformat() not in DATES:
                    return self.respond(409, {'error': 'The live contest runs 11–13 January 2027.'})
                result = remote('/rest/v1/rpc/log_drink', 'POST', {'p_owner': sid, 'p_kind': kind})
                if not result.get('id'):
                    return self.respond(429, {'error': 'Already logged. Please wait 30 seconds before logging another drink.'})
                return self.respond(200, {'id': result['id'], 'totals': totals()})
            if action == 'undo' and posting:
                drink_id = str(data.get('id', ''))
                remote('/rest/v1/drinks?id=eq.' + urllib.parse.quote(drink_id, safe='') + '&owner_id=eq.' + sid, 'DELETE')
                return self.respond(200, {'totals': totals()})
            if action == 'upload' and posting:
                raw = base64.b64decode(data.get('image', ''), validate=True)
                name = str(data.get('name', '')).strip()[:70]
                if not name or not raw.startswith(b'\xff\xd8\xff') or len(raw) > 2_500_000:
                    raise ValueError('Please upload a JPEG photo under 2.5 MB and add your name.')
                # A central database lock enforces a per-session upload rate limit.
                allowed = remote('/rest/v1/rpc/claim_upload', 'POST', {'p_owner': sid})
                if not allowed:
                    return self.respond(429, {'error': 'Please wait 10 seconds before sharing another photo.'})
                path = secrets.token_hex(16) + '.jpg'
                remote('/storage/v1/object/summit-photos/' + path, 'POST', raw, raw=True)
                try:
                    remote('/rest/v1/photos', 'POST', {'id': path[:-4], 'owner_id': sid, 'name': name, 'path': path})
                except Exception:
                    remote('/storage/v1/object/summit-photos', 'DELETE', {'prefixes': [path]})
                    raise
                return self.respond(201, {'ok': True})
            if action == 'delete-photo' and posting:
                photo_id = urllib.parse.quote(str(data.get('id', '')), safe='')
                rows = remote('/rest/v1/photos?id=eq.' + photo_id + '&owner_id=eq.' + sid + '&select=path')
                if not rows:
                    return self.respond(404, {'error': 'This photo was not found in your uploads.'})
                remote('/storage/v1/object/summit-photos', 'DELETE', {'prefixes': [rows[0]['path']]})
                remote('/rest/v1/photos?id=eq.' + photo_id + '&owner_id=eq.' + sid, 'DELETE')
                return self.respond(200, {'ok': True})
            return self.respond(404, {'error': 'Unknown summit request.'})
        except (ValueError, TypeError, KeyError):
            self.respond(400, {'error': 'Please check your input and try again.'})
        except Exception:
            # Never expose upstream URLs, credentials or server exception messages.
            self.respond(502, {'error': 'The summit service could not be reached. Please try again shortly.'})

    def login(self, data):
        # Hash IPs before storing central login throttles. No plaintext addresses are stored.
        ip = self.headers.get('x-forwarded-for', self.client_address[0]).split(',')[0].strip()
        owner = hmac.new(SESSION_SECRET.encode(), ('login:' + ip).encode(), hashlib.sha256).hexdigest()
        allowed = remote('/rest/v1/rpc/allow_login', 'POST', {'p_owner': owner})
        if not allowed:
            return self.respond(429, {'error': 'Too many attempts. Please try again in 15 minutes.'})
        if not hmac.compare_digest(str(data.get('code', '')), EVENT_CODE):
            return self.respond(401, {'error': 'That event code does not match. Please try again.'})
        sid = secrets.token_hex(24)
        exp = str(int(time.time()) + 60 * 60 * 24 * 30)
        msg = sid + '.' + exp
        token = msg + '.' + hmac.new(SESSION_SECRET.encode(), msg.encode(), hashlib.sha256).hexdigest()
        cookie = 'gp27_session=' + token + '; Path=/; HttpOnly; SameSite=Lax; Max-Age=2592000'
        if self.headers.get('Host', '').split(':')[0] not in ('localhost', '127.0.0.1'):
            cookie += '; Secure'
        return self.respond(200, {'ok': True}, cookie)

    def agenda(self):
        url = os.environ.get('GOOGLE_SHEET_CSV_URL', '')
        if not url:
            return self.respond(200, {'connected': False, 'rows': []})
        # The URL is a trusted server setting, not a visitor-supplied fetch target.
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme != 'https' or parsed.hostname != 'docs.google.com':
            return self.respond(200, {'connected': False, 'rows': [], 'error': 'The programme source needs to be checked by the organisers.'})
        try:
            with urllib.request.urlopen(url, timeout=10) as r:
                text = r.read(1_000_001)
            if len(text) > 1_000_000:
                raise ValueError('Sheet too large')
            reader = csv.DictReader(io.StringIO(text.decode('utf-8-sig')))
            required = {'date', 'time', 'title', 'location', 'type', 'speaker'}
            if not required.issubset(set(reader.fieldnames or [])):
                raise ValueError('Sheet columns invalid')
            rows = []
            for row in reader:
                if not row.get('title', '').strip():
                    continue
                datetime.strptime(row['time'].strip(), '%H:%M')
                if row['date'].strip() not in DATES:
                    raise ValueError('Invalid summit date')
                rows.append({k: str(row.get(k, '') or '').strip()[:500] for k in required})
            return self.respond(200, {'connected': True, 'rows': sorted(rows, key=lambda x: (x['date'], x['time']))})
        except Exception:
            return self.respond(200, {'connected': False, 'rows': [], 'error': 'The confirmed programme could not be loaded. The illustrative programme is shown below.'})
