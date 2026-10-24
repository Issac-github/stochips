"""Export only relevant market and audit fields through a read-only DB session."""
import os, json, decimal, datetime, gzip, sys, time
from sqlalchemy import create_engine, text
FIELDS = {
    "continuous_limit_up": "date,code,name,continuous_days,latest_limit_up_time,limit_up_open_count,limit_up_price,change_percent,volume,turnover,market_value",
    "limit_up_pool": "date,code,name,latest_price,limit_up_price,change_percent,limit_up_type,limit_up_time,open_count,last_time,strength,board_amount,volume_ratio,turnover_rate,market_value,block_name",
    "eastmoney_zt_pool": "date,code,name,latest_price,change_percent,first_limit_up_time,last_limit_up_time,volume,turnover,market_value,circulating_value,turnover_rate,amplitude,pre_3_day_change,block_name",
    "lower_limit_pool": "date,code,name,latest_price,change_percent,first_limit_down_time,last_limit_down_time,turnover_rate,market_type,is_new",
    "block_top": "date,block_code,block_name,stock_count,prev_stock_count,change_percent,continuous_plate_num,high_text,high_num,leading_stock,leading_stock_name,continuous_days",
    "block_top_stock": "date,block_code,block_name,code,name,continuous_days,limit_up_type,high_days,first_limit_up_time,last_limit_up_time,change_percent,latest_price,is_new,is_st,market_type,raw_json",
    "data_fetch_log": "date,data_type,status,record_count,created_at",
    "daily_job_run": "date,stage,status,attempt,created_at,updated_at",
    "daily_market_review": "date,content,provider,model,strategy_path,created_at,updated_at",
    "risk_assessment": "date,code,name,risk_level,risk_score,continuous_days,rule_score,ai_score,is_ai_analyzed,suggestion",
}
def encode(value):
    if isinstance(value, decimal.Decimal): return float(value)
    if isinstance(value,(datetime.date,datetime.datetime)): return value.isoformat()
    raise TypeError(type(value).__name__)
result={}
with create_engine(os.environ["DATABASE_URL"]).connect() as conn:
    conn.execute(text("SET SESSION TRANSACTION READ ONLY"))
    conn.execute(text("SET SESSION MAX_EXECUTION_TIME=30000"))
    for table, cols in FIELDS.items():
        result[table]=[dict(r) for r in conn.execute(text(f"SELECT {cols} FROM {table} WHERE date BETWEEN :start AND :end ORDER BY date"),{"start":"2026-07-02","end":"2026-10-02"}).mappings()]
payload = json.dumps(result,ensure_ascii=False,default=encode,separators=(",",":")).encode("utf-8")
sys.stdout.buffer.write(gzip.compress(payload))
sys.stdout.buffer.flush()
time.sleep(1)
