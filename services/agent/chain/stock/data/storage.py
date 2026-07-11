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
    BlockTopStock,
    LimitUpPool,
    LowerLimitPool,
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

    def _first_value(self, item: Dict[str, Any], *keys: str) -> Any:
        """按候选字段名取第一个非空值，兼容不同数据源字段。"""
        for key in keys:
            value = item.get(key)
            if value is not None and value != '' and value != '-':
                return value
        return None

    def _first_list_item(self, item: Dict[str, Any], key: str) -> Dict[str, Any]:
        value = item.get(key)
        if isinstance(value, list) and value and isinstance(value[0], dict):
            return value[0]
        return {}

    def _list_items(self, item: Dict[str, Any], key: str) -> List[Dict[str, Any]]:
        value = item.get(key)
        if not isinstance(value, list):
            return []
        return [entry for entry in value if isinstance(entry, dict)]

    def _upsert_by_keys(
        self,
        session: Session,
        model,
        values: Dict[str, Any],
        key_fields: Tuple[str, ...],
    ):
        """按业务唯一键更新或插入，避免 session.merge 只按主键判断导致重复插入。"""
        filters = [
            getattr(model, field) == values[field]
            for field in key_fields
        ]
        record = session.query(model).filter(*filters).one_or_none()
        if record:
            for key, value in values.items():
                setattr(record, key, value)
            return record
        record = model(**values)
        session.add(record)
        return record

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
                    code = self._safe_str(self._first_value(item, 'code', 'stock_code', 'symbol'))
                    name = self._safe_str(self._first_value(item, 'name', 'stock_name', 'short_name'))
                    if not code or not name:
                        logger.warning(f"跳过连板记录，缺少股票代码或名称: {item}")
                        failed_count += 1
                        continue

                    values = {
                        'date': target_date,
                        'code': code,
                        'name': name,
                        'continuous_days': self._safe_int(self._first_value(item, 'continuous_days', 'high_days', 'limit_up_days', 'days')),
                        'latest_limit_up_time': self._safe_str(self._first_value(item, 'latest_limit_up_time', 'limit_up_time', 'last_limit_up_time')),
                        'limit_up_open_count': self._safe_int(self._first_value(item, 'limit_up_open_count', 'open_count')),
                        'limit_up_price': self._safe_decimal(self._first_value(item, 'limit_up_price', 'price')),
                        'change_percent': self._safe_decimal(self._first_value(item, 'change_percent', 'change_rate', 'rate')),
                        'volume': self._safe_int(self._first_value(item, 'volume', 'vol')),
                        'turnover': self._safe_decimal(self._first_value(item, 'turnover', 'amount')),
                        'market_value': self._safe_decimal(self._first_value(item, 'market_value', 'total_value', 'circulation_value')),
                        'concept': self._safe_str(self._first_value(item, 'concept', 'reason', 'reason_info')),
                    }

                    self._upsert_by_keys(session, ContinuousLimitUp, values, ('date', 'code'))
                    success_count += 1

                except Exception as e:
                    logger.error(f"保存连板记录失败 {item.get('code')}: {e}")
                    failed_count += 1

            # 记录日志
            self._save_log(session, target_date, 'continuous_limit_up', success_count)
            session.commit()
            logger.info(f"连板天梯数据保存完成: 成功{success_count}条，失败{failed_count}条")

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
                    block_name = self._safe_str(self._first_value(item, 'block_name', 'name', 'plate_name', 'concept_name'))
                    block_code = self._safe_str(self._first_value(item, 'block_code', 'code', 'plate_code', 'concept_code'), block_name)
                    if not block_name:
                        logger.warning(f"跳过板块记录，缺少板块名称: {item}")
                        failed_count += 1
                        continue

                    values = {
                        'date': target_date,
                        'block_code': block_code,
                        'block_name': block_name,
                        'stock_count': self._safe_int(self._first_value(item, 'stock_count', 'num', 'count', 'limit_up_count', 'limit_up_num')),
                        'prev_stock_count': self._safe_int(self._first_value(item, 'prev_stock_count', 'pre_num', 'prev_count')),
                        'change_percent': self._safe_decimal(self._first_value(item, 'change_percent', 'change_rate', 'rate', 'change')),
                        'continuous_plate_num': self._safe_int(self._first_value(item, 'continuous_plate_num'), None),
                        'high_text': self._safe_str(self._first_value(item, 'high')),
                        'high_num': self._safe_int(self._first_value(item, 'high_num'), None),
                        'leading_stock': self._safe_str(self._first_value(item, 'leading_stock', 'leader_code', 'stock_code', 'leader.code')),
                        'leading_stock_name': self._safe_str(self._first_value(item, 'leading_stock_name', 'leader_name', 'stock_name', 'leader.name')),
                        'continuous_days': self._safe_int(self._first_value(item, 'continuous_days', 'days', 'high_days'), 1),
                        'avg_limit_up_time': self._safe_str(self._first_value(item, 'avg_limit_up_time', 'avg_time')),
                        'block_type': self._safe_str(self._first_value(item, 'block_type', 'type')),
                    }
                    leader = self._first_list_item(item, 'stock_list')
                    if not values['leading_stock']:
                        values['leading_stock'] = self._safe_str(leader.get('code'))
                    if not values['leading_stock_name']:
                        values['leading_stock_name'] = self._safe_str(leader.get('name'))
                    if not values['avg_limit_up_time']:
                        values['avg_limit_up_time'] = self._safe_str(
                            leader.get('first_limit_up_time')
                        )

                    self._upsert_by_keys(session, BlockTop, values, ('date', 'block_code'))
                    self._save_block_top_stocks(
                        session,
                        item,
                        target_date,
                        block_code,
                        block_name,
                    )
                    success_count += 1

                except Exception as e:
                    logger.error(f"保存板块记录失败 {item.get('block_code')}: {e}")
                    failed_count += 1

            # 记录日志
            self._save_log(session, target_date, 'block_top', success_count)
            session.commit()
            logger.info(f"最强风口数据保存完成: 成功{success_count}条，失败{failed_count}条")

        except Exception as e:
            session.rollback()
            logger.error(f"保存最强风口数据失败: {e}")
            raise
        finally:
            session.close()

        return success_count, failed_count

    def _save_block_top_stocks(
        self,
        session: Session,
        item: Dict[str, Any],
        target_date: date,
        block_code: str,
        block_name: str,
    ) -> int:
        if not isinstance(item.get('stock_list'), list):
            return 0

        stock_list = self._list_items(item, 'stock_list')
        seen_codes = set()
        saved_count = 0

        for index, stock in enumerate(stock_list, 1):
            code = self._safe_str(
                self._first_value(stock, 'code', 'stock_code', 'symbol')
            )
            name = self._safe_str(
                self._first_value(stock, 'name', 'stock_name')
            )
            if not code or not name or code in seen_codes:
                continue

            values = {
                'date': target_date,
                'block_code': block_code,
                'block_name': block_name,
                'code': code,
                'name': name,
                'continuous_days': self._safe_int(
                    self._first_value(
                        stock,
                        'continuous_days',
                        'continue_num',
                        'high_days',
                        'limit_up_days',
                    ),
                    1,
                ),
                'limit_up_type': self._safe_str(
                    self._first_value(stock, 'high', 'limit_up_type')
                ),
                'high_days': self._safe_int(
                    self._first_value(stock, 'high_days'),
                    None,
                ),
                'first_limit_up_time': self._safe_str(
                    self._first_value(
                        stock,
                        'first_limit_up_time',
                        'limit_up_time',
                        'time',
                    )
                ),
                'last_limit_up_time': self._safe_str(
                    self._first_value(stock, 'last_limit_up_time', 'last_time')
                ),
                'change_percent': self._safe_decimal(
                    self._first_value(stock, 'change_percent', 'change_rate')
                ),
                'latest_price': self._safe_decimal(
                    self._first_value(stock, 'latest_price', 'latest')
                ),
                'reason_type': self._safe_str(
                    self._first_value(stock, 'reason_type')
                ),
                'reason_info': self._safe_str(
                    self._first_value(stock, 'reason_info', 'reason')
                ),
                'concept': self._safe_str(
                    self._first_value(stock, 'concept')
                ),
                'market_id': self._safe_int(
                    self._first_value(stock, 'market_id'),
                    None,
                ),
                'market_type': self._safe_str(
                    self._first_value(stock, 'market_type')
                ),
                'is_new': self._safe_int(
                    self._first_value(stock, 'is_new'),
                    None,
                ),
                'is_st': self._safe_int(
                    self._first_value(stock, 'is_st'),
                    None,
                ),
                'change_tag': self._safe_str(
                    self._first_value(stock, 'change_tag')
                ),
                'raw_json': json.dumps(
                    stock,
                    ensure_ascii=False,
                    cls=DecimalEncoder,
                ),
                'sort_order': index,
            }
            self._upsert_by_keys(
                session,
                BlockTopStock,
                values,
                ('date', 'block_code', 'code'),
            )
            seen_codes.add(code)
            saved_count += 1

        stale_query = session.query(BlockTopStock).filter(
            BlockTopStock.date == target_date,
            BlockTopStock.block_code == block_code,
        )
        if seen_codes:
            stale_query = stale_query.filter(BlockTopStock.code.notin_(seen_codes))
        stale_query.delete(synchronize_session=False)
        return saved_count

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
                    code = self._safe_str(self._first_value(item, 'code', '199112'))
                    name = self._safe_str(self._first_value(item, 'name', '10'))
                    if not code or not name:
                        logger.warning(f"跳过涨停强度记录，缺少股票代码或名称: {item}")
                        failed_count += 1
                        continue

                    values = {
                        'date': target_date,
                        'code': code,
                        'name': name,
                        'latest_price': self._safe_decimal(self._first_value(item, 'latest_price', '9001')),
                        'limit_up_price': self._safe_decimal(self._first_value(item, 'limit_up_price', '330323')),
                        'change_percent': self._safe_decimal(self._first_value(item, 'change_percent', 'change_rate')),
                        'limit_up_type': self._safe_str(self._first_value(item, 'limit_up_type', '9002')),
                        'limit_up_time': self._safe_str(
                            self._first_value(
                                item,
                                'first_limit_up_time',
                                'limit_up_time',
                                '330324',
                            )
                        ),
                        'open_count': self._safe_int(item.get('open_num')),
                        'last_time': self._safe_str(
                            self._first_value(
                                item,
                                'last_limit_up_time',
                                'last_time',
                                '330329',
                            )
                        ),
                        'strength': self._safe_decimal(self._first_value(item, 'strength', '133971')),
                        'board_amount': self._safe_decimal(self._first_value(item, 'board_amount', '133970')),
                        'volume_ratio': self._safe_decimal(self._first_value(item, 'volume_ratio', '1968584')),
                        'turnover_rate': self._safe_decimal(self._first_value(item, 'turnover_rate', '3475914')),
                        'market_value': self._safe_decimal(
                            self._first_value(item, 'currency_value', 'market_value', '9003')
                        ),
                        'total_value': self._safe_decimal(self._first_value(item, 'total_value')),
                        'pe_ratio': self._safe_decimal(self._first_value(item, 'pe_ratio')),
                        'pb_ratio': self._safe_decimal(self._first_value(item, 'pb_ratio')),
                        'concept': self._safe_str(
                            self._first_value(item, 'reason_type', 'concept')
                        ),
                        'block_name': self._safe_str(self._first_value(item, 'block_name')),
                        'reason': self._safe_str(
                            self._first_value(item, 'reason_info', 'reason', '9004')
                        ),
                    }

                    self._upsert_by_keys(session, LimitUpPool, values, ('date', 'code'))
                    success_count += 1

                except Exception as e:
                    logger.error(f"保存涨停记录失败 {item.get('code')}: {e}")
                    failed_count += 1

            # 记录日志
            self._save_log(session, target_date, 'limit_up_pool', success_count)
            session.commit()
            logger.info(f"涨停强度数据保存完成: 成功{success_count}条，失败{failed_count}条")

        except Exception as e:
            session.rollback()
            logger.error(f"保存涨停强度数据失败: {e}")
            raise
        finally:
            session.close()

        return success_count, failed_count

    def save_lower_limit_pool(
        self,
        data: List[Dict[str, Any]],
        target_date: Optional[date] = None,
    ) -> Tuple[int, int]:
        """保存同花顺跌停池原始事实数据。"""
        if not target_date:
            target_date = date.today()

        success_count = 0
        failed_count = 0
        session: Session = self.Session()
        try:
            for item in data:
                try:
                    code = self._safe_str(self._first_value(item, 'code', '199112'))
                    name = self._safe_str(self._first_value(item, 'name', '10'))
                    if not code or not name:
                        logger.warning("跳过跌停池记录，缺少股票代码或名称: %s", item)
                        failed_count += 1
                        continue

                    values = {
                        'date': target_date,
                        'code': code,
                        'name': name,
                        'latest_price': self._safe_decimal(self._first_value(item, 'latest', 'latest_price', '330333')),
                        'change_percent': self._safe_decimal(self._first_value(item, 'change_rate', 'change_percent')),
                        'first_limit_down_time': self._safe_str(self._first_value(item, 'first_limit_down_time', '330333')),
                        'last_limit_down_time': self._safe_str(self._first_value(item, 'last_limit_down_time', '330334')),
                        'turnover_rate': self._safe_decimal(self._first_value(item, 'turnover_rate', '3475914')),
                        'market_value': self._safe_decimal(self._first_value(item, 'currency_value')),
                        'market_id': self._safe_int(item.get('market_id')),
                        'market_type': self._safe_str(self._first_value(item, 'market_type')),
                        'is_new': self._safe_int(item.get('is_new')),
                        'is_again_limit': self._safe_int(item.get('is_again_limit')),
                        'change_tag': self._safe_str(self._first_value(item, 'change_tag')),
                        'time_preview': json.dumps(item.get('time_preview'), ensure_ascii=False, cls=DecimalEncoder),
                        'raw_json': json.dumps(item, ensure_ascii=False, cls=DecimalEncoder),
                    }
                    self._upsert_by_keys(session, LowerLimitPool, values, ('date', 'code'))
                    success_count += 1
                except Exception as exc:
                    logger.error("保存跌停池记录失败 %s: %s", item.get('code'), exc)
                    failed_count += 1

            self._save_log(session, target_date, 'lower_limit_pool', success_count)
            session.commit()
            logger.info("同花顺跌停池保存完成: 成功%s条，失败%s条", success_count, failed_count)
        except Exception:
            session.rollback()
            logger.exception("保存同花顺跌停池失败")
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
                    values = {
                        'date': target_date,
                        'code': self._safe_str(item.get('c')),  # 东财字段：c
                        'name': self._safe_str(item.get('n')),  # 东财字段：n
                        'latest_price': self._safe_decimal(item.get('p')),  # 东财字段：p
                        'change_percent': self._safe_decimal(item.get('zdp')),  # 东财字段：zdp
                        'first_limit_up_time': self._safe_str(item.get('fbt')),  # 东财字段：fbt
                        'last_limit_up_time': self._safe_str(item.get('lbt')),  # 东财字段：lbt
                        'limit_up_type': self._safe_str(item.get('zttz')),  # 东财字段：zttz
                        'board_amount': self._safe_decimal(item.get('fund')),  # 东财字段：fund
                        'block_name': self._safe_str(item.get('hybk')),  # 东财字段：hybk
                        'reason': self._safe_str(item.get('ztzy')),  # 东财字段：ztzy
                        'volume': self._safe_int(item.get('v')),  # 东财字段：v
                        'turnover': self._safe_int(item.get('a')),  # 东财字段：a
                        'market_value': self._safe_decimal(item.get('m')),  # 东财字段：m
                        'circulating_value': self._safe_decimal(item.get('cm')),  # 东财字段：cm
                        'turnover_rate': self._safe_decimal(item.get('hs')),  # 东财字段：hs
                        'pe_ratio': self._safe_decimal(item.get('pe')),  # 东财字段：pe
                        'amplitude': self._safe_decimal(item.get('zf')),  # 东财字段：zf
                        'pre_3_day_change': self._safe_decimal(item.get('z3')),  # 东财字段：z3
                    }

                    self._upsert_by_keys(session, EastmoneyZTPool, values, ('date', 'code'))
                    success_count += 1

                except Exception as e:
                    logger.error(f"保存东财涨停记录失败 {item.get('c')}: {e}")
                    failed_count += 1

            # 记录日志
            self._save_log(session, target_date, 'eastmoney_zt_pool', success_count)
            session.commit()
            logger.info(f"东方财富涨停池数据保存完成: 成功{success_count}条，失败{failed_count}条")

        except Exception as e:
            session.rollback()
            logger.error(f"保存东方财富涨停池数据失败: {e}")
            raise
        finally:
            session.close()

        return success_count, failed_count

    def save_all_data(
        self,
        data: Dict[str, Any],
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

        if data.get('skipped'):
            reason = self._safe_str(data.get('skip_reason'), 'skipped')
            self.mark_fetch_skipped(target_date, reason)
            return {
                'continuous_limit_up': (0, 0),
                'block_top': (0, 0),
                'limit_up_pool': (0, 0),
                'lower_limit_pool': (0, 0),
                'eastmoney_zt_pool': (0, 0),
            }

        results = {}
        fetch_errors = {
            self._safe_str(item.get('type')): self._safe_str(item.get('error'))
            for item in data.get('errors', [])
            if isinstance(item, dict) and item.get('type')
        }

        def save_or_record_failure(data_type: str, save_func) -> None:
            if data_type in fetch_errors:
                self.mark_fetch_failed(target_date, data_type, fetch_errors[data_type])
                results[data_type] = (0, 1)
                return
            results[data_type] = save_func()

        # 保存连板天梯
        if 'continuous_limit_up' in data:
            save_or_record_failure(
                'continuous_limit_up',
                lambda: self.save_continuous_limit_up(
                    data['continuous_limit_up'], target_date
                ),
            )

        # 保存最强风口
        if 'block_top' in data:
            save_or_record_failure(
                'block_top',
                lambda: self.save_block_top(data['block_top'], target_date),
            )

        # 保存涨停强度
        if 'limit_up_pool' in data:
            save_or_record_failure(
                'limit_up_pool',
                lambda: self.save_limit_up_pool(data['limit_up_pool'], target_date),
            )

        if 'lower_limit_pool' in data:
            save_or_record_failure(
                'lower_limit_pool',
                lambda: self.save_lower_limit_pool(
                    data['lower_limit_pool'], target_date
                ),
            )

        # 保存东方财富涨停池
        if 'eastmoney_zt_pool' in data:
            save_or_record_failure(
                'eastmoney_zt_pool',
                lambda: self.save_eastmoney_zt_pool(
                    data['eastmoney_zt_pool'], target_date
                ),
            )

        return results

    def mark_fetch_skipped(self, target_date: date, reason: str) -> None:
        session: Session = self.Session()
        try:
            for data_type in (
                'continuous_limit_up',
                'block_top',
                'limit_up_pool',
                'lower_limit_pool',
                'eastmoney_zt_pool',
            ):
                self._save_log(
                    session,
                    target_date,
                    data_type,
                    0,
                    status='skipped',
                    error_message=reason,
                )
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def mark_fetch_failed(
        self, target_date: date, data_type: str, error_message: str
    ) -> None:
        """Persist one source failure instead of recording an empty success."""
        session: Session = self.Session()
        try:
            self._save_log(
                session,
                target_date,
                data_type,
                0,
                status='failed',
                error_message=error_message,
            )
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def is_fetch_skipped(self, target_date: date) -> bool:
        session: Session = self.Session()
        try:
            return (
                session.query(DataFetchLog)
                .filter(
                    DataFetchLog.date == target_date,
                    DataFetchLog.status == 'skipped',
                )
                .count()
                > 0
            )
        finally:
            session.close()

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
        values = {
            'date': target_date,
            'data_type': data_type,
            'status': status,
            'record_count': record_count,
            'error_message': error_message,
        }
        self._upsert_by_keys(session, DataFetchLog, values, ('date', 'data_type'))

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

            status['lower_limit_pool'] = session.query(LowerLimitPool).filter(
                LowerLimitPool.date == target_date
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
                status['limit_up_pool'] > 0,
                status['eastmoney_zt_pool'] > 0,
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
