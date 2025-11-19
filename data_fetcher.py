"""
Data Fetcher Module (A-Share + US-Stock Support)
Features:
1. Default Fetch Range: 400 days (Natural Days)
2. Proxy: Forced to http://127.0.0.1:7897
3. Auto-detects Market (US/CN)
"""

import sys
import io
import os
import akshare as ak
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional

# ================= 配置区域 =================
# 默认获取天数改为 400 天（自然日），以确保能计算年线(MA250)
DEFAULT_DAYS = 400 
DEFAULT_ADJUST = 'qfq'

# 强制代理地址
PROXY_URL = "http://127.0.0.1:7897"
# ===========================================

class DataFetcher:
    """
    Stock Data Fetcher
    Supports:
    - China A-Shares (6-digit codes, e.g., '600519')
    - US Stocks (Ticker symbols, e.g., 'AAPL', 'NVDA')
    """

    def __init__(self, use_proxy: bool = True):
        pass

    def _force_proxy_env(self):
        """
        强制设置当前运行环境的代理，确保能连接到数据源（特别是美股）。
        """
        # 1. 清除可能干扰的 NO_PROXY
        if 'NO_PROXY' in os.environ: del os.environ['NO_PROXY']
        if 'no_proxy' in os.environ: del os.environ['no_proxy']
        
        # 2. 强制设置 HTTP 和 HTTPS 代理
        os.environ['HTTP_PROXY'] = PROXY_URL
        os.environ['HTTPS_PROXY'] = PROXY_URL
        os.environ['http_proxy'] = PROXY_URL
        os.environ['https_proxy'] = PROXY_URL

    def get_stock_data(
        self,
        symbol: str,
        days: int = DEFAULT_DAYS,
        adjust: str = DEFAULT_ADJUST,
        period: str = "daily"
    ) -> Optional[pd.DataFrame]:
        """
        Fetch historical stock data. Auto-detects A-Share vs US-Stock.
        """
        # 强制应用代理
        self._force_proxy_env()

        end_date = datetime.now()
        
        # Calculate start date
        multiplier = 1
        if period == "weekly": multiplier = 5
        elif period == "monthly": multiplier = 22
        
        # 使用传入的 days (默认400)
        start_date = end_date - timedelta(days=days * multiplier)
        
        start_date_str = start_date.strftime("%Y%m%d")
        end_date_str = end_date.strftime("%Y%m%d")

        # 判断是否为美股 (如果不全是数字，则认为是美股)
        is_us_stock = not symbol.isdigit()
        market_name = "US-Stock" if is_us_stock else "A-Share"

        print(f"Fetching {symbol} ({market_name}) from {start_date_str} ({days} days)...")

        try:
            df = None
            if is_us_stock:
                # === 美股接口 (ak.stock_us_daily) ===
                df = ak.stock_us_daily(symbol=symbol, adjust=adjust)
                
                if df is not None and not df.empty:
                    # 统一列名
                    df.rename(columns={
                        'date': 'date', 'open': 'open', 'high': 'high', 'low': 'low', 
                        'close': 'close', 'volume': 'volume'
                    }, inplace=True)
                    
                    # 过滤日期范围
                    df['date'] = pd.to_datetime(df['date'])
                    mask = (df['date'] >= start_date) & (df['date'] <= end_date)
                    df = df.loc[mask].copy()
                    
                    # 转回字符串格式 YYYY-MM-DD
                    df['date'] = df['date'].dt.strftime('%Y-%m-%d')
                    
                    # 补充缺失字段
                    if 'amount' not in df.columns: df['amount'] = df['volume'] * df['close']
                    if 'change_pct' not in df.columns: df['change_pct'] = df['close'].pct_change() * 100

            else:
                # === A股接口 (ak.stock_zh_a_hist) ===
                df = ak.stock_zh_a_hist(
                    symbol=symbol,
                    period=period,
                    start_date=start_date_str,
                    end_date=end_date_str,
                    adjust=adjust
                )
                if df is not None and not df.empty:
                    # 统一列名
                    df.rename(columns={
                        '日期': 'date', '股票代码': 'code', '开盘': 'open', '收盘': 'close', 
                        '最高': 'high', '最低': 'low', '成交量': 'volume', '成交额': 'amount', 
                        '振幅': 'amplitude', '涨跌幅': 'change_pct', '涨跌额': 'change', 
                        '换手率': 'turnover'
                    }, inplace=True)

            # === 通用数据清洗 ===
            if df is None or df.empty:
                print(f"[!] Data for {symbol} is empty. Check symbol or proxy.")
                return None

            # 确保数值列为 float 类型
            numeric_cols = ['open', 'close', 'high', 'low', 'volume', 'amount']
            for col in numeric_cols:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')

            # 确保 date 是字符串 (YYYY-MM-DD)
            if not isinstance(df['date'].iloc[0], str):
                 df['date'] = df['date'].apply(lambda x: x.strftime('%Y-%m-%d') if hasattr(x, 'strftime') else str(x))

            print(f"[OK] Successfully fetched {len(df)} rows")
            return df

        except Exception as e:
            print(f"[!] Fetch error: {e}")
            return None

    def get_stock_info(self, symbol: str) -> Optional[dict]:
        """
        Fetch stock basic info (Name, Code).
        """
        self._force_proxy_env()
        
        # 美股直接返回代码
        if not symbol.isdigit():
             return {'code': symbol, 'name': symbol}

        # A股尝试查询名称
        try:
            all_stocks = ak.stock_info_a_code_name()
            stock_info = all_stocks[all_stocks['code'] == symbol]

            if len(stock_info) == 0:
                return {'code': symbol, 'name': symbol}

            return {
                'code': symbol,
                'name': stock_info.iloc[0]['name'],
            }

        except Exception as e:
            print(f"[!] Info fetch error: {e}")
            return {'code': symbol, 'name': symbol}

    def get_stock_list(self) -> pd.DataFrame:
        """
        Get list of supported stocks (A-Share only).
        """
        self._force_proxy_env()
        try:
            return ak.stock_info_a_code_name()
        except Exception as e:
            print(f"[!] List fetch error: {e}")
            return pd.DataFrame()

if __name__ == "__main__":
    # 初始化抓取器
    fetcher = DataFetcher()
    
    # 检查是否有命令行参数 (例如: python data_fetcher.py NVDA)
    if len(sys.argv) > 1:
        user_symbol = sys.argv[1]
        print(f"\n--- Testing Symbol: {user_symbol} ---")
        
        # 使用默认的 400 天进行测试
        df = fetcher.get_stock_data(user_symbol)
        
        # 获取信息
        info = fetcher.get_stock_info(user_symbol)
        print(f"Info: {info}")
        
        if df is not None:
            print("\nData Tail:")
            print(df.tail())
        else:
            print(f"[!] Failed to fetch data for {user_symbol}")
            
    else:
        print("\nUsage: python data_fetcher.py <symbol>")
        print("No symbol provided, running default self-tests...\n")
        
        print("--- Testing US Stock (NVDA) ---")
        fetcher.get_stock_data("NVDA") # Will use default 400 days
        
        print("\n--- Testing A-Share (600000) ---")
        fetcher.get_stock_data("600000")