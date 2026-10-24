"""Descriptive study of server limit-up snapshots; not an execution backtest."""
import collections
import datetime as dt
import hashlib
import json
import math
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = json.loads((ROOT / "market-data.json").read_text())
TZ = dt.timezone(dt.timedelta(hours=8))
DATES = sorted({r["date"] for r in DATA["limit_up_pool"]})
NEXT = dict(zip(DATES, DATES[1:]))
PREV = dict(zip(DATES[1:], DATES))
INDEX = {t: {(r["date"], r["code"]): r for r in DATA[t]} for t in
         ("limit_up_pool", "continuous_limit_up", "eastmoney_zt_pool", "lower_limit_pool")}
MEMBERS = collections.defaultdict(dict)
SECTORS = collections.defaultdict(set)
for r in DATA["block_top_stock"]:
    MEMBERS[(r["date"], r["block_code"])][r["code"]] = r
    SECTORS[(r["date"], r["code"])].add(r["block_code"])
BLOCK = {(r["date"], r["block_code"]): r for r in DATA["block_top"]}


def main(r):
    return r["code"].startswith(("00", "60")) and "ST" not in r["name"].upper() and "退" not in r["name"]


def clock(value):
    if value in (None, "", 0, "0"):
        return None
    s = str(value)
    if s.isdigit() and len(s) >= 10:
        d = dt.datetime.fromtimestamp(int(s), TZ)
        return d.hour * 3600 + d.minute * 60 + d.second
    if s.isdigit() and len(s) <= 6:
        s = s.zfill(6)
        return int(s[:2]) * 3600 + int(s[2:4]) * 60 + int(s[4:])
    if ":" in s:
        parts = [int(x) for x in s.split(":")]
        return parts[0] * 3600 + parts[1] * 60 + (parts[2] if len(parts)>2 else 0)
    return None


def height(date, code):
    return INDEX["continuous_limit_up"].get((date, code), {}).get("continuous_days", 1)


def hit(date, code):
    return (date, code) in INDEX["limit_up_pool"] or (date, code) in INDEX["eastmoney_zt_pool"]


def down(date, code):
    return (date, code) in INDEX["lower_limit_pool"]


def summary(rows):
    n = len(rows)
    wins = sum(r["next_limit"] for r in rows)
    drops = sum(r["next_down"] for r in rows)
    p = wins / n if n else 0
    z = 1.96
    den = 1 + z*z/n if n else 1
    mid = (p + z*z/(2*n))/den if n else 0
    half = z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/den if n else 0
    return {"n": n, "next_limit": wins, "next_limit_pct": round(p*100,2),
            "wilson95_pct": [round((mid-half)*100,2), round((mid+half)*100,2)],
            "next_down": drops, "next_down_pct": round(drops/n*100,2) if n else None,
            "unique_stocks": len({r["code"] for r in rows})}


EVENTS = []
for r in DATA["limit_up_pool"]:
    date, code = r["date"], r["code"]
    if date not in NEXT or not main(r):
        continue
    tomorrow = NEXT[date]
    h = height(date, code)
    first, last = clock(r["limit_up_time"]), clock(r["last_time"])
    yesterday = PREV.get(date)
    prior = INDEX["limit_up_pool"].get((yesterday, code), {})
    prior_last = clock(prior.get("last_time"))
    support = set()
    for sector in SECTORS[(date, code)]:
        for other, member in MEMBERS[(date, sector)].items():
            other_pool = INDEX["limit_up_pool"].get((date, other), {})
            if other == code or not main(member) or member.get("is_new"):
                continue
            other_h = height(date, other)
            other_time = clock(other_pool.get("limit_up_time"))
            if (2 <= other_h < h and other_pool.get("limit_up_type") == "一字板"
                    and first is not None and other_time is not None and other_time <= first):
                support.add(other)
    sector_growth = []
    for sector in SECTORS[(date, code)]:
        today_block, yesterday_block = BLOCK.get((date,sector)), BLOCK.get((yesterday,sector))
        if today_block and yesterday_block:
            sector_growth.append(today_block["stock_count"] > yesterday_block["stock_count"])
    event = {"date": date, "next_date": tomorrow, "month": date[:7], "code":code,
             "name":r["name"], "height":h, "type":r["limit_up_type"],
             "turnover":r["turnover_rate"], "open_count":r["open_count"],
             "first":first,"last":last,"next_limit":hit(tomorrow,code),
             "next_down":down(tomorrow,code), "next_in_pool":(tomorrow,code) in INDEX["limit_up_pool"],
             "supports":len(support), "support_codes":sorted(support),
             "sector_known":bool(SECTORS[(date,code)]),
             "sector_growth": any(sector_growth) if sector_growth else None,
             "slowdown": last > prior_last if last is not None and prior_last is not None else None,
             "reopened": r["open_count"] > 0 if r["open_count"] is not None else None,
             "concave_proxy": (first <= 10*3600 and last-first >= 3600 and r["open_count"]>0)
                 if first is not None and last is not None and r["open_count"] is not None else None}
    EVENTS.append(event)

DAILY = []
for date in DATES:
    pool = [r for r in DATA["limit_up_pool"] if r["date"] == date and main(r)]
    cont = [r for r in DATA["continuous_limit_up"] if r["date"] == date and main(r)]
    downs = [r for r in DATA["lower_limit_pool"] if r["date"] == date and main(r)]
    events = [r for r in EVENTS if r["date"] == date]
    DAILY.append({"date":date,"limit_count":len(pool),"continuous_count":len(cont),
                  "max_height":max([r["continuous_days"] for r in cont] or [1]),
                  "one_word":sum(r["limit_up_type"]=="一字板" for r in pool),
                  "limit_down_count":len(downs),"next":summary(events),
                  "next_high":summary([r for r in events if r["height"]>=3])})
DAILY_INDEX = {r["date"]:r for r in DAILY}
HIGH = [r for r in EVENTS if r["height"]>=3]
GROUPS = {}
for label, rows in [("all",EVENTS),("high3plus",HIGH),
                    ("high3plus_post0710",[r for r in HIGH if r["date"]>="2026-07-10"])]:
    GROUPS[label] = summary(rows)
    for field in ["height","type","month","slowdown","reopened","concave_proxy","sector_growth"]:
        GROUPS[label+"_by_"+field] = {str(v):summary([r for r in rows if r[field]==v]) for v in sorted({r[field] for r in rows},key=str)}
    known = [r for r in rows if r["turnover"] is not None]
    GROUPS[label+"_turnover"] = {"ge20":summary([r for r in known if r["turnover"]>=20]),"lt20":summary([r for r in known if r["turnover"]<20])}
    known = [r for r in rows if r["sector_known"]]
    GROUPS[label+"_supports"] = {str(k):summary([r for r in known if min(r["supports"],3)==k]) for k in range(4)}
    GROUPS[label+"_seal_time"] = {"by1000":summary([r for r in rows if r["last"] is not None and r["last"]<=36000]),"after1400":summary([r for r in rows if r["last"] is not None and r["last"]>=50400])}

BREAKS=[]
for r in HIGH:
    if r["next_limit"]:
        continue
    next2 = NEXT.get(r["next_date"])
    if next2 is None:
        continue
    future = []
    day=r["next_date"]
    for _ in range(5):
        day=NEXT.get(day)
        if day is None:
            break
        future.append(day)
    BREAKS.append({**r,"rebound_next":hit(next2,r["code"]),
                   "return5":any(hit(day,r["code"]) for day in future) if len(future)==5 else None,
                   "down5":any(down(day,r["code"]) for day in future) if len(future)==5 else None})

def break_summary(rows):
    complete=[r for r in rows if r["return5"] is not None]
    return {"n":len(rows),"rebound_next":sum(r["rebound_next"] for r in rows),
            "next_down":sum(r["next_down"] for r in rows),"n5":len(complete),
            "return5":sum(r["return5"] for r in complete),"down5":sum(r["down5"] for r in complete)}

QUALITY={}
for table in ("continuous_limit_up","limit_up_pool","eastmoney_zt_pool"):
    QUALITY[table]={"rows":len(DATA[table]),"null_or_blank":{},"zeros":{}}
    for field in DATA[table][0]:
        QUALITY[table]["null_or_blank"][field]=sum(r[field] is None or r[field]=="" for r in DATA[table])
        QUALITY[table]["zeros"][field]=sum(r[field]==0 for r in DATA[table])
overlap=[]
block_prices={}
for r in DATA["block_top_stock"]:
    if r.get("latest_price"):
        block_prices[(r["date"],r["code"])]=r["latest_price"]
for r in DATA["eastmoney_zt_pool"]:
    price=block_prices.get((r["date"],r["code"]))
    if price:
        overlap.append(r["latest_price"]/price)
QUALITY["em_price_ratio"]={"n":len(overlap),"median":statistics.median(overlap),"near1000":sum(abs(v-1000)<0.01 for v in overlap)}
QUALITY["block_memberships"]={"rows":len(DATA["block_top_stock"]),"stock_days":len({(r["date"],r["code"]) for r in DATA["block_top_stock"]})}
QUALITY["em_weekend"]=[r["date"] for r in DATA["eastmoney_zt_pool"] if dt.date.fromisoformat(r["date"]).weekday()>=5]
QUALITY["cross_source_next_hits"]={"union":sum(r["next_limit"] for r in EVENTS),"ths":sum(r["next_in_pool"] for r in EVENTS)}
QUALITY["unobserved_after_high_break"] = sum(not any((r["next_date"],r["code"]) in INDEX[t] for t in INDEX) for r in HIGH if not r["next_limit"])
QUALITY["high_break_n"] = sum(not r["next_limit"] for r in HIGH)
RESULT={"data_sha256":hashlib.sha256((ROOT/"market-data.json").read_bytes()).hexdigest(),
        "quality":QUALITY,"groups":GROUPS,"daily":DAILY,
        "breaks":break_summary(BREAKS),
        "breaks_by_height":{str(h):break_summary([r for r in BREAKS if r["height"]==h]) for h in sorted({r["height"] for r in BREAKS})},
        "high_event_examples":HIGH,"break_examples":BREAKS}
(ROOT/"statistics.json").write_text(json.dumps(RESULT,ensure_ascii=False,indent=2))
(ROOT/"events.json").write_text(json.dumps(EVENTS,ensure_ascii=False))
print(json.dumps({"groups":GROUPS,"breaks":RESULT["breaks"],"breaks_by_height":RESULT["breaks_by_height"],
                  "quality_selected":{k:v for k,v in QUALITY.items() if k not in ("continuous_limit_up","limit_up_pool","eastmoney_zt_pool","em_weekend")}},ensure_ascii=False,indent=2))
