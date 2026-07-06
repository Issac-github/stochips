"""
风险评估Agent

基于规则+AI的混合风险评估模型：
1. 规则引擎：基于连板天数、封单强度等技术指标进行初步筛选
2. AI分析：使用LLM分析涨停原因、市场情绪等定性因素
3. 风险评分：综合计算风险分数（0-100），并给出建议
"""

import json
import logging
from datetime import date, datetime
from decimal import Decimal
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum

from sqlalchemy.orm import Session, sessionmaker

from ..models.database import (
    ContinuousLimitUp,
    LimitUpPool,
    RiskAssessment,
    get_session_maker,
)

logger = logging.getLogger(__name__)


class RiskLevel(Enum):
    """风险等级"""
    LOW = "低"
    MEDIUM = "中"
    HIGH = "高"
    CRITICAL = "极高"


class Suggestion(Enum):
    """投资建议"""
    WATCH = "观望"
    CAUTIOUS = "谨慎"
    AVOID = "规避"
    OPPORTUNITY = "机会"


@dataclass
class RiskFactor:
    """风险因子"""
    name: str
    weight: float
    score: float
    description: str


class RiskAssessmentAgent:
    """
    股票风险评估Agent

    评估维度：
    1. 连板风险：连续涨停天数越多，风险越高
    2. 封单强度：封单金额/流通市值比率
    3. 换手率：高换手率意味着分歧大
    4. 开板次数：盘中打开次数反映抛压
    5. 概念热度：所属板块持续性和市场情绪
    6. 估值风险：PE/PB异常值检测
    """

    def __init__(self, database_url: str):
        """
        初始化Agent

        Args:
            database_url: MySQL连接URL
        """
        self.database_url = database_url
        self.engine = None  # 将在需要时延迟初始化
        self.Session: Optional[sessionmaker[Session]] = None

    def _init_db(self):
        """延迟初始化数据库连接"""
        if not self.Session:
            from ..models.database import init_database
            self.engine = init_database(self.database_url)
            self.Session = get_session_maker(self.engine)

    def _get_session(self) -> Session:
        """获取数据库会话。"""
        self._init_db()
        session_factory = self.Session
        if not session_factory:
            raise RuntimeError("数据库会话初始化失败")
        return session_factory()

    def _upsert_assessment(self, session: Session, assessment: Dict[str, Any]):
        """按 date + code 更新或插入风险评估结果。"""
        record = session.query(RiskAssessment).filter(
            RiskAssessment.date == assessment['date'],
            RiskAssessment.code == assessment['code'],
        ).one_or_none()

        values = {
            'date': assessment['date'],
            'code': assessment['code'],
            'name': assessment['name'],
            'risk_level': assessment['risk_level'],
            'risk_score': assessment['risk_score'],
            'continuous_days': assessment['continuous_days'],
            'risk_factors': assessment['risk_factors'],
            'rule_score': assessment.get('rule_score'),
            'ai_score': assessment.get('ai_score'),
            'ai_confidence': assessment.get('ai_confidence'),
            'score_calculation': assessment.get('score_calculation'),
            'ai_factors': assessment.get('ai_factors'),
            'ai_analysis_report': assessment.get('ai_analysis_report'),
            'is_ai_analyzed': 1 if assessment.get('is_ai_analyzed') else 0,
            'suggestion': assessment['suggestion'],
            'assessment_reason': assessment['assessment_reason'],
        }

        if record:
            for key, value in values.items():
                setattr(record, key, value)
            return record

        record = RiskAssessment(**values)
        session.add(record)
        return record

    def calculate_risk_score(
        self,
        continuous_data: Optional[Dict[str, Any]],
        pool_data: Optional[Dict[str, Any]]
    ) -> Tuple[RiskLevel, float, List[RiskFactor], Suggestion, str]:
        """
        计算风险评分

        Args:
            continuous_data: 连板数据
            pool_data: 涨停强度数据

        Returns:
            (风险等级, 风险分数, 风险因子列表, 建议, 评估理由)
        """
        factors = []
        total_score = 0

        # 1. 连板天数风险（权重35%）
        if continuous_data:
            days = continuous_data.get('continuous_days', 1)
            if days >= 7:
                score = 95
                level = RiskLevel.CRITICAL
            elif days >= 5:
                score = 75
                level = RiskLevel.HIGH
            elif days >= 3:
                score = 55
                level = RiskLevel.MEDIUM
            else:
                score = 30
                level = RiskLevel.LOW

            factor = RiskFactor(
                name="连板天数风险",
                weight=0.35,
                score=score,
                description=f"连续{days}天涨停，{'风险极高' if days >= 7 else '风险较高' if days >= 5 else '中等风险' if days >= 3 else '风险可控'}"
            )
            factors.append(factor)
            total_score += score * factor.weight

        # 2. 封板时间风险（权重15%）
        limit_up_time = None
        if pool_data:
            limit_up_time = pool_data.get('limit_up_time')
        if not limit_up_time and continuous_data:
            limit_up_time = continuous_data.get('latest_limit_up_time')
        time_minutes = self._parse_limit_up_time(limit_up_time)
        if time_minutes is not None:
            if time_minutes <= 9 * 60 + 35:
                score = 20
                desc = "早盘快速封板，资金主动性强"
            elif time_minutes < 10 * 60:
                score = 35
                desc = "早盘封板，强度较好"
            elif time_minutes <= 11 * 60 + 30:
                score = 50
                desc = "盘中封板，强度中等"
            elif time_minutes < 14 * 60 + 30:
                score = 65
                desc = "午后封板，分歧偏大"
            else:
                score = 80
                desc = "封板时间偏晚，尾盘抢筹风险高"

            factor = RiskFactor(
                name="封板时间风险",
                weight=0.15,
                score=score,
                description=f"{desc}（{self._format_minutes(time_minutes)}）"
            )
            factors.append(factor)
            total_score += score * factor.weight

        # 3. 封单强度风险（权重20%）
        if pool_data:
            strength = pool_data.get('strength', 0)
            if strength:
                try:
                    strength_val = float(strength)
                    if strength_val < 0.5:
                        score = 80
                        desc = "封单强度极弱，抛压风险高"
                    elif strength_val < 1.0:
                        score = 60
                        desc = "封单强度较弱"
                    elif strength_val < 3.0:
                        score = 40
                        desc = "封单强度中等"
                    else:
                        score = 20
                        desc = "封单强度强，支撑有力"

                    factor = RiskFactor(
                        name="封单强度",
                        weight=0.20,
                        score=score,
                        description=f"{desc}（强度值：{strength_val}）"
                    )
                    factors.append(factor)
                    total_score += score * factor.weight
                except (ValueError, TypeError):
                    pass

        # 4. 换手率风险（权重20%）
        if pool_data:
            turnover = pool_data.get('turnover_rate', 0)
            if turnover:
                try:
                    turnover_val = float(turnover)
                    if turnover_val > 30:
                        score = 85
                        desc = "换手率极高，分歧严重"
                    elif turnover_val > 15:
                        score = 65
                        desc = "换手率较高"
                    elif turnover_val > 5:
                        score = 40
                        desc = "换手率适中"
                    else:
                        score = 25
                        desc = "换手率较低，筹码锁定"

                    factor = RiskFactor(
                        name="换手率风险",
                        weight=0.20,
                        score=score,
                        description=f"{desc}（{turnover_val}%）"
                    )
                    factors.append(factor)
                    total_score += score * factor.weight
                except (ValueError, TypeError):
                    pass

        # 5. 开板次数风险（权重10%）
        if pool_data:
            open_count = pool_data.get('open_count', 0)
            if open_count:
                try:
                    open_val = int(open_count)
                    if open_val >= 5:
                        score = 80
                        desc = "多次开板，抛压严重"
                    elif open_val >= 2:
                        score = 60
                        desc = "多次开板"
                    else:
                        score = 40
                        desc = "少量开板"

                    factor = RiskFactor(
                        name="开板次数风险",
                        weight=0.10,
                        score=score,
                        description=f"{desc}（{open_val}次）"
                    )
                    factors.append(factor)
                    total_score += score * factor.weight
                except (ValueError, TypeError):
                    pass

        # 计算最终风险分数（0-100，分数越高风险越大）
        final_score = min(100, max(0, round(total_score, 2)))

        # 确定风险等级
        if final_score >= 80:
            risk_level = RiskLevel.CRITICAL
        elif final_score >= 60:
            risk_level = RiskLevel.HIGH
        elif final_score >= 40:
            risk_level = RiskLevel.MEDIUM
        else:
            risk_level = RiskLevel.LOW

        # 生成建议
        if risk_level == RiskLevel.CRITICAL:
            suggestion = Suggestion.AVOID
        elif risk_level == RiskLevel.HIGH:
            suggestion = Suggestion.CAUTIOUS
        elif risk_level == RiskLevel.MEDIUM:
            suggestion = Suggestion.WATCH
        else:
            suggestion = Suggestion.OPPORTUNITY

        # 生成评估理由
        reason = self._generate_assessment_reason(factors, risk_level, suggestion)

        return risk_level, final_score, factors, suggestion, reason

    @staticmethod
    def _parse_limit_up_time(value: Any) -> Optional[int]:
        if value is None or value == "" or value == "-":
            return None

        if isinstance(value, datetime):
            return value.hour * 60 + value.minute

        text = str(value).strip()
        if not text:
            return None

        if ":" in text:
            parts = text.split(":")
            if len(parts) < 2:
                return None
            try:
                hour = int(parts[0])
                minute = int(parts[1])
            except ValueError:
                return None
            return RiskAssessmentAgent._valid_minutes(hour, minute)

        try:
            number = int(float(text))
        except ValueError:
            return None

        if number >= 1_000_000_000:
            parsed = datetime.fromtimestamp(number)
            return parsed.hour * 60 + parsed.minute

        digits = text.split(".")[0].zfill(4)
        if len(digits) >= 5:
            digits = digits.zfill(6)
            hour = int(digits[:-4])
            minute = int(digits[-4:-2])
        else:
            hour = int(digits[:-2])
            minute = int(digits[-2:])
        return RiskAssessmentAgent._valid_minutes(hour, minute)

    @staticmethod
    def _valid_minutes(hour: int, minute: int) -> Optional[int]:
        if hour < 0 or hour > 23 or minute < 0 or minute > 59:
            return None
        return hour * 60 + minute

    @staticmethod
    def _format_minutes(minutes: int) -> str:
        return f"{minutes // 60:02d}:{minutes % 60:02d}"

    def _generate_assessment_reason(
        self,
        factors: List[RiskFactor],
        risk_level: RiskLevel,
        suggestion: Suggestion
    ) -> str:
        """生成评估理由"""
        lines = [
            f"【风险评级：{risk_level.value}】",
            f"【操作建议：{suggestion.value}】",
            "",
            "风险评估详情："
        ]

        for i, factor in enumerate(factors, 1):
            lines.append(f"{i}. {factor.name}（权重{int(factor.weight*100)}%）：")
            lines.append(f"   {factor.description}")
            lines.append(f"   风险评分：{factor.score}/100")
            lines.append("")

        # 添加综合建议
        if suggestion == Suggestion.AVOID:
            lines.append("⚠️ 综合建议：该股当前风险极高，建议坚决规避，不要盲目追高。")
        elif suggestion == Suggestion.CAUTIOUS:
            lines.append("⚡ 综合建议：该股存在较大风险，如已持仓建议逢高减仓，未持仓者观望为主。")
        elif suggestion == Suggestion.WATCH:
            lines.append("👀 综合建议：该股风险中等，可放入自选股观察，等待更好的入场时机。")
        else:
            lines.append("✅ 综合建议：该股风险相对较低，如符合交易策略可考虑适量参与。")

        return "\n".join(lines)

    def assess_stock(
        self,
        code: str,
        name: str,
        target_date: Optional[date] = None
    ) -> Optional[Dict[str, Any]]:
        """
        评估单只股票风险

        Args:
            code: 股票代码
            name: 股票名称
            target_date: 评估日期

        Returns:
            评估结果字典
        """
        if not target_date:
            target_date = date.today()

        self._init_db()
        session = self._get_session()

        try:
            # 查询连板数据
            continuous_record = session.query(ContinuousLimitUp).filter(
                ContinuousLimitUp.date == target_date,
                ContinuousLimitUp.code == code
            ).first()

            # 查询涨停强度数据
            pool_record = session.query(LimitUpPool).filter(
                LimitUpPool.date == target_date,
                LimitUpPool.code == code
            ).first()

            if not continuous_record and not pool_record:
                logger.warning(f"未找到股票数据：{code} {name}")
                return None

            # 转换为字典
            continuous_data = None
            if continuous_record:
                continuous_data = {
                    'code': continuous_record.code,
                    'name': continuous_record.name,
                    'continuous_days': continuous_record.continuous_days,
                    'latest_limit_up_time': continuous_record.latest_limit_up_time,
                }

            pool_data = None
            if pool_record:
                pool_data = {
                    'code': pool_record.code,
                    'name': pool_record.name,
                    'strength': pool_record.strength,
                    'turnover_rate': pool_record.turnover_rate,
                    'open_count': pool_record.open_count,
                    'limit_up_time': pool_record.limit_up_time,
                }

            # 计算风险
            risk_level, risk_score, factors, suggestion, reason = \
                self.calculate_risk_score(continuous_data, pool_data)

            # 获取连板天数
            continuous_days = continuous_data['continuous_days'] if continuous_data else \
                             (1 if pool_data else 0)

            result = {
                'date': target_date,
                'code': code,
                'name': name,
                'risk_level': risk_level.value,
                'risk_score': risk_score,
                'continuous_days': continuous_days,
                'risk_factors': json.dumps([{
                    'name': f.name,
                    'weight': f.weight,
                    'score': f.score,
                    'description': f.description
                } for f in factors], ensure_ascii=False),
                'suggestion': suggestion.value,
                'assessment_reason': reason
            }

            return result

        finally:
            session.close()

    def assess_all_stocks(
        self,
        target_date: Optional[date] = None,
        min_continuous_days: int = 2
    ) -> List[Dict[str, Any]]:
        """
        评估所有符合条件的股票

        Args:
            target_date: 评估日期
            min_continuous_days: 最小连板天数，只评估连板天数>=该值的股票

        Returns:
            评估结果列表
        """
        if not target_date:
            target_date = date.today()

        self._init_db()
        session = self._get_session()

        try:
            # 获取所有符合条件的连板股票
            stocks = session.query(ContinuousLimitUp).filter(
                ContinuousLimitUp.date == target_date,
                ContinuousLimitUp.continuous_days >= min_continuous_days
            ).all()

            logger.info(f"开始风险评估：共{len(stocks)}只股票，日期：{target_date}")

            results = []
            for stock in stocks:
                try:
                    assessment = self.assess_stock(stock.code, stock.name, target_date)
                    if assessment:
                        results.append(assessment)
                except Exception as e:
                    logger.error(f"评估股票失败 {stock.code}: {e}")

            logger.info(f"风险评估完成：成功评估{len(results)}只股票")
            return results

        finally:
            session.close()

    def save_assessments(
        self,
        assessments: List[Dict[str, Any]]
    ) -> Tuple[int, int]:
        """
        保存评估结果到数据库

        Args:
            assessments: 评估结果列表

        Returns:
            (成功数量, 失败数量)
        """
        if not assessments:
            return 0, 0

        self._init_db()
        session = self._get_session()

        success_count = 0
        failed_count = 0

        try:
            for assessment in assessments:
                try:
                    self._upsert_assessment(session, assessment)
                    success_count += 1

                except Exception as e:
                    logger.error(f"保存评估结果失败 {assessment.get('code')}: {e}")
                    failed_count += 1

            session.commit()
            logger.info(f"评估结果保存完成：成功{success_count}条，失败{failed_count}条")

        except Exception as e:
            session.rollback()
            logger.error(f"保存评估结果失败: {e}")
            raise
        finally:
            session.close()

        return success_count, failed_count

    def run_daily_assessment(
        self,
        target_date: Optional[date] = None,
        min_continuous_days: int = 2
    ) -> Dict[str, Any]:
        """
        运行每日风险评估（完整流程）

        Args:
            target_date: 评估日期
            min_continuous_days: 最小连板天数

        Returns:
            执行结果统计
        """
        if not target_date:
            target_date = date.today()

        logger.info(f"开始每日风险评估：{target_date}")

        # 1. 评估所有股票
        assessments = self.assess_all_stocks(target_date, min_continuous_days)

        # 2. 保存结果
        success, failed = self.save_assessments(assessments)

        # 3. 统计结果
        risk_distribution = {}
        for assessment in assessments:
            level = assessment['risk_level']
            risk_distribution[level] = risk_distribution.get(level, 0) + 1

        result = {
            'date': target_date.isoformat(),
            'total_assessed': len(assessments),
            'saved_success': success,
            'saved_failed': failed,
            'risk_distribution': risk_distribution
        }

        logger.info(f"每日风险评估完成：{result}")
        return result


def create_risk_agent(database_url: str) -> RiskAssessmentAgent:
    """
    工厂函数：创建风险评估Agent

    Args:
        database_url: MySQL连接URL

    Returns:
        RiskAssessmentAgent实例
    """
    return RiskAssessmentAgent(database_url)
