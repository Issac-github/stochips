"""Exploratory close-snapshot support proxies; no intraday validity claim."""
import collections
import datetime as dt
import json
from pathlib import Path
import experiment as ex
HERE=Path(__file__).resolve().parent
raw=ex.RAW
pool={(r['date'],r['code']):r for r in raw['limit_up_pool']}
heights={(r['date'],r['code']):r['continuous_days'] for r in raw['continuous_limit_up']}
members=collections.defaultdict(dict)
sectors=collections.defaultdict(set)
for r in raw['block_top_stock']:
 members[r['date'],r['block_code']][r['code']]=r
 sectors[r['date'],r['code']].add(r['block_code'])
def clock(value):
 if value in (None,'',0,'0'):return None
 s=str(value)
 if s.isdigit() and len(s)>=10:
  t=dt.datetime.fromtimestamp(int(s),dt.timezone(dt.timedelta(hours=8)))
  return t.hour*3600+t.minute*60+t.second
 if s.isdigit():s=s.zfill(6);return int(s[:2])*3600+int(s[2:4])*60+int(s[4:])
 if ':' in s:
  x=list(map(int,s.split(':')));return x[0]*3600+x[1]*60+(x[2] if len(x)>2 else 0)
 return None
variants=[('strict_oneword',2,True,None),('intraday_lower2',2,False,None),('early_lower2',2,False,35100),('intraday_include_first',1,False,None)]
def supports(row,minheight,oneword,deadline):
 found=set()
 for sector in sectors[row['date'],row['code']]:
  for code,member in members[row['date'],sector].items():
   if code==row['code'] or not code.startswith(('00','60')) or 'ST' in member['name'].upper() or '退' in member['name'] or member.get('is_new'):continue
   p=pool.get((row['date'],code),{})
   height=heights.get((row['date'],code),1)
   t=clock(p.get('limit_up_time'))
   if not minheight<=height<row['height']:continue
   if oneword and p.get('limit_up_type')!='一字板':continue
   if t is None or row['first'] is None or t>row['first']:continue
   if deadline is not None and t>deadline:continue
   found.add(code)
 return sorted(found)
frozen=json.loads((HERE/'frozen-rules.json').read_text())['selected']['nonword']
base=ex.candidates(frozen,['2026-07','2026-08','2026-09'])
results=[]
for name,h,one,deadline in variants:
 selected=[dict(r,support_codes=supports(r,h,one,deadline)) for r in base]
 if one:assert all(len(r['support_codes'])==r['supports'] for r in selected)
 selected=[r for r in selected if r['support_codes']]
 for env in [None,10]:
  rows=[r for r in selected if env is None or r['market_down_count']<env]
  top=ex.top1(rows)
  result=dict(name=name,market_down_lt=env,min_support_height=h,oneword_only=one,first_seal_max=deadline,
   monthly={m:ex.stat([r for r in top if r['month']==m]) for m in ['2026-07','2026-08','2026-09']},
   all=ex.stat(top),pool=ex.stat(rows),signals=[dict(r,**ex.LABELS[r['date'],r['code']]) for r in top])
  results.append(result)
  print(name,env,result['all']['hits'],result['all']['n'],result['monthly']['2026-09']['hits'],result['monthly']['2026-09']['n'])
(HERE/'support-rounds-results.json').write_text(json.dumps(dict(results=results,note='Exploratory; same-day closing sector and limit-up pools cause survivorship and timing limitations.'),ensure_ascii=False,indent=2))
