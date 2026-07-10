"""
股票数据与Codex每日复盘Agent系统主入口

Usage:
    python main.py agent "目标" [date]       # 目标驱动StockAgent
    python main.py fetch [date]             # 抓取数据
    python main.py assess [date]            # 每日Codex市场复盘（兼容别名）
    python main.py ai-analyze [date]        # 每日Codex市场复盘（兼容别名）
    python main.py assess-ai [date] [--force-ai]
                                             # 每日Codex市场复盘
    python main.py run [date]               # 完整流程（抓取+Codex复盘）
    python main.py schedule                 # 启动定时任务
    python main.py status [date]            # 查看数据状态
    python main.py notify-feishu [date]     # 发送飞书涨停数据播报卡片
    python main.py wiki query "问题"        # 查询wiki知识库
    python main.py wiki ingest raw/xxx.md   # 摄入wiki原始素材
    python main.py wiki lint                # 检查wiki健康状态
    python main.py wiki build               # 重建wiki向量索引
    python main.py wiki pages               # 列出wiki页面
    python main.py codex-login              # ChatGPT/Codex设备码登录

Environment Variables:
    DATABASE_URL: MySQL连接URL (required)
    STOCK_COOKIE: 数据抓取的cookie (optional)
    AI_PROVIDER: 每日市场复盘必须设为 codex
    AI_FALLBACK_PROVIDER: 建议设为 none
    CODEX_MODEL: Codex模型（可选，留空使用账号默认模型）
    FEISHU_WEBHOOK_URL: 飞书自定义机器人Webhook (飞书播报需要)
    FEISHU_WEBHOOK_SECRET: 飞书机器人签名密钥 (optional)
    LOG_LEVEL: 日志级别 (default: INFO)
"""

import asyncio
import logging
import os
import sys
from datetime import date, datetime
from typing import Optional

from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

from chain.stock.agents import (
    create_daily_market_review_agent,
    create_feishu_notifier,
    create_stock_agent,
    create_wiki_agent,
)
from chain.stock.data import create_fetcher
from chain.stock.data.storage import StockDataStorage
from chain.stock.config import config
from chain.stock.agents.codex_client import login_chatgpt_device_code
from chain.stock.scheduler import create_scheduler

def setup_logging():
    """设置日志"""
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        level=getattr(logging, log_level),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler("stock_agent.log", encoding="utf-8"),
        ],
    )


def should_skip_after_fetch(database_url: str, date_obj: date, action: str) -> bool:
    storage = StockDataStorage(database_url)
    if storage.is_fetch_skipped(date_obj):
        print(
            f"跳过{action}: {date_obj} 已被抓取流程标记为非交易日/"
            "上游旧数据，不执行后续流程"
        )
        return True
    return False


def parse_date(date_str: Optional[str]) -> date:
    """解析日期字符串"""
    if not date_str:
        return date.today()

    try:
        return datetime.strptime(date_str, "%Y%m%d").date()
    except ValueError:
        try:
            return datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            print(f"错误：无法解析日期 {date_str}")
            print("支持的格式：YYYYMMDD 或 YYYY-MM-DD")
            sys.exit(1)


def parse_date_and_flags(args: list[str]) -> tuple[Optional[str], set[str]]:
    """Split an optional date argument from command flags."""
    target_date = None
    flags: set[str] = set()
    for arg in args:
        if arg.startswith("--"):
            flags.add(arg)
        elif target_date is None:
            target_date = arg
        else:
            print(f"错误：未知参数 {arg}")
            sys.exit(1)
    return target_date, flags


def cmd_fetch(target_date: Optional[str] = None):
    """抓取数据命令"""
    date_obj = parse_date(target_date)
    date_str = date_obj.strftime("%Y%m%d")

    print(f"开始抓取数据: {date_str}")

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("错误：未设置DATABASE_URL环境变量")
        sys.exit(1)

    cookie = os.getenv("STOCK_COOKIE")

    fetcher = create_fetcher(cookie)
    storage = StockDataStorage(database_url)

    try:
        # 抓取数据
        data = fetcher.fetch_all_data(date_str)

        # 检查错误
        errors = data.get("errors", [])
        if errors:
            print("警告：部分数据抓取失败:")
            for error in errors:
                print(f"  - {error['type']}: {error['error']}")

        # 存储数据
        results = storage.save_all_data(data, date_obj)
        if data.get("skipped"):
            print(f"\n⏭️ 数据抓取跳过：{data.get('skip_reason', 'skipped')}")
            return

        print("\n数据保存结果：")
        for data_type, (success, failed) in results.items():
            print(f"  {data_type}: 成功 {success} 条", end="")
            if failed > 0:
                print(f", 失败 {failed} 条")
            else:
                print()

        # 检查状态
        status = storage.get_data_status(date_obj)
        print("\n数据状态检查：")
        print(f"  连板天梯: {status['continuous_limit_up']} 条")
        print(f"  最强风口: {status['block_top']} 条")
        print(f"  涨停强度: {status['limit_up_pool']} 条")
        print(f"  东财涨停池: {status['eastmoney_zt_pool']} 条")

        if status["is_complete"]:
            print("\n✅ 数据抓取完成")
        else:
            print("\n⚠️ 数据不完整")

    except Exception as e:
        print(f"错误：{e}")
        logging.exception("抓取数据失败")
        sys.exit(1)


def cmd_assess(target_date: Optional[str] = None):
    """Compatibility alias for the daily Codex review."""
    cmd_assess_daily_review(target_date)


def cmd_ai_analyze(target_date: Optional[str] = None):
    """Compatibility alias for one daily qualitative Codex review."""
    cmd_assess_daily_review(target_date)


def cmd_assess_daily_review(
    target_date: Optional[str] = None,
    force_ai: bool = False,
):
    """Generate one qualitative Codex review from the daily market material."""
    date_obj = parse_date(target_date)

    print(f"开始Codex每日市场复盘: {date_obj}")

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("错误：未设置DATABASE_URL环境变量")
        sys.exit(1)

    if should_skip_after_fetch(database_url, date_obj, "Codex每日市场复盘"):
        return

    if config.ai.provider != "codex":
        print("错误：每日市场复盘需要 AI_PROVIDER=codex")
        sys.exit(1)

    agent = None
    try:
        agent = create_daily_market_review_agent(database_url)
        if force_ai:
            print("🔁 已开启强制重跑，将替换已有Codex每日复盘")

        result = agent.run(date_obj, force=force_ai)
        print("\nCodex每日市场复盘完成：")
        print(f"  日期: {result.date}")
        print(f"  来源: {result.provider}")
        print(f"  模型: {result.model}")
        print(f"  状态: {'复用已有报告' if result.cached else '新生成并保存'}")
        print("\n✅ Codex每日市场复盘完成")

    except Exception as e:
        print(f"错误：{e}")
        logging.exception("Codex每日市场复盘失败")
        sys.exit(1)
    finally:
        if agent is not None:
            agent.close()


def cmd_run(target_date: Optional[str] = None):
    """运行完整流程"""
    date_obj = parse_date(target_date)

    print(f"开始完整流程: {date_obj}")
    print("=" * 50)

    # 1. 抓取数据
    cmd_fetch(target_date)

    print("\n" + "=" * 50)

    # 2. 数据刚抓取完成，强制用新快照生成当日Codex复盘。
    cmd_assess_daily_review(target_date, force_ai=True)

    print("\n" + "=" * 50)
    print("✅ 所有任务完成")


def cmd_agent(goal: Optional[str] = None, target_date: Optional[str] = None):
    """运行目标驱动 StockAgent"""
    if not goal:
        print('错误：缺少目标，例如 python main.py agent "完成每日市场复盘" 20260506')
        sys.exit(1)

    date_obj = parse_date(target_date)
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("错误：未设置DATABASE_URL环境变量")
        sys.exit(1)

    print(f"启动 StockAgent: {goal}")
    print(f"日期: {date_obj}")
    print("=" * 60)

    agent = None
    try:
        agent = create_stock_agent(database_url)
        result = agent.run(goal, date_obj)
        print(result.summary)
    except Exception as e:
        print(f"错误：{e}")
        logging.exception("StockAgent执行失败")
        sys.exit(1)
    finally:
        if agent is not None:
            agent.close()


def cmd_schedule():
    """启动定时任务"""
    print("启动定时任务调度器...")

    def notification(msg: str):
        print(f"\n[通知] {msg}")

    async def run_scheduler():
        scheduler = create_scheduler(notification_callback=notification)

        if config.ai.provider != "codex":
            print("AI_PROVIDER 不是 codex，未设置每日串行播报任务")
        elif not os.getenv("FEISHU_WEBHOOK_URL"):
            print("未配置 FEISHU_WEBHOOK_URL，未设置每日串行播报任务")
        else:
            # 一个任务内严格按抓取 -> Codex复盘 -> 飞书播报执行。
            scheduler.schedule_daily_job()

        print("\n已设置以下定时任务：")
        for job in scheduler.get_jobs():
            print(f"  - {job.name}: {job.trigger}")

        print("\n按 Ctrl+C 停止调度器")

        # 启动调度器
        scheduler.start()

        # 保持运行
        try:
            await asyncio.Event().wait()
        finally:
            print("\n正在停止调度器...")
            scheduler.shutdown()
            print("调度器已停止")

    try:
        asyncio.run(run_scheduler())
    except KeyboardInterrupt:
        pass

    except Exception as e:
        print(f"错误：{e}")
        logging.exception("启动调度器失败")
        sys.exit(1)


def cmd_status(target_date: Optional[str] = None):
    """查看数据状态"""
    date_obj = parse_date(target_date)

    print(f"查询数据状态: {date_obj}")

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("错误：未设置DATABASE_URL环境变量")
        sys.exit(1)

    storage = StockDataStorage(database_url)

    try:
        status = storage.get_data_status(date_obj)

        print("\n数据状态：")
        print(f"  日期: {status['date']}")
        print(f"  连板天梯: {status['continuous_limit_up']} 条")
        print(f"  最强风口: {status['block_top']} 条")
        print(f"  涨停强度: {status['limit_up_pool']} 条")
        print(f"  东财涨停池: {status['eastmoney_zt_pool']} 条")

        if status["is_complete"]:
            print("\n✅ 数据完整")
        else:
            print("\n⚠️ 数据不完整")

        if status["logs"]:
            print("\n操作日志：")
            for log in status["logs"]:
                print(
                    f"  [{log['created_at']}] {log['data_type']}: "
                    f"{log['status']} ({log['record_count']} 条)"
                )

    except Exception as e:
        print(f"错误：{e}")
        logging.exception("查询状态失败")
        sys.exit(1)


def cmd_notify_feishu(target_date: Optional[str] = None):
    """发送飞书涨停数据播报卡片"""
    date_obj = parse_date(target_date)

    print(f"发送飞书涨停播报: {date_obj}")

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("错误：未设置DATABASE_URL环境变量")
        sys.exit(1)

    if not os.getenv("FEISHU_WEBHOOK_URL"):
        print("错误：未设置FEISHU_WEBHOOK_URL环境变量，无法发送飞书播报")
        sys.exit(1)

    if should_skip_after_fetch(database_url, date_obj, "飞书播报"):
        return

    notifier = create_feishu_notifier(database_url)
    try:
        result = notifier.send_report(date_obj)
        print("\n飞书播报发送完成：")
        print(f"  日期: {result['date']}")
        print(f"  数据完整: {'是' if result['is_complete'] else '否'}")
        print(f"  同花顺涨停: {result['hr_limit_up_count']} 条")
        print(f"  东财涨停: {result['em_limit_up_count']} 条")
        print(
            f"  Codex复盘: {'已附加' if result['daily_review_available'] else '尚未生成'}"
        )
        print("\n✅ 飞书播报完成")
    except Exception as e:
        print(f"错误：{e}")
        logging.exception("飞书播报失败")
        sys.exit(1)


def cmd_wiki(action: Optional[str] = None, arg: Optional[str] = None):
    """Wiki 知识库操作命令"""
    if not action:
        print("错误：缺少wiki子命令")
        print("用法: python main.py wiki [query|ingest|lint|build|pages] [arg]")
        sys.exit(1)

    try:
        wiki_agent = create_wiki_agent()

        if action == "query":
            if not arg:
                print("错误：query 需要提供问题文本")
                sys.exit(1)
            print(f"\n🔍 Wiki查询: {arg}\n")
            print(wiki_agent.query(arg))

        elif action == "ingest":
            if not arg:
                print(
                    "错误：ingest 需要提供 raw 文件路径，例如 raw/001-连板龙头交易体系.md"
                )
                sys.exit(1)
            print(f"\n📥 Wiki摄入: {arg}\n")
            print(wiki_agent.ingest(arg))

        elif action == "lint":
            print(wiki_agent.lint())

        elif action == "build":
            print(wiki_agent.build())

        elif action == "pages":
            pages = wiki_agent.pages()
            print(f"\n📚 Wiki页面（共 {len(pages)} 个）:\n")
            for page in pages:
                print(f"  - {page}")

        else:
            print(f"错误：未知wiki子命令 {action}")
            print("支持: query | ingest | lint | build | pages")
            sys.exit(1)

    except Exception as e:
        print(f"错误：{e}")
        logging.exception("Wiki命令执行失败")
        sys.exit(1)


def main():
    """主入口函数"""
    setup_logging()

    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    command = sys.argv[1]
    date_arg = sys.argv[2] if len(sys.argv) > 2 else None

    if command == "agent":
        args = sys.argv[2:]
        if not args:
            cmd_agent(None)
            return

        target_date = None
        if args[-1].replace("-", "").isdigit() and len(args[-1].replace("-", "")) == 8:
            target_date = args[-1]
            args = args[:-1]

        cmd_agent(" ".join(args), target_date)
        return

    if command == "wiki":
        wiki_action = sys.argv[2] if len(sys.argv) > 2 else None
        wiki_arg = " ".join(sys.argv[3:]) if len(sys.argv) > 3 else None
        cmd_wiki(wiki_action, wiki_arg)
        return

    if command == "codex-login":
        try:
            login_chatgpt_device_code()
        except Exception as e:
            print(f"错误：{e}")
            logging.exception("Codex登录失败")
            sys.exit(1)
        return

    if command in {"assess", "assess-ai", "ai-analyze"}:
        target_date, flags = parse_date_and_flags(sys.argv[2:])
        unknown_flags = flags - {"--force-ai"}
        if unknown_flags:
            print(f"错误：未知参数 {', '.join(sorted(unknown_flags))}")
            sys.exit(1)
        cmd_assess_daily_review(target_date, force_ai="--force-ai" in flags)
        return

    commands = {
        "fetch": cmd_fetch,
        "run": cmd_run,
        "schedule": cmd_schedule,
        "status": cmd_status,
        "notify-feishu": cmd_notify_feishu,
    }

    if command in commands:
        if command == "schedule":
            commands[command]()
        else:
            commands[command](date_arg)
    else:
        print(f"未知命令: {command}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
