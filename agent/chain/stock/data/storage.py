"""
数据存储模块
将抓取的股票数据存储到MySQL数据库
"""

import json
import logging
from datetime import datetime, date
from decimal import Decimal
from typing import Dict, List, Optional, Any, Tuple

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from ..models.database import (
    ContinuousLimitUp,
    BlockTop,
    LimitUpPool,
    DataFetchLog,
    EastmoneyZTPool,
    init_database,
    get_session_maker,
)

logger = logging.getLogger(__name__)


class DecimalEncoder(json.JSONEncoder):
    """处理Decimal类型的JSON编码器"""
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)


class StockDataStorage:
    """股票数据存储器"""

    def __init__(self, database_url: str):
        """
        初始化存储器

        Args:
            database_url: MySQL连接URL
                格式: mysql+pymysql://user:password@host:port/database
        """
        self.database_url = database_url
        self.engine = init_database(database_url)
        self.Session = get_session_maker(self.engine)

    def _safe_decimal(self, value: Any, default: Optional[Decimal] = None) -> Optional[Decimal]:
        """
        安全转换为Decimal

        Args:
            value: 输入值
            default: 默认值

        Returns:
            Decimal值或默认值
        """
        if value is None or value == '' or value == '-':
            return default
        try:
            return Decimal(str(value))
        except (ValueError, TypeError):
            return default

    def _safe_int(self, value: Any, default: int = 0) -> int:
        """
        安全转换为整数

        Args:
            value: 输入值
            default: 默认值

        Returns:
            整数值或默认值
        """
        if value is None or value == '' or value == '-':
            return default
        try:
            return int(value)
        except (ValueError, TypeError):
            return default

    def _safe_str(self, value: Any, default: str = '') -> str:
        """
        安全转换为字符串

        Args:
            value: 输入值
            default: 默认值

        Returns:
            字符串值或默认值
        """
        if value is None:
            return default
        return str(value)

    def save_continuous_limit_up(
        self,
        data: List[Dict[str, Any]],
        target_date: Optional[date] = None
    ) -> Tuple[int, int]:
        """
        保存连板天梯数据

        Args:
            data: 连板天梯数据列表
            target_date: 数据日期，默认今天

        Returns:
            (成功保存数量, 失败数量)
        """
        if not target_date:
            target_date = date.today()

        success_count = 0
        failed_count = 0

        session: Session = self.Session()

        try:
            for item in data:
                try:
                    record = ContinuousLimitUp(
                        date=target_date,
                        code=self._safe_str(item.get('code')),
                        name=self._safe_str(item.get('name')),
                        continuous_days=self._safe_int(item.get('continuous_days')),
                        latest_limit_up_time=self._safe_str(item.get('latest_limit_up_time')),
                        limit_up_open_count=self._safe_int(item.get('limit_up_open_count')),
                        limit_up_price=self._safe_decimal(item.get('limit_up_price')),
                        change_percent=self._safe_decimal(item.get('change_percent')),
                        volume=self._safe_int(item.get('volume')),
                        turnover=self._safe_decimal(item.get('turnover')),
                        market_value=self._safe_decimal(item.get('market_value')),
                        concept=self._safe_str(item.get('concept')),
                    )

                    session.merge(record)  # 使用merge实现upsert
                    success_count += 1

                except Exception as e:
                    logger.error(f"保存连板记录失败 {item.get('code')}: {e}")
                    failed_count += 1

            session.commit()
            logger.info(f"连板天梯数据保存完成: 成功{success_count}条，失败{failed_count}条")

            # 记录日志
            self._save_log(session, target_date, 'continuous_limit_up', success_count)

        except Exception as e:
            session.rollback()
            logger.error(f"保存连板天梯数据失败: {e}")
            raise
        finally:
            session.close()

        return success_count, failed_count

    def save_block_top(
        self,
        data: List[Dict[str, Any]],
        target_date: Optional[date] = None
    ) -> Tuple[int, int]:
        """
        保存最强风口数据

        Args:
            data: 最强风口数据列表
            target_date: 数据日期，默认今天

        Returns:
            (成功保存数量, 失败数量)
        """
        if not target_date:
            target_date = date.today()

        success_count = 0
        failed_count = 0

        session: Session = self.Session()

        try:
            for item in data:
                try:
                    record = BlockTop(
                        date=target_date,
                        block_code=self._safe_str(item.get('block_code')),
                        block_name=self._safe_str(item.get('block_name')),
                        stock_count=self._safe_int(item.get('stock_count')),
                        prev_stock_count=self._safe_int(item.get('prev_stock_count')),
                        change_percent=self._safe_decimal(item.get('change_percent')),
                        leading_stock=self._safe_str(item.get('leading_stock')),
                        leading_stock_name=self._safe_str(item.get('leading_stock_name')),
                        continuous_days=self._safe_int(item.get('continuous_days')),
                        avg_limit_up_time=self._safe_str(item.get('avg_limit_up_time')),
                        block_type=self._safe_str(item.get('block_type')),
                    )

                    session.merge(record)
                    success_count += 1

                except Exception as e:
                    logger.error(f"保存板块记录失败 {item.get('block_code')}: {e}")
                    failed_count += 1

            session.commit()
            logger.info(f"最强风口数据保存完成: 成功{success_count}条，失败{failed_count}条")

            # 记录日志
            self._save_log(session, target_date, 'block_top', success_count)

        except Exception as e:
            session.rollback()
            logger.error(f"保存最强风口数据失败: {e}")
            raise
        finally:
            session.close()

        return success_count, failed_count

    def save_limit_up_pool(
        self,
        data: List[Dict[str, Any]],
        target_date: Optional[date] = None
    ) -> Tuple[int, int]:
        """
        保存涨停强度数据

        Args:
            data: 涨停强度数据列表
            target_date: 数据日期，默认今天

        Returns:
            (成功保存数量, 失败数量)
        """
        if not target_date:
            target_date = date.today()

        success_count = 0
        failed_count = 0

        session: Session = self.Session()

        try:
            for item in data:
                try:
                    record = LimitUpPool(
                        date=target_date,
                        code=self._safe_str(item.get('code')),
                        name=self._safe_str(item.get('name')),
                        latest_price=self._safe_decimal(item.get('latest_price')),
                        limit_up_price=self._safe_decimal(item.get('limit_up_price')),
                        change_percent=self._safe_decimal(item.get('change_percent')),
                        limit_up_type=self._safe_str(item.get('limit_up_type')),
                        limit_up_time=self._safe_str(item.get('limit_up_time')),
                        open_count=self._safe_int(item.get('open_count')),
                        last_time=self._safe_str(item.get('last_time')),
                        strength=self._safe_decimal(item.get('strength')),
                        board_amount=self._safe_decimal(item.get('board_amount')),
                        volume_ratio=self._safe_decimal(item.get('volume_ratio')),
                        turnover_rate=self._safe_decimal(item.get('turnover_rate')),
                        market_value=self._safe_decimal(item.get('market_value')),
                        total_value=self._safe_decimal(item.get('total_value')),
                        pe_ratio=self._safe_decimal(item.get('pe_ratio')),
                        pb_ratio=self._safe_decimal(item.get('pb_ratio')),
                        concept=self._safe_str(item.get('concept')),
                        block_name=self._safe_str(item.get('block_name')),
                        reason=self._safe_str(item.get('reason')),
                    )

                    session.merge(record)
                    success_count += 1

                except Exception as e:
                    logger.error(f"保存涨停记录失败 {item.get('code')}: {e}")
                    failed_count += 1

            session.commit()
            logger.info(f"涨停强度数据保存完成: 成功{success_count}条，失败{failed_count}条")

            # 记录日志
            self._save_log(session, target_date, 'limit_up_pool', success_count)

        except Exception as e:
            session.rollback()
            logger.error(f"保存涨停强度数据失败: {e}")
            raise
        finally:
            session.close()

        return success_count, failed_count

    def save_eastmoney_zt_pool(
        self,
        data: List[Dict[str, Any]],
        target_date: Optional[date] = None
    ) -> Tuple[int, int]:
        """
        保存东方财富涨停池数据

        Args:
            data: 东财涨停池数据列表
            target_date: 数据日期，默认今天

        Returns:
            (成功保存数量, 失败数量)
        """
        if not target_date:
            target_date = date.today()

        success_count = 0
        failed_count = 0

        session: Session = self.Session()

        try:
            for item in data:
                try:
                    record = EastmoneyZTPool(
                        date=target_date,
                        code=self._safe_str(item.get('c')),  # 东财字段：c
                        name=self._safe_str(item.get('n')),  # 东财字段：n
                        latest_price=self._safe_decimal(item.get('p')),  # 东财字段：p
                        change_percent=self._safe_decimal(item.get('zdp')),  # 东财字段：zdp
                        first_limit_up_time=self._safe_str(item.get('fbt')),  # 东财字段：fbt
                        last_limit_up_time=self._safe_str(item.get('lbt')),  # 东财字段：lbt
                        limit_up_type=self._safe_str(item.get('zttz')),  # 东财字段：zttz
                        board_amount=self._safe_decimal(item.get('fund')),  # 东财字段：fund（封单金额）
                        block_name=self._safe_str(item.get('hybk')),  # 东财字段：hybk（行业板块）
                        reason=self._safe_str(item.get('ztzy')),  # 东财字段：ztzy（涨停原因）
                        volume=self._safe_int(item.get('v')),  # 东财字段：v
                        turnover=self._safe_int(item.get('a')),  # 东财字段：a（成交额）
                        market_value=self._safe_decimal(item.get('m')),  # 东财字段：m（总市值）
                        circulating_value=self._safe_decimal(item.get('cm')),  # 东财字段：cm（流通市值）
                        turnover_rate=self._safe_decimal(item.get('hs')),  # 东财字段：hs（换手率）
                        pe_ratio=self._safe_decimal(item.get('pe')),  # 东财字段：pe
                        amplitude=self._safe_decimal(item.get('zf')),  # 东财字段：zf（振幅）
                        pre_3_day_change=self._safe_decimal(item.get('z3')),  # 东财字段：z3（3日涨幅）
                    )

                    session.merge(record)
                    success_count += 1

                except Exception as e:
                    logger.error(f"保存东财涨停记录失败 {item.get('c')}: {e}")
                    failed_count += 1

            session.commit()
            logger.info(f"东方财富涨停池数据保存完成: 成功{success_count}条，失败{failed_count}条")

            # 记录日志
            self._save_log(session, target_date, 'eastmoney_zt_pool', success_count)

        except Exception as e:
            session.rollback()
            logger.error(f"保存东方财富涨停池数据失败: {e}")
            raise
        finally:
            session.close()

        return success_count, failed_count

    def save_all_data(
        self,
        data: Dict[str, List[Dict[str, Any]]],
        target_date: Optional[date] = None
    ) -> Dict[str, Tuple[int, int]]:
        """
        保存所有数据（包括东财数据）

        Args:
            data: 包含各类数据的字典
            target_date: 数据日期

        Returns:
            各类数据的保存结果
        """
        if not target_date:
            target_date = date.today()

        results = {}

        # 保存连板天梯
        if 'continuous_limit_up' in data:
            results['continuous_limit_up'] = self.save_continuous_limit_up(
                data['continuous_limit_up'], target_date
            )

        # 保存最强风口
        if 'block_top' in data:
            results['block_top'] = self.save_block_top(
                data['block_top'], target_date
            )

        # 保存涨停强度
        if 'limit_up_pool' in data:
            results['limit_up_pool'] = self.save_limit_up_pool(
                data['limit_up_pool'], target_date
            )

        # 保存东方财富涨停池
        if 'eastmoney_zt_pool' in data:
            results['eastmoney_zt_pool'] = self.save_eastmoney_zt_pool(
                data['eastmoney_zt_pool'], target_date
            )

        return results

    def _save_log(
        self,
        session: Session,
        target_date: date,
        data_type: str,
        record_count: int,
        status: str = 'success',
        error_message: Optional[str] = None
    ):
        """
        保存数据抓取日志

        Args:
            session: 数据库会话
            target_date: 数据日期
            data_type: 数据类型
            record_count: 记录数
            status: 状态
            error_message: 错误信息
        """
        try:
            log = DataFetchLog(
                date=target_date,
                data_type=data_type,
                status=status,
                record_count=record_count,
                error_message=error_message
            )
            session.merge(log)
            session.commit()
        except Exception as e:
            logger.error(f"保存日志失败: {e}")
            session.rollback()

    def get_data_status(self, target_date: Optional[date] = None) -> Dict[str, Any]:
        """
        获取某天的数据状态

        Args:
            target_date: 数据日期，默认今天

        Returns:
            数据状态字典
        """
        if not target_date:
            target_date = date.today()

        session: Session = self.Session()

        try:
            status = {}

            # 查询各类数据数量
            status['continuous_limit_up'] = session.query(ContinuousLimitUp).filter(
                ContinuousLimitUp.date == target_date
            ).count()

            status['block_top'] = session.query(BlockTop).filter(
                BlockTop.date == target_date
            ).count()

            status['limit_up_pool'] = session.query(LimitUpPool).filter(
                LimitUpPool.date == target_date
            ).count()

            # 查询东方财富涨停池
            status['eastmoney_zt_pool'] = session.query(EastmoneyZTPool).filter(
                EastmoneyZTPool.date == target_date
            ).count()

            # 查询日志
            logs = session.query(DataFetchLog).filter(
                DataFetchLog.date == target_date
            ).all()

            status['logs'] = [
                {
                    'data_type': log.data_type,
                    'status': log.status,
                    'record_count': log.record_count,
                    'error_message': log.error_message,
                    'created_at': log.created_at.isoformat() if log.created_at else None
                }
                for log in logs
            ]

            status['date'] = target_date.isoformat()
            status['is_complete'] = all([
                status['continuous_limit_up'] > 0,
                status['block_top'] > 0,
                status['limit_up_pool'] > 0
            ])

            return status

        finally:
            session.close()


def create_storage(database_url: str) -> StockDataStorage:
    """
    工厂函数：创建数据存储器

    Args:
        database_url: MySQL连接URL

    Returns:
        StockDataStorage实例
    """
    return StockDataStorage(database_url)
