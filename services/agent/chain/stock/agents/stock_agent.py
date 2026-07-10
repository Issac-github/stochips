"""目标驱动的股票 Agent，编排抓取、Codex每日复盘和报告工具。"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Any, Callable, Dict, List, Optional

from langchain_openai import ChatOpenAI
from sqlalchemy.orm import Session

from ..config import config
from ..data import create_fetcher
from ..data.storage import StockDataStorage
from ..models.database import (
    BlockTop,
    ContinuousLimitUp,
    DailyMarketReview,
    LimitUpPool,
    get_session_maker,
    init_database,
)
from .daily_market_review_agent import create_daily_market_review_agent
from .wiki_agent import create_wiki_agent

logger = logging.getLogger(__name__)


@dataclass
class StockAgentStep:
    """Agent 计划中的单步动作。"""

    tool: str
    reason: str
    params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class StockAgentActionResult:
    """单个工具调用结果。"""

    tool: str
    status: str
    result: Any = None
    error: Optional[str] = None


@dataclass
class StockAgentRunResult:
    """Agent 一次运行的完整结果。"""

    goal: str
    date: str
    observation: Dict[str, Any]
    plan: List[StockAgentStep]
    actions: List[StockAgentActionResult]
    summary: str

    def to_dict(self) -> Dict[str, Any]:
        """转换成普通 dict，方便 CLI、API 或日志输出。"""
        return {
            "goal": self.goal,
            "date": self.date,
            "observation": self.observation,
            "plan": [step.__dict__ for step in self.plan],
            "actions": [action.__dict__ for action in self.actions],
            "summary": self.summary,
        }


class StockAgent:
    """
    股票分析 Agent。

    能力边界：
    - 观察：读取数据完整度、Codex复盘状态、热门板块概览。
    - 规划：根据 goal 决定是否抓取、生成Codex复盘、查询wiki、生成报告。
    - 行动：调用现有 fetcher/storage/Codex/wiki 工具。
    - 总结：把执行结果聚合成可读报告。
    """

    def __init__(
        self,
        database_url: str,
        cookie: Optional[str] = None,
        notification_callback: Optional[Callable[[str], None]] = None,
    ):
        self.database_url = database_url
        self.cookie = cookie or config.fetcher.ths_cookie
        self.notification_callback = notification_callback

        self.fetcher = create_fetcher(self.cookie)
        self.storage = StockDataStorage(database_url)
        self.daily_review_agent = None
        self.wiki_agent = create_wiki_agent()
        self.llm_planner = self._create_llm_planner()

        self.engine = init_database(database_url)
        self.Session = get_session_maker(self.engine)

        self.tools: Dict[str, Callable[..., Any]] = {
            "fetch_and_store_data": self.fetch_and_store_data,
            "run_daily_market_review": self.run_daily_market_review,
            "query_wiki": self.query_wiki,
            "generate_report": self.generate_report,
        }

    def run(
        self,
        goal: str,
        target_date: Optional[date] = None,
        *,
        auto_fetch: bool = True,
        use_ai: Optional[bool] = None,
        use_llm_planner: Optional[bool] = None,
        max_iterations: int = 6,
    ) -> StockAgentRunResult:
        """执行一次目标驱动的 Agent 任务。"""
        if not target_date:
            target_date = date.today()
        if use_ai is None:
            use_ai = config.ai.is_configured
        if use_llm_planner is None:
            use_llm_planner = bool(self.llm_planner)

        observation = self.observe(target_date)
        actions: List[StockAgentActionResult] = []
        plan: List[StockAgentStep] = []
        context: Dict[str, Any] = {
            "goal": goal,
            "date": target_date,
            "observation": observation,
            "actions": actions,
        }

        if use_llm_planner:
            for _ in range(max_iterations):
                next_steps = self.plan_with_llm(
                    goal,
                    observation,
                    actions,
                    auto_fetch=auto_fetch,
                    use_ai=use_ai,
                )
                if not next_steps:
                    break

                step = next_steps[0]
                plan.append(step)
                action = self.act(step, target_date, context)
                actions.append(action)

                if action.status == "success" and step.tool in {
                    "fetch_and_store_data",
                    "run_daily_market_review",
                }:
                    observation = self.observe(target_date)
                    context["observation"] = observation

                recovery_step = self.plan_recovery_step(
                    step, action, actions, use_ai=use_ai
                )
                if recovery_step:
                    plan.append(recovery_step)
                    recovery_action = self.act(recovery_step, target_date, context)
                    actions.append(recovery_action)
                    if recovery_action.status == "success":
                        observation = self.observe(target_date)
                        context["observation"] = observation

                if step.tool == "generate_report":
                    break

        if not plan:
            plan = self.plan(goal, observation, auto_fetch=auto_fetch, use_ai=use_ai)

        for step in plan[len(actions) :]:
            action = self.act(step, target_date, context)
            actions.append(action)

            if action.status == "success" and step.tool in {
                "fetch_and_store_data",
                "run_daily_market_review",
            }:
                observation = self.observe(target_date)
                context["observation"] = observation

        summary = self.summarize(goal, target_date, observation, plan, actions)
        if self.notification_callback:
            self.notification_callback(summary)

        return StockAgentRunResult(
            goal=goal,
            date=target_date.isoformat(),
            observation=observation,
            plan=plan,
            actions=actions,
            summary=summary,
        )

    def observe(self, target_date: date) -> Dict[str, Any]:
        """观察当天数据、Codex复盘和热点状态。"""
        data_status = self.storage.get_data_status(target_date)
        review_status = self._get_daily_review_status(target_date)
        market_snapshot = self._get_market_snapshot(target_date)

        return {
            "data_status": data_status,
            "review_status": review_status,
            "market_snapshot": market_snapshot,
        }

    def plan(
        self,
        goal: str,
        observation: Dict[str, Any],
        *,
        auto_fetch: bool = True,
        use_ai: bool = False,
    ) -> List[StockAgentStep]:
        """根据目标和观察结果生成执行计划。"""
        normalized_goal = goal.lower()
        data_status = observation["data_status"]

        wants_fetch = self._contains_any(
            normalized_goal, ["抓取", "更新", "同步", "fetch"]
        )
        wants_status = self._contains_any(normalized_goal, ["状态", "检查", "status"])
        wants_wiki = self._contains_any(
            normalized_goal, ["wiki", "知识", "解释", "查询"]
        )
        wants_report = self._contains_any(
            normalized_goal, ["报告", "总结", "复盘", "巡检", "机会", "report"]
        )
        wants_risk = self._contains_any(
            normalized_goal, ["风险", "评估", "风控", "巡检", "规避", "risk"]
        )
        wants_review = use_ai and self._contains_any(
            normalized_goal,
            [
                "ai",
                "智能",
                "深度",
                "综合",
                "机会",
                "巡检",
                "复盘",
                "研判",
                "风险",
                "风控",
            ],
        )

        plan: List[StockAgentStep] = []

        should_fetch = wants_fetch or (
            auto_fetch and not data_status["is_complete"] and not wants_status
        )
        if should_fetch:
            plan.append(
                StockAgentStep(
                    tool="fetch_and_store_data",
                    reason="目标需要最新数据，或观察到当天数据不完整。",
                )
            )

        if wants_review:
            plan.append(
                StockAgentStep(
                    tool="run_daily_market_review",
                    reason="目标需要市场研判，使用交易体系和每日事实材料生成Codex复盘。",
                    params={"force": should_fetch},
                )
            )

        if wants_wiki:
            plan.append(
                StockAgentStep(
                    tool="query_wiki",
                    reason="目标包含知识库查询或概念解释。",
                    params={"question": goal},
                )
            )

        if wants_report or wants_risk or wants_status:
            plan.append(
                StockAgentStep(
                    tool="generate_report",
                    reason="把观察和行动结果整理成可读结论。",
                )
            )

        if not plan:
            plan.append(
                StockAgentStep(
                    tool="generate_report",
                    reason="未识别到需要执行的外部动作，返回当前观察摘要。",
                )
            )

        return plan

    def plan_with_llm(
        self,
        goal: str,
        observation: Dict[str, Any],
        actions: List[StockAgentActionResult],
        *,
        auto_fetch: bool = True,
        use_ai: bool = False,
    ) -> List[StockAgentStep]:
        """使用 LLM 根据目标、观察和历史动作选择下一步工具。"""
        if not self.llm_planner:
            return self.plan(goal, observation, auto_fetch=auto_fetch, use_ai=use_ai)

        prompt = self._build_planner_prompt(
            goal, observation, actions, auto_fetch, use_ai
        )

        try:
            response = self.llm_planner.invoke(prompt)
            content = (
                response.content if hasattr(response, "content") else str(response)
            )
            raw_steps = self._parse_json_array(content)
            return self._normalize_llm_steps(raw_steps, actions)
        except Exception as exc:
            logger.warning("LLM planner failed, fallback to rule planner: %s", exc)
            rule_steps = self.plan(
                goal, observation, auto_fetch=auto_fetch, use_ai=use_ai
            )
            return self._remaining_steps(rule_steps, actions)

    def plan_recovery_step(
        self,
        failed_step: StockAgentStep,
        action: StockAgentActionResult,
        actions: List[StockAgentActionResult],
        *,
        use_ai: bool,
    ) -> Optional[StockAgentStep]:
        """为失败动作生成一个保守恢复步骤。"""
        if action.status == "success":
            return None

        succeeded_tools = {item.tool for item in actions if item.status == "success"}
        if (
            failed_step.tool != "generate_report"
            and "generate_report" not in succeeded_tools
        ):
            return StockAgentStep(
                tool="generate_report",
                reason="上一步执行失败，先输出当前可用信息和失败原因。",
            )

        return None

    def act(
        self,
        step: StockAgentStep,
        target_date: date,
        context: Dict[str, Any],
    ) -> StockAgentActionResult:
        """执行计划中的一步。"""
        tool = self.tools[step.tool]
        params = dict(step.params)
        params.setdefault("target_date", target_date)

        if step.tool == "generate_report":
            params["context"] = context
        elif step.tool == "run_daily_market_review":
            fetched_data = any(
                action.tool == "fetch_and_store_data" and action.status == "success"
                for action in context["actions"]
            )
            if fetched_data:
                params["force"] = True

        try:
            result = tool(**params)
            return StockAgentActionResult(
                tool=step.tool, status="success", result=result
            )
        except Exception as exc:
            logger.exception("StockAgent tool failed: %s", step.tool)
            return StockAgentActionResult(
                tool=step.tool, status="failed", error=str(exc)
            )

    def fetch_and_store_data(self, target_date: date) -> Dict[str, Any]:
        """抓取并保存当天所有数据。"""
        date_str = target_date.strftime("%Y%m%d")
        data = self.fetcher.fetch_all_data(date_str)
        results = self.storage.save_all_data(data, target_date)
        return {
            "date": date_str,
            "results": results,
            "errors": data.get("errors", []),
        }

    def run_daily_market_review(
        self,
        target_date: date,
        force: bool = False,
    ) -> Dict[str, Any]:
        """Generate or reuse the qualitative daily Codex review."""
        if self.daily_review_agent is None:
            self.daily_review_agent = create_daily_market_review_agent(
                self.database_url
            )
        return self.daily_review_agent.run(target_date, force=force).to_dict()

    def close(self) -> None:
        """Release the Codex app-server if this Agent started one."""
        if self.daily_review_agent is not None:
            self.daily_review_agent.close()
            self.daily_review_agent = None

    def query_wiki(self, target_date: date, question: str) -> str:
        """查询交易知识库。target_date 保留给统一工具签名使用。"""
        del target_date
        return self.wiki_agent.query(question)

    def generate_report(
        self,
        target_date: date,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """生成结构化巡检报告。"""
        observation = (
            context.get("observation") if context else self.observe(target_date)
        )
        return {
            "date": target_date.isoformat(),
            "data_status": observation["data_status"],
            "review_status": self._get_daily_review_status(target_date),
            "market_snapshot": observation["market_snapshot"],
            "action_summary": (
                self._summarize_actions(context.get("actions", [])) if context else []
            ),
        }

    def summarize(
        self,
        goal: str,
        target_date: date,
        observation: Dict[str, Any],
        plan: List[StockAgentStep],
        actions: List[StockAgentActionResult],
    ) -> str:
        """输出面向人的运行摘要。"""
        data_status = observation["data_status"]
        review_status = self._get_daily_review_status(target_date)
        failed_actions = [action for action in actions if action.status != "success"]

        lines = [
            f"StockAgent 完成目标：{goal}",
            f"日期：{target_date.isoformat()}",
            "",
            "计划：",
        ]
        lines.extend(f"- {step.tool}: {step.reason}" for step in plan)

        lines.extend(
            [
                "",
                "数据状态：",
                f"- 连板天梯 {data_status['continuous_limit_up']} 条",
                f"- 最强风口 {data_status['block_top']} 条",
                f"- 涨停强度 {data_status['limit_up_pool']} 条",
                f"- 东财涨停池 {data_status['eastmoney_zt_pool']} 条",
                f"- 完整性：{'完整' if data_status['is_complete'] else '不完整'}",
                "",
                "Codex每日市场复盘：",
                f"- 状态：{'已生成' if review_status['available'] else '尚未生成'}",
            ]
        )

        if review_status["available"]:
            lines.append(f"- 模型：{review_status['model']}")
            lines.append(f"- 来源：{review_status['provider']}")

        if failed_actions:
            lines.append("")
            lines.append("失败动作：")
            lines.extend(
                f"- {action.tool}: {action.error}" for action in failed_actions
            )

        return "\n".join(lines)

    def _get_daily_review_status(self, target_date: date) -> Dict[str, Any]:
        session: Session = self.Session()
        try:
            record = (
                session.query(DailyMarketReview)
                .filter(DailyMarketReview.date == target_date)
                .one_or_none()
            )
            return {
                "available": record is not None,
                "provider": record.provider if record else "",
                "model": (record.model or "default") if record else "",
            }
        finally:
            session.close()

    def _get_market_snapshot(self, target_date: date) -> Dict[str, Any]:
        session: Session = self.Session()
        try:
            top_blocks = (
                session.query(BlockTop)
                .filter(BlockTop.date == target_date)
                .order_by(BlockTop.stock_count.desc())
                .limit(5)
                .all()
            )
            top_continuous = (
                session.query(ContinuousLimitUp)
                .filter(ContinuousLimitUp.date == target_date)
                .order_by(ContinuousLimitUp.continuous_days.desc())
                .limit(5)
                .all()
            )
            weak_boards = (
                session.query(LimitUpPool)
                .filter(LimitUpPool.date == target_date)
                .order_by(LimitUpPool.open_count.desc())
                .limit(5)
                .all()
            )

            return {
                "top_blocks": [
                    {
                        "block_name": item.block_name,
                        "stock_count": item.stock_count,
                        "leading_stock": item.leading_stock,
                        "leading_stock_name": item.leading_stock_name,
                    }
                    for item in top_blocks
                ],
                "top_continuous": [
                    {
                        "code": item.code,
                        "name": item.name,
                        "continuous_days": item.continuous_days,
                    }
                    for item in top_continuous
                ],
                "weak_boards": [
                    {
                        "code": item.code,
                        "name": item.name,
                        "open_count": item.open_count,
                        "turnover_rate": self._to_float(item.turnover_rate),
                    }
                    for item in weak_boards
                ],
            }
        finally:
            session.close()

    def _summarize_actions(
        self, actions: List[StockAgentActionResult]
    ) -> List[Dict[str, str]]:
        return [
            {
                "tool": action.tool,
                "status": action.status,
                "error": action.error or "",
            }
            for action in actions
        ]

    def _contains_any(self, text: str, needles: List[str]) -> bool:
        return any(needle in text for needle in needles)

    def _to_float(self, value: Any) -> Optional[float]:
        if value is None:
            return None
        if isinstance(value, Decimal):
            return float(value)
        return float(value)

    def _create_llm_planner(self) -> Optional[ChatOpenAI]:
        if not config.ai.api_key:
            return None

        return ChatOpenAI(
            model=config.ai.model,
            api_key=config.ai.api_key,
            base_url=config.ai.base_url,
            temperature=0,
            timeout=config.ai.timeout,
        )

    def _build_planner_prompt(
        self,
        goal: str,
        observation: Dict[str, Any],
        actions: List[StockAgentActionResult],
        auto_fetch: bool,
        use_ai: bool,
    ) -> str:
        action_history = [action.__dict__ for action in actions]
        payload = {
            "goal": goal,
            "observation": observation,
            "actions": action_history,
            "options": {
                "auto_fetch": auto_fetch,
                "use_ai": use_ai,
            },
            "available_tools": {
                "fetch_and_store_data": "抓取并保存指定日期的股票数据。",
                "run_daily_market_review": "读取交易体系和每日行情材料，生成Codex市场复盘。",
                "query_wiki": "查询交易知识库，必须提供 question 参数。",
                "generate_report": "根据观察和动作历史生成结构化巡检报告，通常作为最后一步。",
            },
        }

        return f"""你是股票分析系统的任务规划器。请只决定下一步要调用的工具，不要输出解释性文本。

规则：
1. 只输出 JSON 数组，数组元素格式为 {{"tool": "...", "reason": "...", "params": {{...}}}}。
2. 每次最多输出 1 个工具；如果任务已完成，输出 []。
3. 不要重复调用已经成功执行过的非报告工具。
4. 如果当天数据不完整且目标不是单纯查看状态，优先抓取数据。
5. 风险、风控、巡检、复盘类目标在 use_ai=true 时生成每日Codex市场复盘，不做程序评分。
6. 报告、总结、复盘、巡检类目标最后调用 generate_report。
7. wiki、知识、解释、查询类目标调用 query_wiki，并把原始目标作为 question。
8. 如果上一动作失败，选择可降级工具或 generate_report。

输入：
{json.dumps(payload, ensure_ascii=False, default=str)}
"""

    def _parse_json_array(self, content: str) -> List[Dict[str, Any]]:
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError:
            start = content.find("[")
            end = content.rfind("]")
            if start == -1 or end == -1 or end < start:
                raise
            parsed = json.loads(content[start : end + 1])

        if not isinstance(parsed, list):
            raise ValueError("LLM planner output must be a JSON array")
        return parsed

    def _normalize_llm_steps(
        self,
        raw_steps: List[Dict[str, Any]],
        actions: List[StockAgentActionResult],
    ) -> List[StockAgentStep]:
        succeeded_tools = {
            action.tool for action in actions if action.status == "success"
        }
        normalized: List[StockAgentStep] = []

        for raw_step in raw_steps[:1]:
            tool = raw_step.get("tool")
            if tool not in self.tools:
                continue
            if tool != "generate_report" and tool in succeeded_tools:
                continue

            params = raw_step.get("params") or {}
            if not isinstance(params, dict):
                params = {}

            normalized.append(
                StockAgentStep(
                    tool=tool,
                    reason=raw_step.get("reason") or "LLM planner selected this tool.",
                    params=params,
                )
            )

        return normalized

    def _remaining_steps(
        self,
        steps: List[StockAgentStep],
        actions: List[StockAgentActionResult],
    ) -> List[StockAgentStep]:
        succeeded_tools = {
            action.tool for action in actions if action.status == "success"
        }
        return [
            step
            for step in steps
            if step.tool == "generate_report" or step.tool not in succeeded_tools
        ]


def create_stock_agent(
    database_url: Optional[str] = None,
    cookie: Optional[str] = None,
    notification_callback: Optional[Callable[[str], None]] = None,
) -> StockAgent:
    """工厂函数：创建目标驱动 StockAgent。"""
    if not database_url:
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            raise ValueError("请提供database_url或设置DATABASE_URL环境变量")

    return StockAgent(
        database_url, cookie=cookie, notification_callback=notification_callback
    )
