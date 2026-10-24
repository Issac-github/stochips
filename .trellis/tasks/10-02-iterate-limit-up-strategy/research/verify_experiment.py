"""Check chronological isolation, raw labels, deterministic picks and file integrity."""
import ast
import contextlib
import hashlib
import io
import json
import tempfile
from pathlib import Path
import experiment as ex

here=Path(__file__).resolve().parent
frozen=json.loads((here/'frozen-rules.json').read_text())
manifest=json.loads((here/'manifest.json').read_text())
for f in here.glob('*.py'):
    ast.parse(f.read_text(),filename=str(f))
assert len(ex.rules())==85
assert len({r['id'] for r in ex.rules()})==85
assert all(not {'next_limit','next_down','next_date'} & set(r) for r in ex.FEATURES)
assert len({(r['date'],r['code']) for r in ex.FEATURES})==len(ex.FEATURES)
ups={(r['date'],r['code']) for t in ['limit_up_pool','eastmoney_zt_pool'] for r in ex.RAW[t]}
downs={(r['date'],r['code']) for r in ex.RAW['lower_limit_pool']}
for r in ex.FEATURES:
    label=ex.LABELS[(r['date'],r['code'])]
    assert r['date']<label['next_date']<='2026-09-30'
    assert label['next_limit']==((label['next_date'],r['code']) in ups)
    assert label['next_down']==((label['next_date'],r['code']) in downs)
assert ex.evaluate(frozen['selected']['nonword'],['2026-09'])['pool']['hits']==23
assert ex.evaluate(frozen['selected']['nonword'],['2026-09'])['top1']['hits']==9
assert ex.evaluate(frozen['selected']['nonword'],['2026-07','2026-08'],True)['pool']['n']==117

# Deliberately invert every outcome dated September, including Aug 31 signals.
# The development selection must remain exactly identical after purging.
original_labels=ex.LABELS
ex.LABELS={k:dict(v,next_limit=not v['next_limit'],next_down=not v['next_down'])
           if v['next_date']>='2026-09-01' else dict(v) for k,v in ex.LABELS.items()}
original_here=ex.HERE
with tempfile.TemporaryDirectory(prefix='stochips-selection-check-') as tmp:
    ex.HERE=Path(tmp)
    with contextlib.redirect_stdout(io.StringIO()):
        ex.discover()
    changed=json.loads((ex.HERE/'frozen-rules.json').read_text())
    assert changed['selected']==frozen['selected'], 'September outcomes leaked into selection'
ex.LABELS=original_labels
ex.HERE=original_here
for rule in frozen['selected'].values():
    rows=ex.candidates(rule,['2026-07','2026-08','2026-09'])
    assert ex.top1(rows)==ex.top1(list(reversed(rows)))
    assert len(ex.top1(rows))==len({r['date'] for r in rows})
assert manifest['source_sha256']==hashlib.sha256((ex.SOURCE/'market-data.json').read_bytes()).hexdigest()
assert manifest['original_sha256']==hashlib.sha256((ex.REPO/'services/agent/chain/wiki/raw/001-连板龙头交易体系.md').read_bytes()).hexdigest()
assert frozen['experiment_sha256']==hashlib.sha256((here/'experiment.py').read_bytes()).hexdigest()
result=dict(status='passed',checks=['Python syntax','85 unique predefined rules','features exclude labels',
    'unique stock-date observations','raw snapshot outcome parity','next-day time ordering',
    'purged training counts','September-outcome perturbation cannot change selection',
    'deterministic top-one ranking','snapshot hash','original strategy unchanged','frozen source hash'])
(here/'verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
print(json.dumps(result,ensure_ascii=False))
