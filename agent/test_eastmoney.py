"""
测试东方财富涨停池接口
验证两步调用流程：先获取tc，再拉取全部数据
"""

import asyncio
import json
import logging
from datetime import date

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

from chain.stock.data.fetcher import StockDataFetcher


async def test_eastmoney_zt_pool():
    """测试东方财富涨停池接口"""
    target_date = "20260412"

    logger.info(f"开始测试东方财富涨停池接口: date={target_date}")

    async with StockDataFetcher() as fetcher:
        try:
            # 调用新的方法
            data = await fetcher.fetch_eastmoney_zt_pool(
                target_date=target_date,
                sort="fbt:asc"
            )

            logger.info(f"成功获取数据: 共{len(data)}条记录")

            # 打印前3条数据作为示例
            if data:
                logger.info("\n前3条数据示例:")
                for i, item in enumerate(data[:3], 1):
                    logger.info(f"\n记录 {i}:")
                    logger.info(f"  代码: {item.get('c', 'N/A')}")
                    logger.info(f"  名称: {item.get('n', 'N/A')}")
                    logger.info(f"  最新价: {item.get('p', 'N/A')}")
                    logger.info(f"  涨跌幅: {item.get('zdp', 'N/A')}")
                    logger.info(f"  涨停时间: {item.get('fbt', 'N/A')}")
                    logger.info(f"  封单金额: {item.get('fund', 'N/A')}万元")
                    logger.info(f"  所属板块: {item.get('hybk', 'N/A')}")
                    logger.info(f"  涨停原因: {item.get('zttz', 'N/A')}")

            return data

        except Exception as e:
            logger.error(f"测试失败: {e}")
            raise


def test_sync():
    """同步方式测试"""
    from chain.stock.data import create_fetcher

    logger.info("使用同步方式测试...")
    fetcher = create_fetcher()

    try:
        data = fetcher.fetch_eastmoney_zt_pool("20260412")
        logger.info(f"同步方式成功: 共{len(data)}条记录")
        return data
    except Exception as e:
        logger.error(f"同步测试失败: {e}")
        raise


if __name__ == "__main__":
    import sys

    # 默认运行异步测试
    test_type = sys.argv[1] if len(sys.argv) > 1 else "async"

    if test_type == "async":
        logger.info("运行异步测试...")
        asyncio.run(test_eastmoney_zt_pool())
    elif test_type == "sync":
        test_sync()
    else:
        print("用法: python test_eastmoney.py [async|sync]")
