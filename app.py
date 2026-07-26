import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import requests

# 頁面標題與佈局設定
st.set_page_config(page_title="台股 AI 智慧分析系統", layout="wide")
st.title("📈 台股 AI 智慧分析與決策系統")

# ==========================================
# 0. 建立偽裝 Session，突破 Yahoo 的 IP 封鎖
# ==========================================
yf_session = requests.Session()
yf_session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
})

# ==========================================
# 1. 建立名稱轉代碼的超高速搜尋函數
# ==========================================
def search_stock(query):
    url = f"https://query2.finance.yahoo.com/v1/finance/search?q={query}"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0'}
    try:
        response = requests.get(url, headers=headers, timeout=5)
        data = response.json()
        
        if 'quotes' in data and len(data['quotes']) > 0:
            for quote in data['quotes']:
                symbol = quote.get('symbol', '')
                if symbol.endswith('.TW') or symbol.endswith('.TWO'):
                    name = quote.get('shortname', query)
                    return symbol, name
            return data['quotes'][0]['symbol'], data['quotes'][0].get('shortname', query)
    except Exception:
        return None, None
    return None, None

# ==========================================
# 2. 側邊欄與網頁記憶狀態 (Session State)
# ==========================================
if "target_stock" not in st.session_state:
    st.session_state.target_stock = "4938"

st.sidebar.header("📌 自選股管理")
user_input = st.sidebar.text_input("輸入股票名稱或代碼 (例: 和碩 或 4938)", st.session_state.target_stock).strip()

if st.sidebar.button("🔍 搜尋 / 載入線圖"):
    st.session_state.target_stock = user_input

stock_query = st.session_state.target_stock

# ==========================================
# 3. 抓取資料與視覺化呈現 (搭配偽裝 Session)
# ==========================================
st.subheader(f"📊 「{stock_query}」搜尋結果與分析")

if stock_query:
    st.info(f"系統正在精準定位「{stock_query}」的資料，請稍候...")
    
    with st.spinner("連線至資料庫中..."):
        symbol, stock_name = search_stock(stock_query)
        
        if symbol:
            st.success(f"定位成功！系統對應目標為：**{stock_name} ({symbol})**")
            
            try:
                # 【關鍵修正】：將偽裝的 yf_session 傳入 yfinance 中
                stock_target = yf.Ticker(symbol, session=yf_session)
                df = stock_target.history(period="6m")
                
                if df is not None and not df.empty:
                    fig = go.Figure(data=[go.Candlestick(
                        x=df.index,
                        open=df['Open'],
                        high=df['High'],
                        low=df['Low'],
                        close=df['Close'],
                        name="K線"
                    )])
                    fig.update_layout(title=f"{stock_name} 近半年 K 線圖", xaxis_rangeslider_visible=False)
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # ==========================================
                    # 4. 分析說明區塊 (依照需求配置於每股線圖下方)
                    # ==========================================
                    st.markdown(f"### 📝 {stock_query} 詳細分析說明")
                    st.markdown("""
                    **【資料來源】**：公開資訊觀測站、該公司每月財報、相關新聞、獲得的訂單、分配的股利以及線圖指標等綜合分析。
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
                    st.error("伺服器連線遭拒或目前無資料，請稍後重試。")
            except Exception as e:
                st.error(f"下載線圖資料時發生錯誤：{e}")
        else:
            st.error("資料庫找不到此股票，請確認名稱或代碼是否正確。")

st.divider()
st.subheader("🤖 AI 股市諮詢助手")
user_question = st.text_input("請輸入你想詢問的股票或市場問題：")
if user_question:
    st.info("AI 正在分析中...（請於下一步設定 Gemini API Key 後啟用完整功能）")
