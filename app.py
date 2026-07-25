import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import google.generativeai as genai

# 頁面標題與佈局設定
st.set_page_config(page_title="台股 AI 智慧分析系統", layout="wide")

st.title("📈 台股 AI 智慧分析與決策系統")

# 側邊欄：自選股管理
st.sidebar.header("📌 自選股管理")

# 改良1：只需要輸入數字，使用 .strip() 自動清除多餘空白
stock_input = st.sidebar.text_input("輸入股票代碼 (例: 2330)", "2330").strip()

# 改良2：用最單純的按鈕觸發更新，避免表單鎖死問題
update_btn = st.sidebar.button("🔍 搜尋 / 載入線圖")

if stock_input:
    st.subheader(f"📊 {stock_input} 技術線圖與資料")
    
    # 加上讀取動畫，讓你知道系統有在做事
    with st.spinner("資料抓取中，請稍候..."):
        # 邏輯：先嘗試抓取上市 (.TW) 資料
        test_ticker_tw = f"{stock_input}.TW"
        df = yf.download(test_ticker_tw, period="6m")
        actual_ticker = test_ticker_tw
        
        # 如果上市抓不到，自動嘗試抓取上櫃 (.TWO) 資料
        if df is None or df.empty:
            test_ticker_two = f"{stock_input}.TWO"
            df = yf.download(test_ticker_two, period="6m")
            actual_ticker = test_ticker_two
    
    # 判斷最終是否成功抓到資料
    if df is not None and not df.empty:
        st.success(f"成功載入資料！系統自動判定為：{actual_ticker}")
        
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
    else:
        st.error("查無此股票資料，請確認你輸入的數字代碼是否正確。")

st.divider()

st.subheader("🤖 AI 股市諮詢助手")
user_question = st.text_input("請輸入你想詢問的股票或市場問題：")
if user_question:
    st.info("AI 正在分析中...（請於下一步設定 Gemini API Key 後啟用完整功能）")
