#!/usr/bin/env python3
"""Daily refresh for the Markets page: quotes + IPO calendar -> data.json"""
import json, re, os, sys, time, datetime, urllib.request
from bs4 import BeautifulSoup
UA = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36'}
WATCH = ['AAPL','MSFT','NVDA','AMZN','GOOGL','META','TSLA','JPM','GS','MS','SPY','QQQ']
def fetch(url):
    req = urllib.request.Request(url, headers=UA)
    return urllib.request.urlopen(req, timeout=30).read().decode('utf-8','ignore')
def num(x):
    x = x.replace(',','').replace('−','-').replace('$','').replace('%','').strip()
    try: return float(x)
    except: return None
def yahoo_hist(sym, days=30):
    """Best-effort 1mo close history from Yahoo; returns {date: close} or {}."""
    try:
        js = json.loads(fetch(f'https://query1.finance.yahoo.com/v8/finance/chart/{sym}?range=1mo&interval=1d'))
        r = js['chart']['result'][0]
        ts = r['timestamp']
        closes = r['indicators']['quote'][0]['close']
        out = {}
        for t, c in zip(ts, closes):
            if c is None: continue
            out[datetime.datetime.utcfromtimestamp(t).date().isoformat()] = c
        return out
    except Exception:
        return {}
def quote(sym):
    for kind in ('stocks','etf'):
        try:
            html = fetch(f'https://stockanalysis.com/{kind}/{sym.lower()}/')
        except Exception:
            continue
        soup = BeautifulSoup(html, 'html.parser')
        t = soup.get_text(' | ', strip=True)
        i = t.find(chr(183)+' USD')
        if i < 0: continue
        seg = t[i:i+400]
        m = re.search(r'([\d,]+\.\d{2})', seg)
        if not m: continue
        price = num(m.group(1))
        pct = None; chg = None
        after = seg[m.end():]
        pm = re.search(r'([-\u2212+]?[\d.,]+)\s*\(([-\u2212+]?[\d.]+)%\)', after)
        if pm:
            chg = num(pm.group(1)); pct = num(pm.group(2))
            if '\u2212' in pm.group(1): chg = -abs(chg)
            if '\u2212' in pm.group(2): pct = -abs(pct)
        else:
            pm = re.search(r'([-\u2212+])([\d.,]+)\s*\(|([-\u2212+])([\d.]+)%', after)
            if pm:
                if pm.group(2):
                    chg = num(pm.group(2)) * (-1 if '\u2212' in pm.group(1) else 1)
                if pm.group(4):
                    pct = num(pm.group(4)) * (-1 if '\u2212' in pm.group(3) else 1)
        nm = re.search(r"([A-Za-z0-9 .,&\'-]+?) \(" + re.escape(sym) + r'\)', t[:i+400])
        name = nm.group(1).strip() if nm else sym
        vol = rng = mc = None
        vm = re.search(r'Volume \| ([\d,]+)', t)
        if vm: vol = vm.group(1)
        rm = re.search(r"Day's Range \| ([\d.,]+) - ([\d.,]+)", t)
        if rm: rng = rm.group(1) + ' - ' + rm.group(2)
        mm = re.search(r'Market Cap \| ([\d.]+[MBT])', t)
        if mm: mc = mm.group(1)
        return {'name': name, 'price': price, 'chg': chg, 'chgPct': pct, 'vol': vol, 'range': rng, 'mcap': mc}
    return None
def ipos():
    out = {'upcoming': [], 'priced': []}
    soup = BeautifulSoup(fetch('https://stockanalysis.com/ipos/'), 'html.parser')
    for h in soup.find_all(['h2','h3']):
        if 'Last 200 IPOs' not in h.get_text(strip=True): continue
        tbl = h.find_next('table')
        if not tbl: break
        rows = []
        for tr in tbl.find_all('tr')[1:16]:
            cells = [td.get_text(' ', strip=True) for td in tr.find_all(['td','th'])]
            if cells and len(cells) >= 6: rows.append(cells)
        out['priced'] = rows
        break
    soup = BeautifulSoup(fetch('https://stockanalysis.com/ipos/calendar/'), 'html.parser')
    for h in soup.find_all(['h2','h3']):
        title = h.get_text(' ', strip=True)
        if 'IPO' not in title: continue
        tbl = h.find_next('table')
        if not tbl: continue
        for tr in tbl.find_all('tr')[1:]:
            cells = [td.get_text(' ', strip=True) for td in tr.find_all(['td','th'])]
            if cells and len(cells) >= 3 and cells[0] != 'IPO Date':
                out['upcoming'].append([title.split(chr(183))[0].strip()] + cells[:6])
    return out
def main():
    dpath = 'data.json'
    data = {}
    if os.path.exists(dpath):
        try: data = json.load(open(dpath))
        except Exception: data = {}
    today = datetime.date.today().isoformat()
    quotes = data.get('quotes', {})
    for sym in WATCH:
        try:
            q = quote(sym)
        except Exception:
            q = None
        if q and q.get('price'):
            old = quotes.get(sym, {})
            hist = old.get('hist', {})
            if len(hist) < 5:
                for k, v in yahoo_hist(sym).items():
                    hist.setdefault(k, v)
            hist[today] = q['price']
            q['hist'] = dict(sorted(hist.items())[-30:])
            quotes[sym] = q
            print(sym, q['price'], q['chgPct'])
        else:
            print(sym, 'FAILED', file=sys.stderr)
        time.sleep(0.4)
    try:
        ip = ipos()
        print('upcoming rows:', len(ip['upcoming']), 'priced rows:', len(ip['priced']))
    except Exception as e:
        ip = data.get('ipos', {'upcoming': [], 'priced': []})
        print('ipos FAILED', e, file=sys.stderr)
    data.update({'updated': datetime.datetime.now().isoformat(timespec='seconds'), 'quotes': quotes, 'ipos': ip})
    json.dump(data, open(dpath, 'w'), indent=1)
    print('wrote data.json,', len(quotes), 'quotes')
main()
