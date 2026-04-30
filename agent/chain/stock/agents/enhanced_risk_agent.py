"""
增强版风险评估Agent

结合规则引擎 + AI智能分析的综合风险评估系统
"""

import json
import logging
from datetime import date
from typing import Dict, List, Optional, Any, Tuple

from sqlalchemy.orm import Session

from ..models.database import (
    ContinuousLimitUp,
    LimitUpPool,
    RiskAssessment,
    init_database,
    get_session_maker,
)
from .risk_agent import RiskAssessmentAgent, RiskLevel, Suggestion, RiskFactor
from .ai_analyzer import AIStockAnalyzer, create_ai_analyzer

logger = logging.getLogger(__name__)


class EnhancedRiskAssessmentAgent(RiskAssessmentAgent):
    """
    增强版风险评估Agent

    整合规则引擎 + AI分析，提供更全面的风险评估：
    1. 规则引擎：基于技术指标的快速筛选（权重60%）
    2. AI分析：基于LLM的深度分析（权重40%）
    """

    def __init__(self, database_url: str):
        """
        初始化增强版Agent

        Args:
            database_url: MySQL连接URL
        """
        super().__init__(database_url)
        self.ai_analyzer = create_ai_analyzer(database_url)

    def calculate_enhanced_risk_score(
        self,
        rule_score: float,
        ai_score: Optional[float],
        ai_confidence: float = 0.5
    ) -> Tuple[float, str]:
        """
        计算综合风险分数

        Args:
            rule_score: 规则引擎评分(0-100)
            ai_score: AI分析评分(0-100)
            ai_confidence: AI置信度(0-1)

        Returns:
            (综合分数, 计算说明)
        """
        if ai_score is None:
            # 没有AI评分，纯规则引擎
            return rule_score, "纯规则引擎评分"

        # 根据AI置信度调整权重
        # 高置信度(>0.8)：AI权重40%
        # 中置信度(0.5-0.8)：AI权重30%
        # 低置信度(<0.5)：AI权重20%

        if ai_confidence >= 0.8:
            ai_weight = 0.4
            rule_weight = 0.6
            confidence_desc = "高"
        elif ai_confidence >= 0.5:
            ai_weight = 0.3
            rule_weight = 0.7
            confidence_desc = "中"
        else:
            ai_weight = 0.2
            rule_weight = 0.8
            confidence_desc = "低"

        final_score = (rule_score * rule_weight) + (ai_score * ai_weight)

        desc = f"规则引擎({rule_score}分)×{rule_weight} + AI分析({ai_score}分)×{ai_weight} = {final_score:.2f}分 (AI置信度{confidence_desc})"

        return round(final_score, 2), desc

    def assess_stock_enhanced(
        self,
        code: str,
        name: str,
        target_date: Optional[date] = None,
        use_ai: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        增强版单只股票评估

        Args:
            code: 股票代码
            name: 股票名称
            target_date: 评估日期
            use_ai: 是否使用AI分析

        Returns:
            增强版评估结果
        """
        if not target_date:
            target_date = date.today()

        # 1. 规则引擎评估
        base_assessment = super().assess_stock(code, name, target_date)

        if not base_assessment:
            return None

        rule_score = base_assessment['risk_score']
        rule_factors = json.loads(base_assessment.get('risk_factors', '[]'))

        # 2. AI分析（可选）
        ai_score = None
        ai_confidence = 0
        ai_suggestion = None
        ai_report = None
        ai_factors = []

        if use_ai and self.ai_analyzer.llm:
            try:
                ai_result = self.ai_analyzer.analyze_stock(code, name, target_date)

                if ai_result:
                    ai_score = ai_result.ai_risk_score
                    ai_confidence = ai_result.confidence
                    ai_suggestion = ai_result.ai_suggestion
                    ai_report = ai_result.analysis_report
                    ai_factors = ai_result.key_factors

                    logger.info(f"AI分析完成: {code}, 评分: {ai_score}, 置信度: {ai_confidence}")

            except Exception as e:
                logger.error(f"AI分析失败 {code}: {e}")

        # 3. 计算综合分数
        final_score, calc_desc = self.calculate_enhanced_risk_score(
            rule_score, ai_score, ai_confidence
        )

        # 4. 确定最终风险等级和建议
        if final_score >= 80:
            final_level = RiskLevel.CRITICAL.value
            final_suggestion = Suggestion.AVOID.value
        elif final_score >= 60:
            final_level = RiskLevel.HIGH.value
            final_suggestion = Suggestion.CAUTIOUS.value
        elif final_score >= 40:
            final_level = RiskLevel.MEDIUM.value
            final_suggestion = Suggestion.WATCH.value
        else:
            final_level = RiskLevel.LOW.value
            final_suggestion = Suggestion.OPPORTUNITY.value

        # 如果AI建议与规则引擎冲突，以AI为准（如果置信度高）
        if ai_suggestion and ai_confidence >= 0.7:
            suggestion_map = {
                "强烈推荐": Suggestion.OPPORTUNITY.value,
                "推荐": Suggestion.OPPORTUNITY.value,
                "观望": Suggestion.WATCH.value,
                "规避": Suggestion.AVOID.value,
            }
            final_suggestion = suggestion_map.get(ai_suggestion, final_suggestion)

        # 5. 构建增强版结果
        enhanced_result = {
            # 基础信息
            'date': target_date,
            'code': code,
            'name': name,

            # 综合评估
            'risk_level': final_level,
            'risk_score': final_score,
            'suggestion': final_suggestion,
            'continuous_days': base_assessment['continuous_days'],

            # 详细分数
            'rule_score': rule_score,
            'ai_score': ai_score,
            'ai_confidence': ai_confidence,
            'score_calculation': calc_desc,

            # 风险因子
            'risk_factors': base_assessment['risk_factors'],
            'ai_factors': json.dumps(ai_factors, ensure_ascii=False) if ai_factors else None,

            # 评估理由
            'assessment_reason': self._generate_enhanced_reason(
                base_assessment['assessment_reason'],
                ai_report,
                rule_score,
                ai_score,
                ai_confidence
            ),

            # AI专属字段
            'ai_analysis_report': ai_report,
            'is_ai_analyzed': ai_score is not None
        }

        return enhanced_result

    def _generate_enhanced_reason(
        self,
        rule_reason: str,
        ai_report: Optional[str],
        rule_score: float,
        ai_score: Optional[float],
        ai_confidence: float
    ) -> str:
        """生成增强版评估理由"""
        lines = [
            "=" * 60,
            "【增强版风险评估报告 - 规则引擎 + AI智能分析】",
            "=" * 60,
            "",
            "📊 一、规则引擎评估",
            "-" * 60,
            rule_reason,
            "",
            f"📈 规则引擎风险评分: {rule_score}/100",
            ""
        ]

        if ai_report and ai_score is not None:
            lines.extend([
                "🤖 二、AI智能分析",
                "-" * 60,
                ai_report,
                "",
                f"🎯 AI风险评分: {ai_score}/100 (置信度: {ai_confidence})",
                ""
            ])

            lines.extend([
                "⚖️  三、综合评估",
                "-" * 60,
                f"规则引擎评分: {rule_score}分",
                f"AI分析评分: {ai_score}分 (置信度: {ai_confidence})",
                ""
            ])

            # 对比分析
            diff = ai_score - rule_score
            if abs(diff) <= 10:
                lines.append("✅ 规则引擎与AI分析结果高度一致")
            elif diff > 10:
                lines.append(f"⚠️ AI认为风险更高({diff:.1f}分)，建议优先考虑AI判断")
            else:
                lines.append(f"💡 AI认为风险较低({abs(diff):.1f}分)，可能存在机会")

        else:
            lines.extend([
                "🤖 二、AI智能分析",
                "-" * 60,
                "⚠️ AI分析未执行或失败",
                ""
            ])

        lines.append("=" * 60)

        return "\n".join(lines)

    def run_daily_assessment_enhanced(
        self,
        target_date: Optional[date] = None,
        min_continuous_days: int = 2,
        use_ai: bool = True
    ) -> Dict[str, Any]:
        """
        运行每日增强版风险评估

        Args:
            target_date: 评估日期
            min_continuous_days: 最小连板天数
            use_ai: 是否使用AI分析

        Returns:
            执行结果统计
        """
        if not target_date:
            target_date = date.today()

        logger.info(f"开始每日增强版风险评估: {target_date}, AI分析: {use_ai}")

        # 1. 获取所有符合条件的股票
        self._init_db()
        session: Session = self.Session()

        try:
            stocks = session.query(ContinuousLimitUp).filter(
                ContinuousLimitUp.date == target_date,
                ContinuousLimitUp.continuous_days >= min_continuous_days
            ).all()

            logger.info(f"共{len(stocks)}只股票需要评估")

            # 2. 逐个评估
            assessments = []
            ai_success_count = 0

            for i, stock in enumerate(stocks, 1):
                try:
                    logger.info(f"[{i}/{len(stocks)}] 评估: {stock.code} {stock.name}")

                    assessment = self.assess_stock_enhanced(
                        stock.code, stock.name, target_date, use_ai
                    )

                    if assessment:
                        assessments.append(assessment)
                        if assessment.get('is_ai_analyzed'):
                            ai_success_count += 1

                except Exception as e:
                    logger.error(f"评估失败 {stock.code}: {e}")
                    continue

            # 3. 保存结果
            success, failed = self.save_enhanced_assessments(assessments)

            # 4. 统计结果
            risk_distribution = {}
            ai_distribution = {'ai_analyzed': 0, 'rule_only': 0}

            for assessment in assessments:
                level = assessment['risk_level']
                risk_distribution[level] = risk_distribution.get(level, 0) + 1

                if assessment.get('is_ai_analyzed'):
                    ai_distribution['ai_analyzed'] += 1
                else:
                    ai_distribution['rule_only'] += 1

            result = {
                'date': target_date.isoformat(),
                'total_assessed': len(assessments),
                'saved_success': success,
                'saved_failed': failed,
                'ai_success_count': ai_success_count,
                'risk_distribution': risk_distribution,
                'analysis_method_distribution': ai_distribution
            }

            logger.info(f"每日增强版风险评估完成: {result}")
            return result

        finally:
            session.close()

    def save_enhanced_assessments(
        self,
        assessments: List[Dict[str, Any]]
    ) -> Tuple[int, int]:
        """
        保存增强版评估结果

        Args:
            assessments: 评估结果列表

        Returns:
            (成功数量, 失败数量)
        """
        if not assessments:
            return 0, 0

        self._init_db()
        session: Session = self.Session()

        success_count = 0
        failed_count = 0

        try:
            for assessment in assessments:
                try:
                    record = RiskAssessment(
                        date=assessment['date'],
                        code=assessment['code'],
                        name=assessment['name'],
                        risk_level=assessment['risk_level'],
                        risk_score=assessment['risk_score'],
                        continuous_days=assessment['continuous_days'],
                        risk_factors=assessment['risk_factors'],
                        suggestion=assessment['suggestion'],
                        assessment_reason=assessment['assessment_reason']
                    )

                    session.merge(record)
                    success_count += 1

                except Exception as e:
                    logger.error(f"保存评估结果失败 {assessment.get('code')}: {e}")
                    failed_count += 1

            session.commit()
            logger.info(f"增强版评估结果保存完成: 成功{success_count}条，失败{failed_count}条")

        except Exception as e:
            session.rollback()
            logger.error(f"保存评估结果失败: {e}")
            raise
        finally:
            session.close()

        return success_count, failed_count


def create_enhanced_risk_agent(database_url: Optional[str] = None) -> EnhancedRiskAssessmentAgent:
    """
    工厂函数：创建增强版风险评估Agent

    Args:
        database_url: MySQL连接URL，默认从环境变量读取

    Returns:
        EnhancedRiskAssessmentAgent实例
    """
    import os

    if not database_url:
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            raise ValueError("请提供database_url或设置DATABASE_URL环境变量")

    return EnhancedRiskAssessmentAgent(database_url)
