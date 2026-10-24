"""Finite, chronological continuation-screen experiments; no execution backtest."""
import argparse
import collections
import datetime as dt
import hashlib
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = next(p for p in HERE.parents if (p / '.git').exists())
SOURCE = REPO / '.trellis/tasks/archive/2026-10/10-02-audit-three-month-limit-up-strategy/research'
EVENTS = json.loads((SOURCE / 'events.json').read_text())
RAW = json.loads((SOURCE / 'market-data.json').read_text())
FEATURE_FIELDS = ['date', 'month', 'code', 'name', 'height', 'type', 'turnover',
                  'open_count', 'first', 'last', 'slowdown', 'concave_proxy', 'supports']
FEATURES = [{k:r[k] for k in FEATURE_FIELDS} for r in EVENTS if r['date']>='2026-07-10']
LABELS = {(r['date'],r['code']): {k:r[k] for k in ['next_limit','next_down','next_date']} for r in EVENTS}
DOWNS = collections.Counter(r['date'] for r in RAW['lower_limit_pool']
                           if r['code'].startswith(('00','60')) and 'ST' not in r['name'].upper() and '退' not in r['name'])
for r in FEATURES:
    r['market_down_count'] = DOWNS[r['date']]


def rules():
    out = []
    def add(name, group, **kw):
        out.append(dict(id=name, group=group, **kw))
    add('B_all', 'baseline', hmin=1)
    add('B_2plus', 'baseline', hmin=2)
    add('B_3plus', 'baseline', hmin=3)
    add('B_nonword', 'baseline', kind='nonword', hmin=2)
    add('B_oneword', 'baseline', kind='oneword', hmin=2)
    for name, kw in [
        ('height3',dict(hmin=3)), ('height4',dict(hmin=4)),
        ('seal0945',dict(last_max=35100)), ('seal1000',dict(last_max=36000)),
        ('seal1030',dict(last_max=37800)), ('zeroopen',dict(open_max=0)),
        ('oneopen',dict(open_max=1)), ('turn10',dict(turn_max=10)),
        ('turn20',dict(turn_max=20)), ('notslower',dict(not_slower=True)),
        ('marketdown20',dict(down_max=19)), ('support',dict(support_min=1))]:
        opts=dict(kind='nonword',hmin=2)
        opts.update(kw)
        add('A_'+name,'ablation',**opts)
    for hmin,hmax in [(2,5),(2,10),(3,5),(3,10)]:
        for seal in [35100,36000,37800]:
            for opens in [0,1]:
                for turnover in [10,20]:
                    add(f'N_h{hmin}-{hmax}_s{seal}_o{opens}_t{turnover}', 'nonword',
                        kind='nonword',hmin=hmin,hmax=hmax,last_max=seal,
                        open_max=opens,turn_max=turnover)
    for hmin,hmax in [(2,4),(2,5),(2,10),(3,5),(3,10)]:
        for turnover in [5,10,20,None]:
            opts=dict(kind='oneword',hmin=hmin,hmax=hmax)
            if turnover is not None:
                opts['turn_max']=turnover
            add(f'O_h{hmin}-{hmax}_t{turnover}', 'oneword', **opts)
    return out


def matches(r, rule):
    if r['height'] < rule.get('hmin',1) or r['height'] > rule.get('hmax',100):
        return False
    kind=rule.get('kind')
    if kind=='oneword' and r['type']!='一字板':
        return False
    if kind=='nonword' and r['type'] not in ('换手板','T字板'):
        return False
    for field,setting in [('last','last_max'),('open_count','open_max'),('turnover','turn_max')]:
        if setting in rule and (r[field] is None or r[field]>rule[setting]):
            return False
    if rule.get('not_slower') and r['slowdown'] is not False:
        return False
    if 'down_max' in rule and r['market_down_count']>rule['down_max']:
        return False
    if 'support_min' in rule and r['supports']<rule['support_min']:
        return False
    return True


def candidates(rule, months):
    return [r for r in FEATURES if r['month'] in months and matches(r,rule)]


def top1(rows):
    byday=collections.defaultdict(list)
    for r in rows:
        byday[r['date']].append(r)
    return [sorted(rs,key=lambda r:(-r['height'],r['open_count'] if r['open_count'] is not None else 999,
                                      r['last'] if r['last'] is not None else 999999,
                                      r['turnover'] if r['turnover'] is not None else 99999,r['code']))[0]
            for _,rs in sorted(byday.items())]


def stat(rows):
    n=len(rows)
    hits=sum(LABELS[(r['date'],r['code'])]['next_limit'] for r in rows)
    down=sum(LABELS[(r['date'],r['code'])]['next_down'] for r in rows)
    p=hits/n if n else 0
    z=1.96
    center=(p+z*z/(2*n))/(1+z*z/n) if n else 0
    half=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/(1+z*z/n) if n else 0
    return dict(n=n,hits=hits,hit_pct=round(p*100,2),downs=down,
                down_pct=round(down/n*100,2) if n else None,
                dates=len({r['date'] for r in rows}),stocks=len({r['code'] for r in rows}),
                wilson95=[round(100*(center-half),2),round(100*(center+half),2)])


def evaluate(rule, months):
    rows=candidates(rule,months)
    return dict(pool=stat(rows),top1=stat(top1(rows)))


def discover():
    library=rules()
    manifest=dict(candidate_rules=len(library),train='2026-07',validation='2026-08',holdout='2026-09',
        feature_fields=FEATURE_FIELDS+['market_down_count'],
        ranking='Eligible rules ranked by pooled July+August Wilson lower bound; August hit rate and lower downside break ties.',
        gates=dict(july_n_min=8,august_n_min=15,pooled_n_min=40,pooled_stocks_min=20,pooled_dates_min=15,
                   each_month_hit_ge_own_unfiltered_type_baseline=True),
        source_sha256=hashlib.sha256((SOURCE/'market-data.json').read_bytes()).hexdigest(),
        original_sha256=hashlib.sha256((REPO/'services/agent/chain/wiki/raw/001-连板龙头交易体系.md').read_bytes()).hexdigest(),
        caveat='September aggregate data was inspected in an earlier audit; temporal validation is not fully blind.',rules=library)
    (HERE/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
    results=[]
    for rule in library:
        results.append(dict(rule=rule,july=evaluate(rule,['2026-07']),august=evaluate(rule,['2026-08']),
                            development=evaluate(rule,['2026-07','2026-08'])))
    byid={r['rule']['id']:r for r in results}
    selected={}
    for family,base in [('nonword','B_nonword'),('oneword','B_oneword')]:
        ranked=[]
        for result in results:
            if result['rule']['group']!=family:
                continue
            j,a,p=(result[k]['pool'] for k in ['july','august','development'])
            ok=(j['n']>=8 and a['n']>=15 and p['n']>=40 and p['stocks']>=20 and p['dates']>=15
                and j['hit_pct']>=byid[base]['july']['pool']['hit_pct']
                and a['hit_pct']>=byid[base]['august']['pool']['hit_pct'])
            result['eligible']=ok
            if ok:
                ranked.append(result)
        ranked.sort(key=lambda r:(r['development']['pool']['wilson95'][0],r['august']['pool']['hit_pct'],
                                 -r['development']['pool']['down_pct'],r['development']['pool']['n']),reverse=True)
        selected[family]=ranked[0]['rule'] if ranked else byid[base]['rule']
    frozen=dict(selected=selected,selection_used_months=['2026-07','2026-08'],
                manifest_sha256=hashlib.sha256((HERE/'manifest.json').read_bytes()).hexdigest(),
                experiment_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    (HERE/'development-results.json').write_text(json.dumps(results,ensure_ascii=False,indent=2))
    (HERE/'frozen-rules.json').write_text(json.dumps(frozen,ensure_ascii=False,indent=2))
    print(json.dumps(dict(rule_count=len(results),selected=selected,eligible_counts={g:sum(r.get('eligible',False) and r['rule']['group']==g for r in results) for g in selected},
        selected_results=[byid[v['id']] for v in selected.values()],
        ablations=[r for r in results if r['rule']['group'] in ('baseline','ablation')]),ensure_ascii=False,indent=2))


def holdout():
    frozen=json.loads((HERE/'frozen-rules.json').read_text())
    assert frozen['experiment_sha256']==hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    selected=list(frozen['selected'].values())
    base=[r for r in rules() if r['group']=='baseline']
    result={}
    for r in base+selected:
        result[r['id']]={m:evaluate(r,[m]) for m in ['2026-07','2026-08','2026-09']}
        result[r['id']]['all']=evaluate(r,['2026-07','2026-08','2026-09'])
    records=[]
    for r in selected:
        for row in candidates(r,['2026-07','2026-08','2026-09']):
            records.append(dict(rule_id=r['id'],**row,**LABELS[(row['date'],row['code'])]))
    (HERE/'holdout-results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
    (HERE/'selected-events.json').write_text(json.dumps(records,ensure_ascii=False,indent=2))
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('phase',choices=['discover','holdout'])
    args=parser.parse_args()
    discover() if args.phase=='discover' else holdout()
