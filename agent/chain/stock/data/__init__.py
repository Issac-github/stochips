"""
数据模块

包含数据抓取和存储功能
"""

from .fetcher import StockDataFetcher, StockDataFetcherSync, create_fetcher
from .storage import StockDataStorage, create_storage

__all__ = [
    'StockDataFetcher',
    'StockDataFetcherSync',
    'create_fetcher',
    'StockDataStorage',
    'create_storage',
    'EastmoneyZTPool',
]
