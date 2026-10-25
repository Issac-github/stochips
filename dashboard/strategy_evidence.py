"""Bounded, read-only evidence coverage; no trading-pattern classification."""

import json
from pathlib import Path
import re

from sqlalchemy import case, func, or_, select
from chain.stock.models.database import (
    BlockTopStock,
    ContinuousLimitUp,
    EastmoneyZTPool,
    LimitUpPool,
    LowerLimitPool,
)

CATALOG = json.loads(
    Path(__file__).with_name("strategy-concepts.json").read_text(encoding="utf-8")
)
SOURCES = (
    (
        ContinuousLimitUp,
        "连板池",
        (ContinuousLimitUp.limit_up_price,),
        ContinuousLimitUp.volume,
    ),
    (
        LimitUpPool,
        "同花顺涨停池",
        (LimitUpPool.limit_up_price, LimitUpPool.latest_price),
        None,
    ),
    (
        EastmoneyZTPool,
        "东财涨停池",
        (EastmoneyZTPool.latest_price,),
        EastmoneyZTPool.volume,
    ),
    (BlockTopStock, "板块成员", (BlockTopStock.latest_price,), None),
    (LowerLimitPool, "跌停池", (LowerLimitPool.latest_price,), None),
)


def read_coverage(sessions, target):
    result = []
    with sessions() as session:
        for model, label, prices, volume in SOURCES:
            expressions = [
                func.count(),
                func.count(func.distinct(model.date)),
                func.count(func.distinct(model.code)),
                func.min(model.date),
                func.max(model.date),
                func.count(case((or_(*(column > 0 for column in prices)), 1))),
            ]
            if volume is not None:
                expressions.append(func.count(case((volume > 0, 1))))
            row = session.execute(
                select(*expressions).select_from(model).where(model.date <= target)
            ).one()
            result.append(
                dict(
                    source=model.__tablename__,
                    label=label,
                    rows=row[0],
                    dates=row[1],
                    stocks=row[2],
                    first_date=row[3].isoformat() if row[3] else None,
                    last_date=row[4].isoformat() if row[4] else None,
                    positive_price_rows=row[5],
                    positive_volume_rows=row[6] if volume is not None else None,
                )
            )
    return result


def capability(key, label, state, detail):
    return dict(key=key, label=label, state=state, detail=detail)


def build_capabilities(report, coverage):
    volume_sources = [
        item for item in coverage if item["positive_volume_rows"] is not None
    ]
    volume_rows = sum(item["positive_volume_rows"] for item in volume_sources)
    volume_samples = sum(item["rows"] for item in volume_sources)
    price_rows = sum(item["positive_price_rows"] for item in coverage)
    metrics = report["limit_up_pool_metrics"]
    first = sum(bool(item.get("first_limit_up_time")) for item in metrics)
    last = sum(bool(item.get("last_limit_up_time")) for item in metrics)
    boards = len(report["top_blocks"]) + len(report["eastmoney_industries"])
    return {
        "daily_bars": capability(
            "daily_bars",
            "连续日线 OHLCV",
            "not_integrated",
            "看板尚未接入每股逐日开高低收量序列；涨停/连板池中的离散记录不能代替连续日线。",
        ),
        "auction": capability(
            "auction",
            "集合竞价",
            "not_integrated",
            "未接入竞价价格、成交量与封单变化；收盘一字板记录不能证明竞价抢筹。",
        ),
        "intraday": capability(
            "intraday",
            "分钟/逐笔分时",
            "not_integrated",
            "未接入分钟或逐笔序列，无法核对开盘首段、开板持续时间及承接过程。",
        ),
        "volume": capability(
            "volume",
            "历史成交量",
            "partial" if volume_rows else "missing",
            f"截至所选日期，连板池/东财涨停池 {volume_samples} 条观测中有 {volume_rows} 条正成交量。"
            + (
                "仅为池内样本，未核验单位与非涨停日连续性，不能据此确认历史天量。"
                if volume_rows
                else "缺少可用成交量，不能用换手率或成交额替代。"
            ),
        ),
        "prices": capability(
            "prices",
            "池内历史价格",
            "partial" if price_rows else "missing",
            f"历史来源中 {price_rows} 条记录含正价格；来源可能重叠，仅为池内价格，不是完整K线或平台边界。",
        ),
        "ladder": capability(
            "ladder",
            "当日连板梯队",
            "available" if report["continuous_distribution"] else "missing",
            f"当日连板分布 {len(report['continuous_distribution'])} 个高度层次，核心连板 {len(report['top_stocks'])} 条；高度不等于龙头身份。",
        ),
        "boards": capability(
            "boards",
            "板块与行业事实",
            "available" if boards else "missing",
            f"当日板块/行业 {boards} 条来源记录，成员可能重叠；不自动判定主线。",
        ),
        "feedback": capability(
            "feedback",
            "昨日高标反馈",
            "available" if report["previous_high_feedback"] else "missing",
            f"当日 {len(report['previous_high_feedback'])} 条昨日高标反馈；未进入涨停池不等于跌停。",
        ),
        "assists": capability(
            "assists",
            "收盘助攻候选",
            "available" if report["leader_assists"] else "missing",
            f"当日 {len(report['leader_assists'])} 条回溯候选，不证明盘中有效性或因果带动。",
        ),
        "seals": capability(
            "seals",
            "当日封板时间",
            (
                "available"
                if metrics and first == last == len(metrics)
                else "partial" if first or last else "missing"
            ),
            f"涨停池指标 {len(metrics)} 条，其中首次封板时间 {first} 条、末次封板时间 {last} 条；跨日加速尚未计算。",
        ),
    }


def assess_concept(concept, report, capabilities):
    counts = [dict(dataset=key, rows=len(report[key])) for key in concept["sources"]]
    records = sum(item["rows"] for item in counts)
    codes = set()
    for source in concept["sources"]:
        for row in report[source]:
            stock = row.get("stock", {}) if source == "leader_assists" else row
            code = stock.get("code")
            if isinstance(code, str) and re.fullmatch(r"[0-9]{6}", code):
                codes.add(code)
    requirements = [capabilities[key] for key in concept["requirements"]]
    kind = concept["kind"]
    if kind == "manual":
        status, explanation = (
            "manual",
            "风险判断和处理计划由人工记录；下方提供可核对的来源事实。",
        )
    elif kind == "fact":
        status = "facts_available" if records else "no_observations"
        explanation = (
            "已有相关事实记录，概念身份仍未自动判定。"
            if records
            else "所选日期没有关联事实记录，请对照抓取状态；不代表市场没有该模式。"
        )
    elif kind == "candidate":
        status = "candidate" if codes else "no_observations"
        explanation = (
            "现有报告生成了关联候选，仍需核对角色与有效性。"
            if codes
            else "当日没有关联候选记录，不能据此认定模式不成立。"
        )
    else:
        status = (
            "data_gap"
            if any(item["state"] != "available" for item in requirements)
            else "not_implemented"
        )
        explanation = "完整模式识别尚未实现；关联观测和前高记录不等于该模式匹配。"
    return dict(
        key=concept["key"],
        status=status,
        kind=kind,
        explanation=explanation,
        source_counts=counts,
        stock_count=len(codes),
        requirements=requirements,
    )


def build_strategy_evidence(sessions, target, report):
    coverage = read_coverage(sessions, target)
    capabilities = build_capabilities(report, coverage)
    return dict(
        date=target.isoformat(),
        coverage=coverage,
        concepts=[
            assess_concept(concept, report, capabilities)
            for concept in CATALOG["concepts"]
        ],
    )
