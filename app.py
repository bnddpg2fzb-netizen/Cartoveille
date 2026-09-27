"""CartoVeille V2 — local-first API. Public RSS only; no LinkedIn scraping."""
from __future__ import annotations
import hashlib
import secrets
import threading
import time
from datetime import timedelta
import json
import os
import re
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import Response
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

BASE = Path(__file__).resolve().parent
DB = Path(os.getenv('CARTOVEILLE_DB', str(BASE / 'cartoveille.sqlite3')))
DB.parent.mkdir(parents=True, exist_ok=True)
app = FastAPI(title='CartoVeille API', version='2.1-cloud')

# All routes, including API docs and exports, require HTTP Basic credentials in cloud mode.
# HTTPS is supplied by the hosting platform; never publish the app over plain HTTP.
@app.middleware('http')
async def basic_auth(request: Request, call_next):
    username = os.getenv('CARTOVEILLE_USER', '')
    password = os.getenv('CARTOVEILLE_PASSWORD', '')
    if not username or not password:
        return Response('Configuration manquante: identifiants serveur requis.', status_code=503)
    header = request.headers.get('authorization', '')
    import base64
    try:
        scheme, token = header.split(' ', 1)
        decoded = base64.b64decode(token, validate=True).decode('utf-8')
        provided_user, provided_password = decoded.split(':', 1)
    except (ValueError, UnicodeDecodeError, Exception):
        provided_user, provided_password, scheme = '', '', ''
    if scheme.lower() != 'basic' or not (secrets.compare_digest(provided_user, username) and secrets.compare_digest(provided_password, password)):
        return Response('Authentification requise', status_code=401, headers={'WWW-Authenticate': 'Basic realm="CartoVeille"', 'Cache-Control':'no-store'})
    response = await call_next(request)
    response.headers['Cache-Control'] = 'no-store'
    return response


@contextmanager
def conn():
    db = sqlite3.connect(DB)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA foreign_keys=ON')
    try:
        yield db
        db.commit()
    finally:
        db.close()

def init_db():
    with conn() as db:
        db.executescript('''
        CREATE TABLE IF NOT EXISTS companies (
            id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE, sector TEXT NOT NULL DEFAULT 'cartonnage',
            city TEXT NOT NULL DEFAULT '', department TEXT NOT NULL DEFAULT '', region TEXT NOT NULL DEFAULT '',
            latitude REAL, longitude REAL, website TEXT NOT NULL DEFAULT '', notes TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY, company_id INTEGER REFERENCES companies(id) ON DELETE SET NULL,
            title TEXT NOT NULL, summary TEXT NOT NULL DEFAULT '', category TEXT NOT NULL DEFAULT 'actualité',
            source TEXT NOT NULL, url TEXT NOT NULL UNIQUE, published_at TEXT,
            collected_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, status TEXT NOT NULL DEFAULT 'à qualifier'
        );
        CREATE TABLE IF NOT EXISTS prices (
            id INTEGER PRIMARY KEY, company_id INTEGER REFERENCES companies(id) ON DELETE SET NULL,
            competitor TEXT NOT NULL, product TEXT NOT NULL, market TEXT NOT NULL DEFAULT '',
            quantity INTEGER NOT NULL CHECK(quantity>0), unit_price REAL NOT NULL CHECK(unit_price>0),
            unit TEXT NOT NULL DEFAULT 'EUR/pièce', city TEXT NOT NULL DEFAULT '',
            source TEXT NOT NULL DEFAULT '', observed_at TEXT NOT NULL,
            confidence TEXT NOT NULL DEFAULT 'déclaré', notes TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS ix_events_company ON events(company_id);
        CREATE INDEX IF NOT EXISTS ix_prices_product ON prices(product, market);
        ''')
init_db()

class CompanyIn(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    sector: str = 'cartonnage'
    city: str = ''
    department: str = ''
    region: str = ''
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    website: str = ''
    notes: str = ''

class EventIn(BaseModel):
    company_id: int | None = None
    title: str = Field(min_length=3)
    summary: str = ''
    category: str = 'actualité'
    source: str = Field(min_length=2)
    url: str
    published_at: str | None = None
    status: str = 'à qualifier'

class PriceIn(BaseModel):
    company_id: int | None = None
    competitor: str = Field(min_length=2)
    product: str = Field(min_length=2)
    market: str = ''
    quantity: int = Field(gt=0)
    unit_price: float = Field(gt=0)
    unit: str = 'EUR/pièce'
    city: str = ''
    source: str = ''
    observed_at: str = Field(min_length=8)
    confidence: str = 'déclaré'
    notes: str = ''

class EstimateIn(BaseModel):
    product: str
    market: str = ''
    quantity: int = Field(gt=0)
    city: str = ''
    competitor: str = ''

def rows(db, sql, params=()):
    return [dict(r) for r in db.execute(sql, params).fetchall()]

def validate_http_url(value):
    p = urlparse(value)
    if p.scheme not in ('http', 'https') or not p.netloc:
        raise HTTPException(422, 'URL HTTP(S) valide requise')

app.mount('/static', StaticFiles(directory=BASE / 'static'), name='static')

@app.get('/manifest.webmanifest')
def pwa_manifest():
    return FileResponse(BASE / 'static' / 'manifest.webmanifest', media_type='application/manifest+json')

@app.get('/service-worker.js')
def pwa_worker():
    return FileResponse(BASE / 'static' / 'service-worker.js', media_type='application/javascript', headers={'Service-Worker-Allowed': '/'})

@app.get('/')
def home():
    return FileResponse(BASE / 'static' / 'index.html')

@app.get('/api/health')
def health():
    return {'status': 'ok', 'database': 'sqlite', 'collection': 'manual + daily RSS scheduler if enabled'}

@app.get('/api/dashboard')
def dashboard():
    with conn() as db:
        return {table: db.execute(f'SELECT count(*) FROM {table}').fetchone()[0] for table in ('companies', 'events', 'prices')}

@app.get('/api/companies')
def list_companies(q: str = ''):
    with conn() as db:
        return rows(db, 'SELECT * FROM companies WHERE name LIKE ? OR city LIKE ? ORDER BY name', (f'%{q}%', f'%{q}%'))

@app.post('/api/companies', status_code=201)
def add_company(item: CompanyIn):
    with conn() as db:
        try:
            cur = db.execute('INSERT INTO companies(name,sector,city,department,region,latitude,longitude,website,notes) VALUES (?,?,?,?,?,?,?,?,?)', tuple(item.model_dump().values()))
        except sqlite3.IntegrityError:
            raise HTTPException(409, 'Entreprise déjà enregistrée')
        return {'id': cur.lastrowid}

@app.get('/api/companies/{company_id}')
def company_detail(company_id: int):
    with conn() as db:
        c = db.execute('SELECT * FROM companies WHERE id=?', (company_id,)).fetchone()
        if not c:
            raise HTTPException(404, 'Entreprise introuvable')
        return {'company': dict(c), 'events': rows(db, 'SELECT * FROM events WHERE company_id=? ORDER BY published_at DESC', (company_id,)), 'prices': rows(db, 'SELECT * FROM prices WHERE company_id=? ORDER BY observed_at DESC', (company_id,))}

@app.get('/api/events')
def list_events(q: str = '', category: str = ''):
    with conn() as db:
        return rows(db, '''SELECT e.*, c.name company_name FROM events e LEFT JOIN companies c ON c.id=e.company_id
        WHERE (e.title LIKE ? OR e.summary LIKE ?) AND e.category LIKE ? ORDER BY COALESCE(e.published_at,e.collected_at) DESC LIMIT 500''', (f'%{q}%', f'%{q}%', f'%{category}%'))

@app.post('/api/events', status_code=201)
def add_event(item: EventIn):
    validate_http_url(item.url)
    with conn() as db:
        try:
            cur = db.execute('INSERT INTO events(company_id,title,summary,category,source,url,published_at,status) VALUES (?,?,?,?,?,?,?,?)', tuple(item.model_dump().values()))
        except sqlite3.IntegrityError:
            raise HTTPException(409, 'Source déjà enregistrée ou entreprise inconnue')
        return {'id': cur.lastrowid}

@app.get('/api/prices')
def list_prices():
    with conn() as db:
        return rows(db, 'SELECT * FROM prices ORDER BY observed_at DESC')

@app.post('/api/prices', status_code=201)
def add_price(item: PriceIn):
    with conn() as db:
        try:
            cur = db.execute('''INSERT INTO prices(company_id,competitor,product,market,quantity,unit_price,unit,city,source,observed_at,confidence,notes)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)''', tuple(item.model_dump().values()))
        except sqlite3.IntegrityError:
            raise HTTPException(422, 'Entreprise inconnue')
        return {'id': cur.lastrowid}

@app.post('/api/prices/estimate')
def estimate(item: EstimateIn):
    """Transparent comparables only, not a machine-learning prediction."""
    with conn() as db:
        candidates = rows(db, 'SELECT * FROM prices WHERE lower(product)=lower(?) AND unit=?', (item.product.strip(), 'EUR/pièce'))
    if not candidates:
        return {'status': 'insufficient_data', 'message': 'Aucun comparable exact disponible. Ajouter des prix documentés.', 'comparables': []}
    scored = []
    for p in candidates:
        weight = 1.0
        if item.market and p['market'].casefold() == item.market.casefold(): weight *= 1.5
        if item.city and p['city'].casefold() == item.city.casefold(): weight *= 1.3
        if item.competitor and p['competitor'].casefold() == item.competitor.casefold(): weight *= 1.1
        ratio = max(p['quantity'], item.quantity) / min(p['quantity'], item.quantity)
        weight /= ratio ** 0.5
        if p['confidence'] == 'confirmé': weight *= 1.2
        scored.append((p, weight))
    weighted = sum(p['unit_price'] * w for p,w in scored) / sum(w for _,w in scored)
    return {'status': 'indicative', 'estimated_unit_price': round(weighted, 4), 'currency': 'EUR',
            'sample_size': len(scored), 'observed_min': min(p['unit_price'] for p,_ in scored),
            'observed_max': max(p['unit_price'] for p,_ in scored),
            'method': 'Moyenne pondérée de prix documentés pour produit identique ; pondération marché, ville, quantité et fiabilité. Hors coût matière, transport, marge et spécifications techniques.',
            'comparables': [p for p,_ in scored]}

RSS_FEEDS = [
    ('Google Actualités — cartonnage', 'https://news.google.com/rss/search?q=cartonnage+entreprise+France&hl=fr&gl=FR&ceid=FR:fr'),
    ('Google Actualités — carton ondulé', 'https://news.google.com/rss/search?q=%22carton+ondul%C3%A9%22+usine+France&hl=fr&gl=FR&ceid=FR:fr'),
    ('Google Actualités — emballage carton', 'https://news.google.com/rss/search?q=%22emballage+carton%22+investissement+France&hl=fr&gl=FR&ceid=FR:fr'),
]

@app.post('/api/collect/rss')
def collect_rss():
    import feedparser
    imported, skipped, errors = 0, 0, []
    with conn() as db:
        companies = rows(db, 'SELECT id,name FROM companies')
        for label, url in RSS_FEEDS:
            try:
                feed = feedparser.parse(url)
                if feed.bozo and not feed.entries:
                    raise ValueError(str(feed.bozo_exception))
                for entry in feed.entries[:50]:
                    link = entry.get('link','')
                    if not link.startswith(('https://','http://')):
                        skipped += 1; continue
                    title = re.sub(r'<[^>]*>', '', entry.get('title','')).strip()
                    if not title:
                        skipped += 1; continue
                    match = next((c['id'] for c in companies if c['name'].casefold() in title.casefold()), None)
                    pub = entry.get('published','') or None
                    summary = re.sub(r'<[^>]*>', '', entry.get('summary',''))[:1200]
                    cur = db.execute('''INSERT OR IGNORE INTO events(company_id,title,summary,category,source,url,published_at)
                       VALUES (?,?,?,?,?,?,?)''', (match,title,summary,'veille RSS',label,link,pub))
                    if cur.rowcount: imported += 1
                    else: skipped += 1
            except Exception as exc:
                errors.append({'feed': label, 'error': str(exc)[:200]})
    return {'imported': imported, 'skipped': skipped, 'errors': errors, 'note': 'Collecte déclenchée manuellement. Vérifier les articles avant exploitation.'}

@app.get('/api/export')
def export_json():
    with conn() as db:
        return {t: rows(db, f'SELECT * FROM {t}') for t in ('companies','events','prices')}


# One-instance scheduler: enable only for a single worker / single service instance.
# RSS errors are logged; the server remains available when a feed fails.
def daily_collector():
    while True:
        now = datetime.now(timezone.utc)
        target = now.replace(hour=6, minute=0, second=0, microsecond=0)
        if target <= now:
            target += timedelta(days=1)
        time.sleep((target - now).total_seconds())
        try:
            result = collect_rss()
            print('Collecte quotidienne CartoVeille:', result, flush=True)
        except Exception as exc:
            print('Erreur collecte quotidienne:', repr(exc), flush=True)

if os.getenv('CARTOVEILLE_DAILY_RSS', '0') == '1':
    threading.Thread(target=daily_collector, daemon=True, name='cartoveille-daily-rss').start()
