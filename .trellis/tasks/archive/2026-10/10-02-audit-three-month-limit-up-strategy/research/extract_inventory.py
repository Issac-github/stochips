import os, json
from sqlalchemy import create_engine, text
START, END = "2026-07-02", "2026-10-02"
engine = create_engine(os.environ["DATABASE_URL"])
result = {"start": START, "end": END, "tables": {}}
with engine.connect() as conn:
    conn.execute(text("SET SESSION TRANSACTION READ ONLY"))
    conn.execute(text("SET SESSION MAX_EXECUTION_TIME=30000"))
    columns = conn.execute(text("SELECT TABLE_NAME,COLUMN_NAME,DATA_TYPE FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=DATABASE() ORDER BY TABLE_NAME,ORDINAL_POSITION")).mappings().all()
    schema = {}
    for r in columns:
        schema.setdefault(r["TABLE_NAME"], []).append(dict(r))
    for table, cols in schema.items():
        names = [r["COLUMN_NAME"] for r in cols]
        date_col = "date" if "date" in names else "created_at" if "created_at" in names else "applied_at"
        ident = chr(96) + table + chr(96)
        dc = chr(96) + date_col + chr(96)
        r = dict(conn.execute(text(f"SELECT COUNT(*) n,MIN({dc}) first_date,MAX({dc}) last_date FROM {ident}")).mappings().one())
        r["columns"] = {c["COLUMN_NAME"]: c["DATA_TYPE"] for c in cols}
        r["daily"] = [dict(x) for x in conn.execute(text(f"SELECT DATE({dc}) d,COUNT(*) n FROM {ident} WHERE {dc} >= :start AND {dc} < DATE_ADD(:end,INTERVAL 1 DAY) GROUP BY DATE({dc}) ORDER BY d"), {"start":START,"end":END}).mappings()]
        if "code" in names:
            keys = "date,block_code,code" if table=="block_top_stock" else "date,code"
            r["duplicates"] = conn.execute(text(f"SELECT COUNT(*) FROM (SELECT {keys} FROM {ident} GROUP BY {keys} HAVING COUNT(*)>1) dup")).scalar()
        if "limit_up_type" in names:
            r["types"]=[dict(x) for x in conn.execute(text(f"SELECT limit_up_type,COUNT(*) n FROM {ident} WHERE date BETWEEN :start AND :end GROUP BY limit_up_type ORDER BY n DESC"),{"start":START,"end":END}).mappings()]
        result["tables"][table]=r
    result["fetch_status"]=[dict(x) for x in conn.execute(text("SELECT data_type,status,COUNT(*) n,MIN(date) first_date,MAX(date) last_date FROM data_fetch_log WHERE date BETWEEN :start AND :end GROUP BY data_type,status"),{"start":START,"end":END}).mappings()]
    result["review_config"]=[dict(x) for x in conn.execute(text("SELECT provider,model,strategy_path,COUNT(*) n FROM daily_market_review WHERE date BETWEEN :start AND :end GROUP BY provider,model,strategy_path"),{"start":START,"end":END}).mappings()]
print("INVENTORY_BEGIN")
print(json.dumps(result,ensure_ascii=False,default=str))
print("INVENTORY_END")
