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
stock_input = st.sidebar.text_input("輸入股票代碼 (例: 2330.TW)", "2330.TW")

if stock_input:
    st.subheader(f"📊 {stock_input} 技術線圖與籌碼分析")
    
    # 抓取股票資料
    df = yf.download(stock_input, period="6m")
    
    if not df.empty:
        # 繪制 K 線圖
        fig = go.Figure(data=[go.Candlestick(
            x=df.index,
            open=df['Open'],
            high=df['High'],
            low=df['Low'],
            close=df['Close'],
            name="K線"
        )])
        fig.update_layout(title="近半年 K 線圖", xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.error("查無此股票資料，請確認代碼是否正確（台股請加上 .TW）。")

# AI 對話視窗
st.hr()
st.subheader("🤖 AI 股市諮詢助手")
user_question = st.text_input("請輸入你想詢問的股票或市場問題：")
if user_question:
    st.info("AI 正在分析中...（請於下一步設定 Gemini API Key 後啟用完整功能）")
