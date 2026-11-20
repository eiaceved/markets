"""Refresh ONLY the market strip (tape) in reads.json. Keeps items/audio/label intact.
Writes tape as the chip array the page renders: [{name, value, chg}, ...]
Quotes: Yahoo Finance chart API (spaced requests, retry); Bitcoin falls back to CoinGecko."""
import json, time, urllib.request, urllib.parse, datetime
UA={'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36'}
STRIP=[("S&P 500","^GSPC"),("Dow 30","^DJI"),("Nasdaq","^IXIC"),("10-Yr","^TNX"),("VIX","^VIX"),("Gold","GC=F"),("Bitcoin","BTC-USD")]
def fetch(url):
    req=urllib.request.Request(url,headers=UA)
    return urllib.request.urlopen(req,timeout=30).read().decode('utf-8','ignore')
def yahoo(sym):
    u='https://query1.finance.yahoo.com/v8/finance/chart/'+urllib.parse.quote(sym,safe='')+'?range=1d&interval=1d'
    for attempt in (1,2,3):
        try:
            m=json.loads(fetch(u))['chart']['result'][0]['meta']
            return m.get('regularMarketPrice'),(m.get('chartPreviousClose') or m.get('previousClose'))
        except Exception:
            if attempt==3: return None,None
            time.sleep(4*attempt)
def btc_cg():
    try:
        js=json.loads(fetch('https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd&include_24hr_change=true'))
        px=js['bitcoin']['usd']; chg=js['bitcoin'].get('usd_24h_change')
        return px,'CG',chg
    except Exception:
        return None,None,None
def chip(name,px,prev,forced_chg=None):
    if px is None: return None
    pct=forced_chg if forced_chg is not None else (((px-prev)/prev*100.0) if prev else None)
    # plain numbers: read-daily.html adds % and $ itself (fmt() in the page)
    value=round(float(px),2)
    chg=('' if pct is None else ('%+.2f%%'%pct))
    return {'name':name,'value':value,'chg':chg}
def main():
    d=json.load(open('reads.json'))
    tape=[]
    for name,sym in STRIP:
        if sym=='BTC-USD':
            px,_prev,cg=btc_cg()
            c=chip(name,px,None,cg)
        else:
            px,prev=yahoo(sym)
            c=chip(name,px,prev)
        if c: tape.append(c)
        time.sleep(3)
    if len(tape)<5:
        print('too few quotes (%d), keeping existing tape'%len(tape)); return 1
    d['tape']=tape
    d['updated']=datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%S+00:00')
    json.dump(d,open('reads.json','w'),indent=1,ensure_ascii=False)
    print('tape updated:',len(tape),'quotes; updated=',d['updated'])
    return 0
if __name__=='__main__':
    raise SystemExit(main())
