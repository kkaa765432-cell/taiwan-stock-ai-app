import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import google.generativeai as genai

# 頁面標題與佈局設定
st.set_page_config(page_title="台股 AI 智慧分析系統", layout="wide")

st.title("📈 台股 AI 智慧分析與決策系統")

# 側邊欄：自選股管理 (加入表單與按鈕，解決無法輸入/沒反應的問題)
st.sidebar.header("📌 自選股管理")
st.sidebar.markdown("💡 **提示**：上市股票請加 `.TW`，上櫃股票請加 `.TWO`")

# 建立一個表單，使用者必須點擊按鈕才會送出資料
with st.sidebar.form(key='stock_search_form'):
    stock_input = st.text_input("輸入股票代碼 (例: 2330.TW)", "2330.TW")
    submit_button = st.form_submit_button(label="🔍 搜尋 / 載入線圖")

# 當按下按鈕，或是表單內有預設值時執行
if submit_button or stock_input:
    st.subheader(f"📊 {stock_input} 技術線圖與籌碼分析")
    
    # 抓取股票資料
    df = yf.download(stock_input, period="6m")
    
    # 判斷資料是否為空
    if df is not None and not df.empty:
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
        st.error("查無此股票資料，請確認代碼是否正確（上市請加上 .TW，上櫃請加上 .TWO）。")

st.divider()

st.subheader("🤖 AI 股市諮詢助手")
user_question = st.text_input("請輸入你想詢問的股票或市場問題：")
if user_question:
    st.info("AI 正在分析中...（請於下一步設定 Gemini API Key 後啟用完整功能）")
