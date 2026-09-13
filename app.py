import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import yfinance as yf
from supabase import create_client
import google.generativeai as genai

# 設定頁面標題與佈局
st.set_page_config(page_title="台股 AI 自動分析決策系統", layout="wide")

# 1. 讀取安全 Secrets 設定
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
genai.configure(api_key=GEMINI_API_KEY)

st.title("📈 台股 AI 智慧分析與籌碼決策系統")

# 側邊欄：自選股管理
st.sidebar.header("📌 自選股管理")
new_stock_input = st.sidebar.text_input("輸入股票代碼或名稱 (如: 4938 或 和碩)", "")

if st.sidebar.button("新增自選股"):
    if new_stock_input:
        # 簡單寫入 Supabase user_stocks
        supabase.table("user_stocks").upsert({"stock_id": new_stock_input, "stock_name": new_stock_input}).execute()
        st.sidebar.success(f"已新增 {new_stock_input}")
        st.rerun()

# 抓取自選股清單
user_stocks_res = supabase.table("user_stocks").select("*").execute()
user_stocks = user_stocks_res.data if user_stocks_res.data else [{"stock_id": "4938", "stock_name": "和碩"}]

# 頁面分頁設定
tab1, tab2, tab3 = st.tabs(["📊 自選股分析", "🚀 每日推薦 10 檔起漲股", "🤖 AI 智慧對話視窗"])

with tab1:
    st.subheader("我的自選股票清單")
    
    # 顯示自選股標籤與買賣訊號
    cols = st.columns(len(user_stocks) if user_stocks else 1)
    selected_stock = None
    
    # 抓取最新的 daily_analysis 數據
    today_analysis = supabase.table("daily_analysis").select("*").execute().data
    analysis_dict = {item["stock_id"]: item for item in today_analysis} if today_analysis else {}

    for idx, s in enumerate(user_stocks):
        sid = s["stock_id"]
        s_data = analysis_dict.get(sid, {})
        signal = s_data.get("signal", "觀望")
        
        # 根據訊號設定外觀
        badge = ""
        if signal == "買":
            badge = " 🔴 [買]"
        elif signal == "賣":
            badge = " ⬛ [賣]"
            
        btn_label = f"{s['stock_name']} ({sid}){badge}"
        if cols[idx % len(cols)].button(btn_label, key=f"btn_{sid}"):
            selected_stock = sid

    if not selected_stock and user_stocks:
        selected_stock = user_stocks[0]["stock_id"]

    st.markdown("---")
    
    if selected_stock:
        st.header(f"🔍 股票代碼分析：{selected_stock}")
        
        # 展示 Plotly Yahoo 技術線圖
        df = yf.download(f"{selected_stock}.TW", period="6m")
        if df.empty:
            df = yf.download(f"{selected_stock}.TWO", period="6m")
            
        if not df.empty:
            fig = go.Figure(data=[go.Candlestick(
                x=df.index,
                open=df['Open']['4938.TW'] if '4938.TW' in df['Open'] else df['Open'].iloc[:,0],
                high=df['High']['4938.TW'] if '4938.TW' in df['High'] else df['High'].iloc[:,0],
                low=df['Low']['4938.TW'] if '4938.TW' in df['Low'] else df['Low'].iloc[:,0],
                close=df['Close']['4938.TW'] if '4938.TW' in df['Close'] else df['Close'].iloc[:,0],
                name="K線"
            )])
            fig.update_layout(title=f"{selected_stock} 6個月技術線圖", yaxis_title="股價 (NTD)", template="plotly_white")
            st.plotly_chart(fig, use_container_width=True)
            
        # 呈現分析結果
        res_data = analysis_dict.get(selected_stock, {})
        if res_data:
            conf = res_data.get("confidence", 95)
            signal = res_data.get("signal", "觀望")
            
            # 信心指數標籤 (綠底白字)
            st.markdown(f"### 信心指數：<span style='background-color:green; color:white; padding:3px 8px; border-radius:5px;'>{conf}%</span>", unsafe_allow_html=True)
            
            # 買賣區間訊號標籤
            if signal == "買":
                st.markdown(f"#### 建議買進區間：<span style='background-color:red; color:yellow; padding:5px 10px; border-radius:5px;'>{res_data.get('buy_range')}</span> (安全係數>80)", unsafe_allow_html=True)
            elif signal == "賣":
                st.markdown(f"#### 建議賣出區間：<span style='background-color:black; color:white; padding:5px 10px; border-radius:5px;'>{res_data.get('sell_range')}</span> (危險係數>80)", unsafe_allow_html=True)
                
            st.markdown("#### 【技術面與籌碼面詳細分析】")
            st.write(res_data.get("analysis_text", "目前尚無今天 17:30 更新之分析內容。"))

with tab2:
    st.subheader("🚀 每日完成整理準備起漲推薦股 (信心度 > 95%)")
    st.info("系統每日 17:30 自動掃描全市場，精選 10 檔型態完成、籌碼集中度高之股票。")

with tab3:
    st.subheader("🤖 AI 智慧對話助手")
    user_query = st.text_input("輸入您想詢問的台股問題（例如：和碩的德州廠展望如何？）：")
    if st.button("發送詢問") and user_query:
        model = genai.GenerativeModel('gemini-2.5-flash')
        response = model.generate_content(user_query)
        st.write("### AI 回覆：")
        st.write(response.text)
