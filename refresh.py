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
    """Best-effort 1-month close history for sparklines; returns {date: close} or {}."""
    for base in ('https://stockanalysis.com/api/symbol/s/','https://stockanalysis.com/api/symbol/e/'):
        try:
            js = json.loads(fetch(base + sym + '/history?range=1M&period=Daily'))
            if js.get('status') != 200: continue
            out = {}
            for row in js.get('data', []):
                if row.get('c') is None: continue
                out[row['t']] = row['c']
            if out: return out
        except Exception:
            continue
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
def money(v):
    if v >= 1e9: return '$%.1fB' % (v/1e9)
    if v >= 1e6: return '$%.0fM' % (v/1e6)
    return '$%.0fK' % (v/1e3)

def clean_deal(x):
    x = (x or '').strip().replace('$','').replace(',','')
    if not x or x in ('-','\u2014'): return None
    v = num(x)
    if v: return money(v)
    return '$' + x

def deal_size(sym, deals, offer=None):
    d = deals.get(sym) or {}
    ds = clean_deal(d.get('deal'))
    if ds: return ds
    sh = num((d.get('shares') or '').replace(',',''))
    off = num(offer) if offer else None
    if sh and off: return money(sh*off)
    return '\u2014'

def raise_est(d):
    sh = num((d.get('shares') or '').replace(',',''))
    m = re.match(r'\$?([\d.]+)\s*-\s*\$?([\d.]+)', (d.get('rng') or ''))
    if m and sh: return money(sh*(float(m.group(1))+float(m.group(2)))/2)
    off = num((d.get('offer') or '').replace('$','')) if d.get('offer') else None
    if off and sh: return money(sh*off)
    return None


def page_mcap(sym):
    for kind in ('stocks','etf'):
        try:
            html = fetch(f'https://stockanalysis.com/{kind}/{sym.lower()}/')
        except Exception:
            continue
        soup = BeautifulSoup(html, 'html.parser')
        t = soup.get_text(' | ', strip=True)
        m = re.search(r'Market Cap \| ([\d.]+[MBT])', t)
        if m: return m.group(1)
    return None

def sold_for(sym, deals, offer, latest):
    d = deals.get(sym) or {}
    mc = clean_deal(d.get('mcap'))
    if mc and mc != '\u2014': return mc
    pv = page_mcap(sym)
    off = num(offer) if offer else None
    cur = num(latest) if latest else None
    pm = re.match(r'([\d.]+)([MBT]?)$', pv or '')
    if pm and off and cur:
        mult = {'B':1e9,'M':1e6,'T':1e12}.get(pm.group(2), 1e6)
        v = (float(pm.group(1))*mult/cur) * off
        return money(v)
    return '\u2014'

def ipos():
    out = {'upcoming': [], 'priced': [], 'deals': {}}
    deals = {}
    offers = {}
    soup = BeautifulSoup(fetch('https://stockanalysis.com/ipos/'), 'html.parser')
    for h in soup.find_all(['h2','h3']):
        if 'Last 200 IPOs' not in h.get_text(strip=True): continue
        tbl = h.find_next('table')
        if not tbl: break
        priced_rows = []
        for tr in tbl.find_all('tr')[1:16]:
            cells = [td.get_text(' ', strip=True) for td in tr.find_all(['td','th'])]
            if cells and len(cells) >= 6:
                deals.setdefault(cells[1], {})
                deals[cells[1]]['offer'] = cells[3]
                offers[cells[1]] = cells[3]
                priced_rows.append(cells[:6])
        out['priced'] = priced_rows
        break
    soup = BeautifulSoup(fetch('https://stockanalysis.com/ipos/calendar/'), 'html.parser')
    for h in soup.find_all(['h2','h3']):
        title = h.get_text(' ', strip=True)
        if 'IPO' not in title: continue
        tbl = h.find_next('table')
        if not tbl: continue
        mc_i = None
        hdr = tbl.find('tr')
        if hdr:
            hcells = [c.get_text(' ', strip=True).lower() for c in hdr.find_all(['td','th'])]
            for i,hc in enumerate(hcells):
                if 'market cap' in hc: mc_i = i
        for tr in tbl.find_all('tr')[1:]:
            cells = [td.get_text(' ', strip=True) for td in tr.find_all(['td','th'])]
            if cells and len(cells) >= 7 and cells[0] != 'IPO Date':
                d = deals.setdefault(cells[1], {})
                d.update({'rng': cells[4], 'shares': cells[5], 'deal': cells[6], 'offer': offers.get(cells[1])})
                if mc_i is not None and mc_i < len(cells):
                    mc = clean_deal(cells[mc_i])
                    if mc and mc != '\u2014': d['mcap'] = mc
                rv = clean_deal(cells[6]) or raise_est(d) or '\u2014'
                out['upcoming'].append([title.split(chr(183))[0].strip()] + cells[:6] + [rv])
    out['deals'] = deals
    out['priced'] = [r + [deal_size(r[1], deals, r[3]), sold_for(r[1], deals, r[3], r[4])] for r in out['priced']]
    return out


def treasury(csv_type, year=2026):
    url = ('https://home.treasury.gov/resource-center/data-chart-center/interest-rates/'
           'daily-treasury-rates.csv/%d/all?type=daily_treasury_%s&field_tdr_date_value=%d&page&_format=csv'
           % (year, csv_type, year))
    txt = fetch(url)
    rows = [r.split(',') for r in txt.strip().splitlines()]
    hdr = {h.strip().strip('"').replace(' YR', ' Yr'): i for i, h in enumerate(rows[0])}
    return hdr, rows[1:]

def fdic():
    """FDIC national average deposit rates (monthly page), savings + 12-month CD."""
    soup = BeautifulSoup(fetch('https://www.fdic.gov/national-rates-and-rate-caps'), 'html.parser')
    out = {}
    for tr in soup.find_all('tr'):
        cells = [td.get_text(' ', strip=True) for td in tr.find_all('td')]
        if len(cells) >= 2 and cells[0] in ('Savings', '12 month CD', '6 month CD'):
            v = num(cells[1])
            if v is not None:
                key = {'Savings': 'savings', '12 month CD': 'cd12m', '6 month CD': 'cd6m'}[cells[0]]
                out[key] = v
    t = soup.title.get_text(' ', strip=True) if soup.title else ''
    m = re.search(r'Rate Caps\s*[\u2013\u2014-]\s*([A-Z][a-z]+ 20\d\d)', t)
    if m: out['fdic_asof'] = m.group(1)
    return out

def rates():
    out = {}
    hdr, rows = treasury('yield_curve')
    r0 = rows[0]
    out['date'] = r0[hdr['Date']].strip()
    for key, col in (('y3m', '3 Mo'), ('y2y', '2 Yr'), ('y10y', '10 Yr'), ('y30y', '30 Yr')):
        if col in hdr: out[key] = num(r0[hdr[col]])
    hdr2, rows2 = treasury('real_yield_curve')
    r0 = rows2[0]
    out['date_real'] = r0[hdr2['Date']].strip()
    if '10 Yr' in hdr2: out['tips10y'] = num(r0[hdr2['10 Yr']])
    if out.get('y10y') is not None and out.get('tips10y') is not None:
        out['breakeven'] = round(out['y10y'] - out['tips10y'], 2)
    try:
        f = fdic()
        out.update(f)
        print('fdic:', f)
    except Exception as e:
        print('fdic failed', e, file=sys.stderr)
    try:
        js = None
        body = json.dumps({'seriesid': ['LNS14000000'], 'startyear': 2024, 'endyear': 2026}).encode()
        for attempt in range(3):
            try:
                req = urllib.request.Request('https://api.bls.gov/publicAPI/v1/timeseries/data/', data=body,
                                             headers={'Content-Type': 'application/json', 'User-Agent': UA['User-Agent']})
                with urllib.request.urlopen(req, timeout=30) as r:
                    js = json.load(r)
                break
            except Exception:
                time.sleep(3)
        if js is not None:
            d0 = js['Results']['series'][0]['data'][0]
            out['unemployment'] = float(d0['value'])
            out['unemployment_month'] = d0['periodName'] + ' ' + d0['year']
        else:
            print('BLS unreachable, unemployment omitted', file=sys.stderr)
    except Exception as e:
        print('BLS failed', e, file=sys.stderr)
    return out

NOTABLE=['SPCX','SKHY','CBRS','JMKE']

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
        old_ip = data.get('ipos') or {}
        if not ip['upcoming'] and old_ip.get('upcoming'):
            ip['upcoming'] = old_ip['upcoming']
            print('upcoming parse empty, kept previous rows')
        print('upcoming rows:', len(ip['upcoming']), 'priced rows:', len(ip['priced']))
    except Exception as e:
        ip = data.get('ipos', {'upcoming': [], 'priced': []})
        print('ipos FAILED', e, file=sys.stderr)
    try:
        rt = rates()
        print('rates:', rt.get('y10y'), '10y;', rt.get('tips10y'), 'tips;', rt.get('unemployment'), rt.get('unemployment_month'))
    except Exception as e:
        rt = data.get('rates')
        print('rates FAILED', e, file=sys.stderr)
    notable={}
    for sym in NOTABLE:
        try:
            q=quote(sym)
            if q and q.get('price'): notable[sym]=q
        except Exception:
            pass
        time.sleep(0.3)
    if rt: data['rates'] = rt
    data.update({'updated': datetime.datetime.now().isoformat(timespec='seconds'), 'quotes': quotes, 'ipos': ip, 'notable': notable})
    json.dump(data, open(dpath, 'w'), indent=1)
    print('wrote data.json,', len(quotes), 'quotes')
main()
