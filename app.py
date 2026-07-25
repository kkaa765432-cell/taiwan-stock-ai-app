import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import google.generativeai as genai

# 頁面標題與佈局設定
st.set_page_config(page_title="台股 AI 智慧分析系統", layout="wide")
st.title("📈 台股 AI 智慧分析與決策系統")

# ==========================================
# 1. 建立網頁記憶狀態 (Session State)
# 這能確保按鈕按下去時，網頁確實會記住你要搜尋的新股票
# ==========================================
if "target_stock" not in st.session_state:
    st.session_state.target_stock = "2330"

st.sidebar.header("📌 自選股管理")
# 輸入框：使用者輸入內容
user_input = st.sidebar.text_input("輸入股票代碼 (例: 2330)", st.session_state.target_stock).strip()

# 按鈕：按下後，才將輸入的內容寫入記憶中，並觸發網頁更新
if st.sidebar.button("🔍 搜尋 / 載入線圖"):
    st.session_state.target_stock = user_input

# 將要查詢的股票代碼設定為記憶中的代碼
stock_to_fetch = st.session_state.target_stock

# ==========================================
# 2. 抓取資料與視覺化呈現
# ==========================================
st.subheader(f"📊 {stock_to_fetch} 技術線圖與資料")

# 加入明確的文字提示，確保你知道按鈕有反應
st.info(f"系統正在處理 {stock_to_fetch} 的資料，請稍候...")

# 載入動畫區域
with st.spinner("連線至伺服器抓取資料中..."):
    df = None
    try:
        # 先嘗試抓取上市 (.TW)
        test_ticker_tw = f"{stock_to_fetch}.TW"
        df_temp = yf.download(test_ticker_tw, period="6m")
        if df_temp is not None and not df_temp.empty:
            df = df_temp
            actual_ticker = test_ticker_tw
        else:
            # 如果上市抓不到，自動嘗試抓取上櫃 (.TWO)
            test_ticker_two = f"{stock_to_fetch}.TWO"
            df_temp = yf.download(test_ticker_two, period="6m")
            if df_temp is not None and not df_temp.empty:
                df = df_temp
                actual_ticker = test_ticker_two
    except Exception as e:
        st.error(f"資料讀取發生錯誤: {e}")

# ==========================================
# 3. 呈現結果與 AI 分析區塊
# ==========================================
if df is not None and not df.empty:
    st.success(f"成功載入資料！系統判定為：{actual_ticker}")
    
    # 繪製 K 線圖
    fig = go.Figure(data=[go.Candlestick(
        x=df.index,
        open=df['Open'].squeeze(),
        high=df['High'].squeeze(),
        low=df['Low'].squeeze(),
        close=df['Close'].squeeze(),
        name="K線"
    )])
    fig.update_layout(title="近半年 K 線圖", xaxis_rangeslider_visible=False)
    st.plotly_chart(fig, use_container_width=True)
    
    # --- 詳細分析說明區塊 (預留版位) ---
    st.markdown(f"### 📝 {actual_ticker} 詳細分析說明")
    st.markdown("""
    **【資料來源】**：公開資訊觀測站、每月財報、相關新聞、獲得訂單與分配股利。
    
    *(以下為預留的 AI 分析欄位，待下一步串接 Gemini API 與爬蟲後將自動生成)*
    """)
    
    # 模擬未來的信心指數與買賣建議區塊
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**近期底部支撐與高點壓力**：計算中...")
        st.markdown("**綜合分析信心指數**：<span style='background-color:green;color:white;padding:2px 5px;'>等待 AI 運算 > 95%</span>", unsafe_allow_html=True)
    with col2:
        st.markdown("**買進/賣出建議區間**：")
        st.markdown("<span style='background-color:red;color:yellow;padding:2px 5px;'>安全係數計算中... (建議買進區間)</span>", unsafe_allow_html=True)
        st.markdown("<span style='background-color:black;color:white;padding:2px 5px;'>危險係數計算中... (建議賣出區間)</span>", unsafe_allow_html=True)

else:
    st.error("查無此股票資料，請確認你輸入的數字代碼是否正確。")

st.divider()
st.subheader("🤖 AI 股市諮詢助手")
user_question = st.text_input("請輸入你想詢問的股票或市場問題：")
if user_question:
    st.info("AI 正在分析中...（請於下一步設定 Gemini API Key 後啟用完整功能）")
