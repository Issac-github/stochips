"""Post-freeze sensitivity checks; never overwrite or reselect frozen rules."""
import collections
import datetime as dt
import hashlib
import json
import random
from pathlib import Path
import experiment as ex

HERE=Path(__file__).resolve().parent
frozen=json.loads((HERE/'frozen-rules.json').read_text())
rule=frozen['selected']['nonword']
baseline=next(r for r in ex.rules() if r['id']=='B_nonword')
variants=[]
for name,changes in [('frozen',{}),('seal0945',{'last_max':35100}),
                     ('seal1030',{'last_max':37800}),('zero_open',{'open_max':0}),
                     ('two_opens',{'open_max':2}),('turn15',{'turn_max':15}),
                     ('turn25',{'turn_max':25}),('height3',{'hmin':3}),('height_max5',{'hmax':5})]:
    candidate=dict(rule,**changes)
    variants.append(dict(name=name,rule=candidate,
        development=ex.evaluate(candidate,['2026-07','2026-08'],True),
        september=ex.evaluate(candidate,['2026-09'])))

for field in ['last_max','open_max','turn_max']:
    candidate={k:v for k,v in rule.items() if k!=field}
    variants.append(dict(name='remove_'+field,rule=candidate,
        development=ex.evaluate(candidate,['2026-07','2026-08'],True),
        september=ex.evaluate(candidate,['2026-09'])))

dates=sorted({r['date'] for r in ex.EVENTS}|{v['next_date'] for v in ex.LABELS.values()})
dayindex={d:i for i,d in enumerate(dates)}
def episode_first(rows):
    kept={}
    for r in sorted(rows,key=lambda r:(r['date'],r['code'])):
        key=(r['code'],dayindex[r['date']]-r['height']+1)
        kept.setdefault(key,r)
    return list(kept.values())

episodes={}
for r in [baseline,rule,frozen['selected']['oneword'],next(r for r in ex.rules() if r['id']=='B_oneword')]:
    for mode,select in [('all_candidates',lambda rows:rows),('daily_top1',ex.top1)]:
        rows=episode_first(select(ex.candidates(r,['2026-07','2026-08','2026-09'])))
        episodes[r['id']+'_'+mode]={m:ex.stat([v for v in rows if v['month']==m]) for m in ['2026-07','2026-08','2026-09']}
        episodes[r['id']+'_'+mode]['all']=ex.stat(rows)

def bootstrap_delta(months, mode, seed=20261002):
    selected=ex.candidates(rule,months)
    controls=ex.candidates(baseline,months)
    if months==['2026-07','2026-08']:
        selected=[r for r in selected if ex.LABELS[(r['date'],r['code'])]['next_date'][:7]==r['month']]
        controls=[r for r in controls if ex.LABELS[(r['date'],r['code'])]['next_date'][:7]==r['month']]
    if mode=='top1':
        selected,controls=ex.top1(selected),ex.top1(controls)
    def grouped(rows):
        g=collections.defaultdict(list)
        for r in rows:
            g[dt.date.fromisoformat(r['date']).isocalendar()[:2]].append(r)
        return g
    sg,cg=grouped(selected),grouped(controls)
    weeks=sorted(set(sg)|set(cg))
    rng=random.Random(seed)
    deltas=[]
    for _ in range(3000):
        picks=rng.choices(weeks,k=len(weeks))
        a=[r for w in picks for r in sg[w]]
        b=[r for w in picks for r in cg[w]]
        if a and b:
            ha=sum(ex.LABELS[(r['date'],r['code'])]['next_limit'] for r in a)/len(a)
            hb=sum(ex.LABELS[(r['date'],r['code'])]['next_limit'] for r in b)/len(b)
            deltas.append((ha-hb)*100)
    deltas.sort()
    return dict(weeks=len(weeks),replicates=len(deltas),
        delta95_pp=[round(deltas[int(len(deltas)*.025)],2),round(deltas[int(len(deltas)*.975)],2)])

bootstrap={f'{period}_{mode}':bootstrap_delta(months,mode) for period,months in
           [('development',['2026-07','2026-08']),('september',['2026-09'])] for mode in ['pool','top1']}

allrows=ex.candidates(rule,['2026-07','2026-08','2026-09'])
top=ex.top1(allrows)
failure=[dict(r,**ex.LABELS[(r['date'],r['code'])]) for r in top
         if not ex.LABELS[(r['date'],r['code'])]['next_limit']]
result=dict(variants=variants,episodes=episodes,bootstrap=bootstrap,
    top1_failures=failure,nonword_pool_downs=[dict(r,**ex.LABELS[(r['date'],r['code'])]) for r in allrows if ex.LABELS[(r['date'],r['code'])]['next_down']],
    frozen_hash=hashlib.sha256((HERE/'frozen-rules.json').read_bytes()).hexdigest(),
    note='Sensitivity diagnostics observed after holdout; not eligible for promotion as a newly validated strategy.')
(HERE/'robustness-results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
print(json.dumps(result,ensure_ascii=False,indent=2))
