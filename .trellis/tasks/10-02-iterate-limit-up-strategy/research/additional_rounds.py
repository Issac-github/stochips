"""Additional exploratory diagnostics; does not alter frozen strategy."""
import json
from pathlib import Path
import experiment as ex
HERE=Path(__file__).resolve().parent
frozen=json.loads((HERE/'frozen-rules.json').read_text())['selected']['nonword']
months=['2026-07','2026-08','2026-09']
rounds=[]
# Round 2: fixed ranking alternatives on the frozen pool.
rankings={
 'height_first':lambda r:(-r['height'],r['open_count'],r['last'],r['turnover'],r['code']),
 'early_seal':lambda r:(r['last'],-r['height'],r['code']),
 'low_turnover':lambda r:(r['turnover'],-r['height'],r['code']),
 'few_opens':lambda r:(r['open_count'],-r['height'],r['code']),
 'low_height':lambda r:(r['height'],r['last'],r['code'])}
def pick(rows,key):
 days=sorted({r['date'] for r in rows})
 return [min((r for r in rows if r['date']==d),key=key) for d in days]
for name,key in rankings.items():
 rounds.append(dict(round='ranking',name=name,results={m:ex.stat(pick(ex.candidates(frozen,[m]),key)) for m in months}))
# Round 3: add individual context features, without recombining winners.
for name,change in [('support1',{'support_min':1}),('not_slower',{'not_slower':True}),('market_down_lt10',{'down_max':9}),('market_down_lt20',{'down_max':19}),('market_down_lt30',{'down_max':29})]:
 rule=dict(frozen,**change)
 rounds.append(dict(round='context',name=name,results={m:ex.evaluate(rule,[m]) for m in months}))
# Round 4: each observed week is separately reported, including weeks without picks.
import datetime
rows=ex.top1(ex.candidates(frozen,months))
week=lambda r:datetime.date.fromisoformat(r['date']).strftime('%G-W%V')
weekly={w:ex.stat([r for r in rows if week(r)==w]) for w in sorted({week(r) for r in ex.FEATURES})}
result=dict(note='All rounds are exploratory after September was inspected. No new out-of-sample claim or rule promotion.',rounds=rounds,weekly_top1=weekly)
(HERE/'additional-rounds-results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
for r in rounds:
 print(r['round'],r['name'],[(m,(v.get('top1',v))['hits'],(v.get('top1',v))['n']) for m,v in r['results'].items()])
print('weekly',[(k,v['hits'],v['n']) for k,v in weekly.items()])
