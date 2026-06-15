"""
数据库模型定义
使用SQLAlchemy ORM定义股票数据表结构
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Column, String, Integer, Float, DateTime, Date,
    Index, create_engine, Text, Numeric as Decimal, BigInteger
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

Base = declarative_base()


class ContinuousLimitUp(Base):
    """
    连板天梯数据表
    存储每日连板股票信息
    """
    __tablename__ = 'continuous_limit_up'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    date = Column(Date, nullable=False, index=True, comment='数据日期')
    code = Column(String(20), nullable=False, index=True, comment='股票代码')
    name = Column(String(100), nullable=False, comment='股票名称')
    continuous_days = Column(Integer, nullable=False, comment='连板天数')
    latest_limit_up_time = Column(String(20), nullable=True, comment='最新涨停时间')
    limit_up_open_count = Column(Integer, default=0, comment='涨停打开次数')
    limit_up_price = Column(Decimal(10, 2), nullable=True, comment='涨停价')
    change_percent = Column(Decimal(10, 2), nullable=True, comment='涨跌幅%')
    volume = Column(BigInteger, nullable=True, comment='成交量')
    turnover = Column(Decimal(20, 2), nullable=True, comment='成交额')
    market_value = Column(Decimal(20, 2), nullable=True, comment='总市值')
    concept = Column(Text, nullable=True, comment='所属概念')
    created_at = Column(DateTime, default=datetime.now, comment='创建时间')
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')

    __table_args__ = (
        Index('idx_date_continuous', 'date', 'continuous_days'),
        Index('idx_date_code', 'date', 'code', unique=True),
        {'comment': '连板天梯数据'}
    )


class BlockTop(Base):
    """
    最强风口数据表
    存储每日热点板块信息
    """
    __tablename__ = 'block_top'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    date = Column(Date, nullable=False, index=True, comment='数据日期')
    block_code = Column(String(20), nullable=False, index=True, comment='板块代码')
    block_name = Column(String(100), nullable=False, comment='板块名称')
    stock_count = Column(Integer, default=0, comment='涨停家数')
    prev_stock_count = Column(Integer, default=0, comment='上一日涨停家数')
    change_percent = Column(Decimal(10, 2), nullable=True, comment='板块涨跌幅%')
    leading_stock = Column(String(20), nullable=True, comment='龙头股代码')
    leading_stock_name = Column(String(100), nullable=True, comment='龙头股名称')
    continuous_days = Column(Integer, default=1, comment='持续天数')
    avg_limit_up_time = Column(String(20), nullable=True, comment='平均涨停时间')
    block_type = Column(String(50), nullable=True, comment='板块类型')
    created_at = Column(DateTime, default=datetime.now, comment='创建时间')
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')

    __table_args__ = (
        Index('idx_date_block', 'date', 'block_code', unique=True),
        Index('idx_date_count', 'date', 'stock_count'),
        {'comment': '最强风口数据'}
    )


class LimitUpPool(Base):
    """
    涨停强度数据表
    存储每日涨停股票的详细信息
    """
    __tablename__ = 'limit_up_pool'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    date = Column(Date, nullable=False, index=True, comment='数据日期')
    code = Column(String(20), nullable=False, index=True, comment='股票代码')
    name = Column(String(100), nullable=False, comment='股票名称')
    latest_price = Column(Decimal(10, 2), nullable=True, comment='最新价')
    limit_up_price = Column(Decimal(10, 2), nullable=True, comment='涨停价')
    change_percent = Column(Decimal(10, 2), nullable=True, comment='涨跌幅%')
    limit_up_type = Column(String(20), nullable=True, comment='涨停类型(首板/连板)')
    limit_up_time = Column(String(20), nullable=True, comment='涨停时间')
    open_count = Column(Integer, default=0, comment='打开次数')
    last_time = Column(String(100), nullable=True, comment='最后封板时间')
    strength = Column(Decimal(10, 4), nullable=True, comment='封单强度')
    board_amount = Column(Decimal(20, 2), nullable=True, comment='封单金额')
    volume_ratio = Column(Decimal(10, 2), nullable=True, comment='量比')
    turnover_rate = Column(Decimal(10, 2), nullable=True, comment='换手率%')
    market_value = Column(Decimal(20, 2), nullable=True, comment='流通市值')
    total_value = Column(Decimal(20, 2), nullable=True, comment='总市值')
    pe_ratio = Column(Decimal(10, 2), nullable=True, comment='市盈率')
    pb_ratio = Column(Decimal(10, 2), nullable=True, comment='市净率')
    concept = Column(Text, nullable=True, comment='所属概念')
    block_name = Column(String(100), nullable=True, comment='所属板块')
    reason = Column(Text, nullable=True, comment='涨停原因')
    created_at = Column(DateTime, default=datetime.now, comment='创建时间')
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')

    __table_args__ = (
        Index('idx_date_code_pool', 'date', 'code', unique=True),
        Index('idx_date_type', 'date', 'limit_up_type'),
        Index('idx_date_strength', 'date', 'strength'),
        {'comment': '涨停强度数据'}
    )


class RiskAssessment(Base):
    """
    风险评估结果表
    存储AI Agent对每日股票的风险评估
    """
    __tablename__ = 'risk_assessment'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    date = Column(Date, nullable=False, index=True, comment='数据日期')
    code = Column(String(20), nullable=False, index=True, comment='股票代码')
    name = Column(String(100), nullable=False, comment='股票名称')
    risk_level = Column(String(20), nullable=False, comment='风险等级(高/中/低)')
    risk_score = Column(Decimal(5, 2), nullable=True, comment='风险分数(0-100)')
    continuous_days = Column(Integer, default=0, comment='连板天数')
    risk_factors = Column(Text, nullable=True, comment='风险因子JSON')
    rule_score = Column(Decimal(5, 2), nullable=True, comment='规则引擎风险分数')
    ai_score = Column(Decimal(5, 2), nullable=True, comment='AI风险分数')
    ai_confidence = Column(Decimal(5, 4), nullable=True, comment='AI分析置信度')
    score_calculation = Column(Text, nullable=True, comment='综合分数计算说明')
    ai_factors = Column(Text, nullable=True, comment='AI关键因子JSON')
    ai_analysis_report = Column(Text, nullable=True, comment='AI分析报告')
    is_ai_analyzed = Column(Integer, default=0, comment='是否完成AI分析')
    suggestion = Column(String(50), nullable=True, comment='建议(观望/谨慎/规避)')
    assessment_reason = Column(Text, nullable=True, comment='评估理由')
    created_at = Column(DateTime, default=datetime.now, comment='创建时间')
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')

    __table_args__ = (
        Index('idx_date_code_risk', 'date', 'code', unique=True),
        Index('idx_date_level', 'date', 'risk_level'),
        {'comment': '风险评估结果'}
    )


class DataFetchLog(Base):
    """
    数据抓取日志表
    记录每日数据抓取情况
    """
    __tablename__ = 'data_fetch_log'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    date = Column(Date, nullable=False, index=True, comment='数据日期')
    data_type = Column(String(50), nullable=False, comment='数据类型')
    status = Column(String(20), nullable=False, comment='状态(success/failed)')
    record_count = Column(Integer, default=0, comment='记录数')
    error_message = Column(Text, nullable=True, comment='错误信息')
    created_at = Column(DateTime, default=datetime.now, comment='创建时间')

    __table_args__ = (
        Index('idx_date_type', 'date', 'data_type', unique=True),
        {'comment': '数据抓取日志'}
    )


class EastmoneyZTPool(Base):
    """
    东方财富涨停池数据表
    存储从东方财富抓取的涨停股票数据
    """
    __tablename__ = 'eastmoney_zt_pool'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    date = Column(Date, nullable=False, index=True, comment='数据日期')
    code = Column(String(20), nullable=False, index=True, comment='股票代码')
    name = Column(String(100), nullable=False, comment='股票名称')
    latest_price = Column(Decimal(10, 2), nullable=True, comment='最新价')
    change_percent = Column(Decimal(10, 2), nullable=True, comment='涨跌幅%')
    first_limit_up_time = Column(String(20), nullable=True, comment='首次涨停时间')
    last_limit_up_time = Column(String(20), nullable=True, comment='最后涨停时间')
    limit_up_type = Column(String(20), nullable=True, comment='涨停类型(首板/连板)')
    board_amount = Column(Decimal(20, 2), nullable=True, comment='封单金额(万元)')
    block_name = Column(String(100), nullable=True, comment='所属板块/行业')
    reason = Column(Text, nullable=True, comment='涨停原因/特征')
    volume = Column(BigInteger, nullable=True, comment='成交量')
    turnover = Column(BigInteger, nullable=True, comment='成交额')
    market_value = Column(Decimal(20, 2), nullable=True, comment='总市值(亿元)')
    circulating_value = Column(Decimal(20, 2), nullable=True, comment='流通市值(亿元)')
    turnover_rate = Column(Decimal(10, 2), nullable=True, comment='换手率%')
    pe_ratio = Column(Decimal(10, 2), nullable=True, comment='市盈率')
    amplitude = Column(Decimal(10, 2), nullable=True, comment='振幅%')
    pre_3_day_change = Column(Decimal(10, 2), nullable=True, comment='前3日涨幅%')
    created_at = Column(DateTime, default=datetime.now, comment='创建时间')
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')

    __table_args__ = (
        Index('idx_date_code_em', 'date', 'code', unique=True),
        Index('idx_date_block_em', 'date', 'block_name'),
        Index('idx_date_first_time', 'date', 'first_limit_up_time'),
        {'comment': '东方财富涨停池数据'}
    )


def init_database(database_url: str):
    """
    初始化数据库，创建所有表

    Args:
        database_url: MySQL连接URL
            格式: mysql+pymysql://user:password@host:port/database
    """
    engine = create_engine(database_url, pool_pre_ping=True)
    Base.metadata.create_all(engine)
    return engine


def get_session_maker(engine):
    """获取数据库会话工厂"""
    return sessionmaker(bind=engine)
