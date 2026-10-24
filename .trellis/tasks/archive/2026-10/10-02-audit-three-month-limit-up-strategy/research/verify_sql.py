import os,json
from sqlalchemy import create_engine,text
q="""
WITH days AS (SELECT DISTINCT date FROM limit_up_pool WHERE date BETWEEN '2026-07-02' AND '2026-09-30'),
calendar AS (SELECT date,LEAD(date) OVER(ORDER BY date) next_date FROM days),
events AS (
 SELECT p.date,p.code,p.name,COALESCE(c.continuous_days,1) height,p.turnover_rate,
        n.code IS NOT NULL next_limit,l.code IS NOT NULL next_down
 FROM limit_up_pool p JOIN calendar d ON p.date=d.date AND d.next_date IS NOT NULL
 LEFT JOIN continuous_limit_up c ON c.date=p.date AND c.code=p.code
 LEFT JOIN limit_up_pool n ON n.date=d.next_date AND n.code=p.code
 LEFT JOIN lower_limit_pool l ON l.date=d.next_date AND l.code=p.code
 WHERE p.code REGEXP '^(00|60)' AND UPPER(p.name) NOT LIKE '%ST%' AND p.name NOT LIKE '%退%'
)
SELECT 'all' label,COUNT(*) n,SUM(next_limit) next_limit,SUM(next_down) next_down FROM events
UNION ALL SELECT 'high3plus',COUNT(*),SUM(next_limit),SUM(next_down) FROM events WHERE height>=3
UNION ALL SELECT 'high_turn20',COUNT(*),SUM(next_limit),SUM(next_down) FROM events WHERE height>=3 AND turnover_rate>=20
UNION ALL SELECT 'high_post0710',COUNT(*),SUM(next_limit),SUM(next_down) FROM events WHERE height>=3 AND date>='2026-07-10'
"""
with create_engine(os.environ["DATABASE_URL"]).connect() as conn:
 conn.execute(text("SET SESSION TRANSACTION READ ONLY"))
 conn.execute(text("SET SESSION MAX_EXECUTION_TIME=30000"))
 result=[dict(r) for r in conn.execute(text(q)).mappings()]
print(json.dumps(result,ensure_ascii=False,default=str))
