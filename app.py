import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import google.generativeai as genai
import requests

# 頁面標題與佈局設定
st.set_page_config(page_title="台股 AI 智慧分析系統", layout="wide")
st.title("📈 台股 AI 智慧分析與決策系統")

# ==========================================
# 1. 建立名稱轉代碼的超高速搜尋函數
# ==========================================
def search_stock(query):
    """透過 API 瞬間將中文名稱或數字轉換為正確的股票代碼"""
    url = f"https://query2.finance.yahoo.com/v1/finance/search?q={query}"
    # 加上偽裝標頭，避免被伺服器阻擋
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/91.0'}
    try:
        response = requests.get(url, headers=headers, timeout=5)
        data = response.json()
        
        if 'quotes' in data and len(data['quotes']) > 0:
            for quote in data['quotes']:
                symbol = quote.get('symbol', '')
                # 優先篩選台灣股市 (.TW 或 .TWO)
                if symbol.endswith('.TW') or symbol.endswith('.TWO'):
                    name = quote.get('shortname', query)
                    return symbol, name
            # 如果找不到台股，回傳第一個結果
            return data['quotes'][0]['symbol'], data['quotes'][0].get('shortname', query)
    except Exception:
        return None, None
    return None, None

# ==========================================
# 2. 側邊欄與網頁記憶狀態 (Session State)
# ==========================================
if "target_stock" not in st.session_state:
    st.session_state.target_stock = "台積電"

st.sidebar.header("📌 自選股管理")
# 讓使用者可以輸入名稱或代碼
user_input = st.sidebar.text_input("輸入股票名稱或代碼 (例: 台積電 或 2330)", st.session_state.target_stock).strip()

if st.sidebar.button("🔍 搜尋 / 載入線圖"):
    st.session_state.target_stock = user_input

stock_query = st.session_state.target_stock

# ==========================================
# 3. 抓取資料與視覺化呈現
# ==========================================
st.subheader(f"📊 「{stock_query}」搜尋結果與分析")

if stock_query:
    st.info(f"系統正在精準定位「{stock_query}」的資料，請稍候...")
    
    with st.spinner("連線至資料庫中..."):
        # 步驟 A: 將名稱轉換為代碼 (瞬間完成)
        symbol, stock_name = search_stock(stock_query)
        
        if symbol:
            st.success(f"定位成功！系統對應目標為：**{stock_name} ({symbol})**")
            
            # 步驟 B: 下載線圖資料 (直接下載正確代碼，解決卡頓問題)
            try:
                # progress=False 避免在終端機印出雜訊導致減速
                df = yf.download(symbol, period="6m", progress=False)
                
                if df is not None and not df.empty:
                    # 繪製 K 線圖
                    fig = go.Figure(data=[go.Candlestick(
                        x=df.index,
                        open=df['Open'].squeeze(),
                        high=df['High'].squeeze(),
                        low=df['Low'].squeeze(),
                        close=df['Close'].squeeze(),
                        name="K線"
                    )])
                    fig.update_layout(title=f"{stock_name} 近半年 K 線圖", xaxis_rangeslider_visible=False)
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # ==========================================
                    # 4. 分析說明區塊 (依照需求放置於每股線圖下方)
                    # ==========================================
                    st.markdown(f"### 📝 {stock_name} 詳細分析說明")
                    st.markdown("""
                    **【資料來源】**：公開資訊觀測站、該公司每月財報、相關新聞、獲得的訂單、分配的股利以及線圖指標。
                    """)
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown("**近期底部支撐與高點壓力**：等待 AI 判讀...")
                        st.markdown("**綜合分析信心指數**：<span style='background-color:green;color:white;padding:2px 5px;'>等待 AI 運算 > 95%</span>", unsafe_allow_html=True)
                    with col2:
                        st.markdown("**買進/賣出建議區間**：")
                        st.markdown("<span style='background-color:red;color:yellow;padding:2px 5px;'>安全係數計算中... (建議買進區間)</span>", unsafe_allow_html=True)
                        st.markdown("<span style='background-color:black;color:white;padding:2px 5px;'>危險係數計算中... (建議賣出區間)</span>", unsafe_allow_html=True)
                else:
                    st.error("此股票目前無近半年的交易資料。")
            except Exception as e:
                st.error("下載線圖資料時發生錯誤，請稍後再試。")
        else:
            st.error("資料庫找不到此股票，請確認名稱或代碼是否正確。")

st.divider()
st.subheader("🤖 AI 股市諮詢助手")
user_question = st.text_input("請輸入你想詢問的股票或市場問題：")
if user_question:
    st.info("AI 正在分析中...（請於下一步設定 Gemini API Key 後啟用完整功能）")
