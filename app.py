import os
import re
import json
import requests
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime, timedelta
import streamlit as st
import google.generativeai as genai

# --- 1. 頁面基本配置 ---
st.set_page_config(
    page_title="台股 AI 智慧分析與投資決策系統",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. 載入 API Key 與設定 ---
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY") or st.secrets.get("GEMINI_API_KEY", "")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

WATCHLIST_FILE = "watchlist.json"

# --- 3. 智能股票名稱與代號自動查詢引擎 ---
@st.cache_data(ttl=86400)
def lookup_stock_info(query):
    query = query.strip()
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
    
    # 1. 嘗試 Yahoo 股市搜尋 API
    try:
        url = f"https://tw.stock.yahoo.com/_td-stock/api/resource/stocksearch;keyword={query}"
        res = requests.get(url, headers=headers, timeout=5)
        if res.status_code == 200:
            data = res.json()
            hits = data.get('hits', [])
            for item in hits:
                symbol = item.get('symbol', '')
                name = item.get('name', '')
                code = item.get('code', '')
                if (symbol.endswith('.TW') or symbol.endswith('.TWO')) and code:
                    return name, symbol, code
    except:
        pass

    # 2. 備用網頁爬蟲查詢
    try:
        url = f"https://tw.stock.yahoo.com/quote/{query}"
        res = requests.get(url, headers=headers, timeout=5)
        if res.status_code == 200:
            match = re.search(r'<title>(.*?)\s*\(([\d]{4,6})\.(TW|TWO)\)', res.text)
            if match:
                name = match.group(1).strip()
                code = match.group(2)
                market = match.group(3)
                return name, f"{code}.{market}", code
    except:
        pass

    return None, None, None

def load_watchlist():
    if os.path.exists(WATCHLIST_FILE):
        try:
            with open(WATCHLIST_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    return [{"code": "2330.TW", "name": "台積電"}, {"code": "2317.TW", "name": "鴻海"}]

def save_watchlist(watchlist):
    with open(WATCHLIST_FILE, "w", encoding="utf-8") as f:
        json.dump(watchlist, f, ensure_ascii=False, indent=2)

def fetch_stock_data(ticker_symbol):
    """
    直連 API 抓取 6 個月歷史 K 線數據 (解決雲端伺服器 IP 被阻擋的問題)
    """
    ticker_symbol = ticker_symbol.strip().upper()
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
    
    # 嘗試清單（先搜原檔名，若無則切換 .TW / .TWO）
    symbols_to_try = [ticker_symbol]
    if ticker_symbol.endswith(".TW"):
        symbols_to_try.append(ticker_symbol.replace(".TW", ".TWO"))
    elif ticker_symbol.endswith(".TWO"):
        symbols_to_try.append(ticker_symbol.replace(".TWO", ".TW"))

    # 方法一：Yahoo v8 API 直連（最穩定且快速）
    for sym in symbols_to_try:
        try:
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}?range=6m&interval=1d"
            res = requests.get(url, headers=headers, timeout=5)
            if res.status_code == 200:
                data = res.json()
                result = data['chart']['result'][0]
                timestamps = result['timestamp']
                quote = result['indicators']['quote'][0]
                
                df = pd.DataFrame({
                    'Open': quote['open'],
                    'High': quote['high'],
                    'Low': quote['low'],
                    'Close': quote['close'],
                    'Volume': quote['volume']
                }, index=pd.to_datetime(timestamps, unit='s'))
                
                df = df.dropna()
                if not df.empty:
                    return df, {}, sym
        except:
            pass

    # 方法二：yfinance 套件備用
    for sym in symbols_to_try:
        try:
            stock = yf.Ticker(sym)
            df = stock.history(period="6m")
            if not df.empty:
                return df, {}, sym
        except:
            pass

    return pd.DataFrame(), {}, ticker_symbol

def fetch_stock_news(query):
    try:
        url = f"https://news.google.com/rss/search?q={query}+台股+股票&hl=zh-TW&gl=TW&ceid=TW:zh-Hant"
        res = requests.get(url, timeout=5)
        from xml.etree import ElementTree as ET
        root = ET.fromstring(res.content)
        news_items = []
        for item in root.findall('.//item')[:5]:
            title = item.find('title').text if item.find('title') is not None else ""
            link = item.find('link').text if item.find('link') is not None else ""
            news_items.append({"title": title, "link": link})
        return news_items
    except:
        return []

def run_gemini_analysis(stock_name, stock_code, df, info, news):
    if not GEMINI_API_KEY:
        return {
            "confidence": 0, "safety_score": 0, "danger_score": 0,
            "support": "未設定 API Key", "pressure": "未設定 API Key",
            "buy_range": "", "sell_range": "",
            "summary": "請先至 Streamlit 或 GitHub Secrets 設定 GEMINI_API_KEY。",
            "action": "無"
        }

    recent_data = df.tail(10).to_string()
    news_text = "\n".join([n['title'] for n in news])
    
    prompt = f"""
你是一位專業的台股資深分析師。請針對【{stock_name} ({stock_code})】進行深度技術分析與綜合研判。

近10日交易數據：
{recent_data}

相關新聞與市場消息：
{news_text}

請輸出 JSON 格式（不要包含 markdown 標籤或文字說明以外的內容）：
{{
  "confidence": 綜合信心指數整數(0-100),
  "safety_score": 安全係數整數(0-100, >80 代表低檔安全買點),
  "danger_score": 危險係數整數(0-100, >80 代表高檔過熱賣點),
  "support": "近期底部支撐價位說明",
  "pressure": "近期高點壓力價位說明",
  "buy_range": "建議買進價位區間 (若安全係數<=80請填寫無)",
  "sell_range": "建議賣出價位區間 (若危險係數<=80請填寫無)",
  "summary": "詳細技術線圖與消息面分析說明",
  "action": "訊號動作 ('買', '賣', 或 '觀望')"
}}
"""
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt)
        text = response.text.replace("```json", "").replace("
