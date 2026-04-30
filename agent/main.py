"""
股票选股及风控Agent系统主入口

Usage:
    python main.py fetch [date]             # 抓取数据
    python main.py assess [date]            # 风险评估（规则引擎）
    python main.py ai-analyze [date]        # AI智能分析
    python main.py assess-ai [date]         # 增强版风险评估（规则+AI）
    python main.py run [date]               # 完整流程（抓取+评估）
    python main.py schedule                 # 启动定时任务
    python main.py status [date]            # 查看数据状态
    python main.py wiki query "问题"        # 查询wiki知识库
    python main.py wiki ingest raw/xxx.md   # 摄入wiki原始素材
    python main.py wiki lint                # 检查wiki健康状态
    python main.py wiki build               # 重建wiki向量索引
    python main.py wiki pages               # 列出wiki页面

Environment Variables:
    DATABASE_URL: MySQL连接URL (required)
    STOCK_COOKIE: 数据抓取的cookie (optional)
    MOONSHOT_API_KEY: Moonshot API Key (AI分析功能需要)
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
    create_ai_analyzer,
    create_enhanced_risk_agent,
    create_risk_agent,
    create_wiki_agent,
)
from chain.stock.data import create_fetcher
from chain.stock.data.storage import StockDataStorage
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

        if status["is_complete"]:
            print("\n✅ 数据抓取完成")
        else:
            print("\n⚠️ 数据不完整")

    except Exception as e:
        print(f"错误：{e}")
        logging.exception("抓取数据失败")
        sys.exit(1)


def cmd_assess(target_date: Optional[str] = None):
    """风险评估命令（规则引擎）"""
    date_obj = parse_date(target_date)

    print(f"开始风险评估: {date_obj}")

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("错误：未设置DATABASE_URL环境变量")
        sys.exit(1)

    agent = create_risk_agent(database_url)

    try:
        result = agent.run_daily_assessment(date_obj)

        print("\n风险评估完成：")
        print(f"  评估股票数: {result['total_assessed']} 只")
        print(f"  成功保存: {result['saved_success']} 条")
        if result["saved_failed"] > 0:
            print(f"  保存失败: {result['saved_failed']} 条")

        if result["risk_distribution"]:
            print("\n风险分布：")
            for level, count in result["risk_distribution"].items():
                print(f"  {level}: {count} 只")

        print("\n✅ 风险评估完成")

    except Exception as e:
        print(f"错误：{e}")
        logging.exception("风险评估失败")
        sys.exit(1)


def cmd_ai_analyze(target_date: Optional[str] = None):
    """AI智能分析命令"""
    date_obj = parse_date(target_date)

    print(f"开始AI智能分析: {date_obj}")

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("错误：未设置DATABASE_URL环境变量")
        sys.exit(1)

    api_key = os.getenv("MOONSHOT_API_KEY")
    if not api_key:
        print("错误：未设置MOONSHOT_API_KEY环境变量，无法进行AI分析")
        print("请设置环境变量：export MOONSHOT_API_KEY='your-api-key'")
        sys.exit(1)

    analyzer = create_ai_analyzer(database_url)

    try:
        # 批量分析
        results = analyzer.batch_analyze(date_obj, min_continuous_days=2, limit=20)

        print("\nAI分析完成：")
        print(f"  分析股票数: {len(results)} 只")

        # 显示每只股票的简要分析结果
        print("\n分析结果摘要：")
        for result in results:
            print(f"\n  {result.code} {result.name}:")
            print(f"    AI风险评分: {result.ai_risk_score}/100")
            print(f"    投资建议: {result.ai_suggestion}")
            print(f"    概念热度: {result.concept_heat}")
            print(f"    市场情绪: {result.market_sentiment}")
            print(f"    置信度: {result.confidence}")

        print("\n✅ AI分析完成")

    except Exception as e:
        print(f"错误：{e}")
        logging.exception("AI分析失败")
        sys.exit(1)


def cmd_assess_enhanced(target_date: Optional[str] = None):
    """增强版风险评估命令（规则引擎 + AI）"""
    date_obj = parse_date(target_date)

    print(f"开始增强版风险评估: {date_obj}")
    print("=" * 60)
    print("📊 规则引擎 + 🤖 AI智能分析")
    print("=" * 60)

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("错误：未设置DATABASE_URL环境变量")
        sys.exit(1)

    agent = create_enhanced_risk_agent(database_url)

    # 检查是否有AI API Key
    use_ai = bool(os.getenv("MOONSHOT_API_KEY"))
    if not use_ai:
        print("⚠️ 警告：未设置MOONSHOT_API_KEY，将只使用规则引擎")
    else:
        print("✅ 已配置AI分析功能")

    try:
        result = agent.run_daily_assessment_enhanced(
            date_obj, min_continuous_days=2, use_ai=use_ai
        )

        print("\n增强版风险评估完成：")
        print(f"  评估股票数: {result['total_assessed']} 只")
        print(f"  成功保存: {result['saved_success']} 条")

        if result["saved_failed"] > 0:
            print(f"  保存失败: {result['saved_failed']} 条")

        # 分析方法分布
        print("\n分析方法分布：")
        print(
            f"  AI+规则混合分析: {result['analysis_method_distribution']['ai_analyzed']} 只"
        )
        print(
            f"  纯规则引擎分析: {result['analysis_method_distribution']['rule_only']} 只"
        )

        # AI成功数量
        if use_ai:
            print(f"  AI分析成功: {result['ai_success_count']} 只")

        # 风险分布
        if result["risk_distribution"]:
            print("\n风险分布：")
            for level, count in result["risk_distribution"].items():
                print(f"  {level}: {count} 只")

        print("\n✅ 增强版风险评估完成")

    except Exception as e:
        print(f"错误：{e}")
        logging.exception("增强版风险评估失败")
        sys.exit(1)


def cmd_run(target_date: Optional[str] = None):
    """运行完整流程"""
    date_obj = parse_date(target_date)

    print(f"开始完整流程: {date_obj}")
    print("=" * 50)

    # 1. 抓取数据
    cmd_fetch(target_date)

    print("\n" + "=" * 50)

    # 2. 风险评估
    cmd_assess(target_date)

    print("\n" + "=" * 50)
    print("✅ 所有任务完成")


def cmd_schedule():
    """启动定时任务"""
    print("启动定时任务调度器...")

    def notification(msg: str):
        print(f"\n[通知] {msg}")

    try:
        scheduler = create_scheduler(notification_callback=notification)

        # 设置定时任务
        # 数据抓取：每天 16:00
        scheduler.schedule_data_fetch(hour=16, minute=0)

        # 风险评估：每天 16:30
        scheduler.schedule_risk_assessment(hour=16, minute=30)

        print("\n已设置以下定时任务：")
        for job in scheduler.get_jobs():
            print(f"  - {job.name}: {job.trigger}")

        print("\n按 Ctrl+C 停止调度器")

        # 启动调度器
        scheduler.start()

        # 保持运行
        try:
            asyncio.get_event_loop().run_forever()
        except KeyboardInterrupt:
            print("\n正在停止调度器...")
            scheduler.shutdown()
            print("调度器已停止")

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

    if command == "wiki":
        wiki_action = sys.argv[2] if len(sys.argv) > 2 else None
        wiki_arg = " ".join(sys.argv[3:]) if len(sys.argv) > 3 else None
        cmd_wiki(wiki_action, wiki_arg)
        return

    commands = {
        "fetch": cmd_fetch,
        "assess": cmd_assess,
        "ai-analyze": cmd_ai_analyze,
        "assess-ai": cmd_assess_enhanced,
        "run": cmd_run,
        "schedule": cmd_schedule,
        "status": cmd_status,
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
