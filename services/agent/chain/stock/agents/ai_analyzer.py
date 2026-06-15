"""
AI智能分析模块

使用LLM（Moonshot/Kimi）深度分析股票数据：
1. 涨停原因分析
2. 概念热度评估
3. 市场情绪分析
4. 个股基本面评估
5. 技术面分析
6. 生成投资建议报告
"""

import json
import logging
from datetime import date, datetime
from decimal import Decimal
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

from sqlalchemy.orm import Session, sessionmaker

# LangChain imports
from langchain_openai import ChatOpenAI

from ..config import config
from ..models.database import (
    ContinuousLimitUp,
    LimitUpPool,
    BlockTop,
    get_session_maker,
    init_database,
)

logger = logging.getLogger(__name__)

ALLOWED_AI_SUGGESTIONS = {"机会", "观望", "谨慎", "规避"}
SUGGESTION_ALIASES = {
    "强烈推荐": "机会",
    "推荐": "机会",
    "买入": "机会",
    "关注": "观望",
    "持有": "观望",
    "谨慎": "谨慎",
    "观望": "观望",
    "回避": "规避",
    "规避": "规避",
    "卖出": "规避",
}


class Sentiment(Enum):
    """市场情绪"""
    VERY_POSITIVE = "非常乐观"
    POSITIVE = "乐观"
    NEUTRAL = "中性"
    NEGATIVE = "悲观"
    VERY_NEGATIVE = "非常悲观"


class ConceptHeat(Enum):
    """概念热度"""
    HOT = "热点"
    WARM = "温热"
    COLD = "冷门"


@dataclass
class AIAnalysisResult:
    """AI分析结果"""
    code: str
    name: str
    date: date

    # 分析维度
    limit_up_reason_analysis: str  # 涨停原因分析
    concept_heat: str  # 概念热度
    market_sentiment: str  # 市场情绪
    fundamentalAssessment: str  # 基本面评估
    technical_analysis: str  # 技术面分析

    # 综合评估
    ai_risk_score: float  # AI风险评分(0-100)
    ai_suggestion: str  # AI建议
    confidence: float  # 置信度(0-1)

    # 详细报告
    analysis_report: str  # 完整分析报告
    key_factors: List[Dict[str, Any]]  # 关键因子

    # 对比分析
    similar_cases: List[Dict[str, Any]]  # 相似案例
    history_pattern: str  # 历史模式


class AIStockAnalyzer:
    """
    AI股票分析器

    使用LLM进行多维度分析，结合规则引擎提供智能投资建议
    """

    def __init__(self, database_url: str, api_key: Optional[str] = None):
        """
        初始化AI分析器

        Args:
            database_url: MySQL连接URL
            api_key: Moonshot API Key，默认从环境变量读取
        """
        self.database_url = database_url
        self.engine = None
        self.Session: Optional[sessionmaker[Session]] = None

        # 初始化LLM
        self.api_key = api_key or config.ai.api_key
        if not self.api_key:
            logger.warning("MOONSHOT_API_KEY未设置，AI分析功能将不可用")
            self.llm = None
        else:
            self.llm = ChatOpenAI(
                model=config.ai.model,
                api_key=self.api_key,
                base_url=config.ai.base_url,
                temperature=config.ai.temperature,
                max_tokens=config.ai.max_tokens,
                timeout=config.ai.timeout,
            )

    def _init_db(self):
        """延迟初始化数据库"""
        if not self.Session:
            self.engine = init_database(self.database_url)
            self.Session = get_session_maker(self.engine)

    def _get_session(self) -> Session:
        """获取数据库会话。"""
        self._init_db()
        session_factory = self.Session
        if not session_factory:
            raise RuntimeError("数据库会话初始化失败")
        return session_factory()

    def _get_stock_data(self, code: str, target_date: date) -> Dict[str, Any]:
        """
        获取股票完整数据

        Args:
            code: 股票代码
            target_date: 日期

        Returns:
            股票完整数据字典
        """
        session = self._get_session()

        try:
            # 查询连板数据
            continuous = session.query(ContinuousLimitUp).filter(
                ContinuousLimitUp.date == target_date,
                ContinuousLimitUp.code == code
            ).first()

            # 查询涨停强度数据
            pool = session.query(LimitUpPool).filter(
                LimitUpPool.date == target_date,
                LimitUpPool.code == code
            ).first()

            # 查询所属板块
            block_data = None
            if pool and pool.block_name:
                block_data = session.query(BlockTop).filter(
                    BlockTop.date == target_date,
                    BlockTop.block_name == pool.block_name
                ).first()

            # 查询历史数据（近5日）
            history = session.query(ContinuousLimitUp).filter(
                ContinuousLimitUp.code == code,
                ContinuousLimitUp.date < target_date
            ).order_by(ContinuousLimitUp.date.desc()).limit(5).all()

            return {
                'continuous': continuous,
                'pool': pool,
                'block': block_data,
                'history': history
            }

        finally:
            session.close()

    def _build_analysis_prompt(self, data: Dict[str, Any]) -> str:
        """
        构建分析Prompt

        Args:
            data: 股票数据

        Returns:
            Prompt字符串
        """
        continuous = data['continuous']
        pool = data['pool']
        block = data['block']
        history = data['history']

        # 基础信息
        code = continuous.code if continuous else pool.code
        name = continuous.name if continuous else pool.name
        continuous_days = continuous.continuous_days if continuous else 1

        # 涨停强度信息
        strength_info = ""
        if pool:
            strength_info = f"""
涨停强度数据：
- 最新价：{pool.latest_price}
- 涨停价：{pool.limit_up_price}
- 涨停类型：{pool.limit_up_type}
- 涨停时间：{pool.limit_up_time}
- 封单强度：{pool.strength}
- 封单金额：{pool.board_amount}万元
- 换手率：{pool.turnover_rate}%
- 量比：{pool.volume_ratio}
- 流通市值：{pool.market_value}亿元
- 市盈率：{pool.pe_ratio}
- 市净率：{pool.pb_ratio}
- 涨停原因：{pool.reason or '未提供'}
- 所属概念：{pool.concept or '未提供'}
- 所属板块：{pool.block_name or '未提供'}
"""

        # 板块信息
        block_info = ""
        if block:
            block_info = f"""
板块热度数据：
- 板块名称：{block.block_name}
- 涨停家数：{block.stock_count}只
- 板块涨跌幅：{block.change_percent}%
- 持续天数：{block.continuous_days}天
- 龙头股：{block.leading_stock_name}({block.leading_stock})
"""

        # 历史数据
        history_info = ""
        if history:
            history_info = "历史连板记录（近5日）：\n"
            for h in history:
                history_info += f"- {h.date}: 连板{h.continuous_days}天\n"

        prompt = f"""你是一位专业的股票分析师，擅长分析涨停股票的投资价值和风险。

请分析以下股票：

【基础信息】
- 股票代码：{code}
- 股票名称：{name}
- 当前连板天数：{continuous_days}天

{strength_info}
{block_info}
{history_info}

请从以下维度进行分析，并输出JSON格式结果：

1. **涨停原因分析**：分析涨停原因的可信度和持续性
2. **概念热度评估**：评估所属概念的市场热度（热点/温热/冷门）
3. **市场情绪判断**：判断当前市场情绪（非常乐观/乐观/中性/悲观/非常悲观）
4. **基本面评估**：基于PE、PB、市值等指标评估基本面
5. **技术面分析**：分析封单强度、换手率、量比等技术信号
6. **AI风险评分**：0-100分，分数越高风险越大
7. **风险建议**：明确给出建议（机会/观望/谨慎/规避），不要输出直接荐股或买卖指令
8. **关键因子**：列出3-5个最关键的影响因子
9. **相似案例**：描述历史上类似走势的案例
10. **明日预判**：预测明日可能的走势

输出格式（必须是合法的JSON）：
{{
    "limit_up_reason_analysis": "分析内容...",
    "concept_heat": "热点/温热/冷门",
    "market_sentiment": "非常乐观/乐观/中性/悲观/非常悲观",
    "fundamental_assessment": "基本面评估...",
    "technical_analysis": "技术面分析...",
    "ai_risk_score": 75.5,
    "ai_suggestion": "机会/观望/谨慎/规避",
    "confidence": 0.85,
    "key_factors": [
        {{"factor": "概念热度", "impact": "正面", "weight": 0.3}},
        {{"factor": "封单强度", "impact": "负面", "weight": 0.25}}
    ],
    "similar_cases": "历史上类似走势...",
    "tomorrow_prediction": "明日可能..."
}}

要求：
1. 必须输出合法JSON，不要包含markdown格式
2. 分析要客观、专业，只基于提供的数据；数据不足时写“无足够数据”，不要编造历史案例
3. AI风险评分要综合考虑所有因素
4. 风险建议只能是：机会、观望、谨慎、规避
"""

        return prompt

    @staticmethod
    def _clamp_float(value: Any, default: float, min_value: float, max_value: float) -> float:
        try:
            number = float(value)
        except (TypeError, ValueError):
            number = default
        return max(min_value, min(max_value, number))

    @staticmethod
    def normalize_suggestion(value: Any) -> str:
        """把模型可能输出的荐股话术收敛到系统风险建议枚举。"""
        if value is None:
            return "观望"
        text = str(value).strip()
        if text in ALLOWED_AI_SUGGESTIONS:
            return text
        return SUGGESTION_ALIASES.get(text, "观望")

    @classmethod
    def parse_analysis_json(cls, content: Any) -> Dict[str, Any]:
        """解析并归一化LLM返回，避免上层直接面对不稳定JSON。"""
        if not isinstance(content, str):
            raise ValueError("LLM返回内容不是文本")

        try:
            result_json = json.loads(content)
        except json.JSONDecodeError:
            json_start = content.find('{')
            json_end = content.rfind('}')
            if json_start == -1 or json_end == -1 or json_end <= json_start:
                raise ValueError("无法解析LLM返回的JSON")
            try:
                result_json = json.loads(content[json_start:json_end + 1])
            except json.JSONDecodeError as exc:
                raise ValueError("无法解析LLM返回的JSON") from exc

        if not isinstance(result_json, dict):
            raise ValueError("LLM返回JSON必须是对象")

        result_json["ai_risk_score"] = cls._clamp_float(
            result_json.get("ai_risk_score"),
            50.0,
            0.0,
            100.0,
        )
        result_json["confidence"] = cls._clamp_float(
            result_json.get("confidence"),
            0.5,
            0.0,
            1.0,
        )
        result_json["ai_suggestion"] = cls.normalize_suggestion(
            result_json.get("ai_suggestion")
        )

        factors = result_json.get("key_factors", [])
        if not isinstance(factors, list):
            factors = []
        result_json["key_factors"] = [
            factor for factor in factors if isinstance(factor, dict)
        ]

        return result_json

    def _invoke_llm_with_retry(self, messages: List[Dict[str, str]]):
        """带有限重试的LLM调用，避免偶发网络错误直接吞掉整只股票。"""
        last_error: Optional[Exception] = None
        attempts = max(1, config.ai.max_retries + 1)
        for attempt in range(1, attempts + 1):
            try:
                return self.llm.invoke(messages)
            except Exception as exc:
                last_error = exc
                logger.warning("AI调用失败，第%s/%s次: %s", attempt, attempts, exc)
        raise RuntimeError(f"AI调用失败: {last_error}") from last_error

    def analyze_stock(
        self,
        code: str,
        name: str,
        target_date: Optional[date] = None
    ) -> Optional[AIAnalysisResult]:
        """
        AI分析单只股票

        Args:
            code: 股票代码
            name: 股票名称
            target_date: 分析日期

        Returns:
            AI分析结果
        """
        if not target_date:
            target_date = date.today()

        if not self.llm:
            logger.warning("LLM未初始化，无法执行AI分析")
            return None

        logger.info(f"开始AI分析: {code} {name} ({target_date})")

        try:
            # 获取股票数据
            data = self._get_stock_data(code, target_date)

            if not data['continuous'] and not data['pool']:
                logger.warning(f"未找到股票数据: {code}")
                return None

            # 构建Prompt
            prompt_text = self._build_analysis_prompt(data)

            # 调用LLM
            messages = [
                {"role": "system", "content": "你是一位专业的A股涨停股票风险分析师。只做风险研判，不给直接买卖指令。输出必须是合法JSON。"},
                {"role": "user", "content": prompt_text}
            ]

            response = self._invoke_llm_with_retry(messages)
            content = response.content

            # 解析并归一化JSON
            result_json = self.parse_analysis_json(content)

            # 构建结果
            result = AIAnalysisResult(
                code=code,
                name=name,
                date=target_date,
                limit_up_reason_analysis=result_json.get('limit_up_reason_analysis', ''),
                concept_heat=result_json.get('concept_heat', ''),
                market_sentiment=result_json.get('market_sentiment', ''),
                fundamentalAssessment=result_json.get('fundamental_assessment', ''),
                technical_analysis=result_json.get('technical_analysis', ''),
                ai_risk_score=result_json.get('ai_risk_score', 50.0),
                ai_suggestion=result_json.get('ai_suggestion', '观望'),
                confidence=result_json.get('confidence', 0.5),
                analysis_report=self._generate_report(result_json),
                key_factors=result_json.get('key_factors', []),
                similar_cases=[{"description": result_json.get('similar_cases', '')}],
                history_pattern=result_json.get('tomorrow_prediction', '')
            )

            logger.info(f"AI分析完成: {code}, 风险评分: {result.ai_risk_score}, 建议: {result.ai_suggestion}")
            return result

        except Exception as e:
            logger.error(f"AI分析失败 {code}: {e}")
            return None

    def _generate_report(self, result_json: Dict) -> str:
        """生成格式化的分析报告"""
        report = f"""
【AI智能分析报告】

一、涨停原因分析
{result_json.get('limit_up_reason_analysis', 'N/A')}

二、概念热度评估
热度等级：{result_json.get('concept_heat', 'N/A')}

三、市场情绪判断
当前情绪：{result_json.get('market_sentiment', 'N/A')}

四、基本面评估
{result_json.get('fundamental_assessment', 'N/A')}

五、技术面分析
{result_json.get('technical_analysis', 'N/A')}

六、综合评估
- AI风险评分：{result_json.get('ai_risk_score', 'N/A')}/100
- 投资建议：{result_json.get('ai_suggestion', 'N/A')}
- 置信度：{result_json.get('confidence', 'N/A')}

七、关键影响因子
"""

        factors = result_json.get('key_factors', [])
        for i, factor in enumerate(factors, 1):
            report += f"{i}. {factor.get('factor', '')}: {factor.get('impact', '')} (权重{factor.get('weight', 0)})\n"

        report += f"""
八、历史相似案例
{result_json.get('similar_cases', 'N/A')}

九、明日走势预判
{result_json.get('tomorrow_prediction', 'N/A')}
"""

        return report

    def batch_analyze(
        self,
        target_date: Optional[date] = None,
        min_continuous_days: int = 2,
        limit: int = 50
    ) -> List[AIAnalysisResult]:
        """
        批量分析股票

        Args:
            target_date: 分析日期
            min_continuous_days: 最小连板天数
            limit: 最大分析数量

        Returns:
            分析结果列表
        """
        if not target_date:
            target_date = date.today()

        session = self._get_session()

        try:
            # 获取符合条件的股票
            stocks = session.query(ContinuousLimitUp).filter(
                ContinuousLimitUp.date == target_date,
                ContinuousLimitUp.continuous_days >= min_continuous_days
            ).order_by(
                ContinuousLimitUp.continuous_days.desc(),
                ContinuousLimitUp.code.asc(),
            ).limit(limit).all()

            logger.info(f"批量AI分析: {len(stocks)}只股票")

            results = []
            for stock in stocks:
                try:
                    result = self.analyze_stock(stock.code, stock.name, target_date)
                    if result:
                        results.append(result)
                except Exception as e:
                    logger.error(f"分析股票失败 {stock.code}: {e}")
                    continue

            logger.info(f"批量AI分析完成: 成功{len(results)}只")
            return results

        finally:
            session.close()


def create_ai_analyzer(database_url: Optional[str] = None) -> AIStockAnalyzer:
    """
    工厂函数：创建AI分析器

    Args:
        database_url: MySQL连接URL，默认从环境变量读取

    Returns:
        AIStockAnalyzer实例
    """
    if not database_url:
        database_url = config.database.url
        if not database_url:
            raise ValueError("请提供database_url或设置DATABASE_URL环境变量")

    return AIStockAnalyzer(database_url)
