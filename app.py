import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import yfinance as yf
from supabase import create_client
import google.generativeai as genai

# 設定頁面標題與佈局
st.set_page_config(page_title="台股 AI 自動分析決策系統", layout="wide")

# 1. 讀取安全 Secrets 設定
SUPABASE_URL = st.secrets.get("SUPABASE_URL", "")
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY", "")
GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", "")

# 初始化 Supabase 與 Gemini
supabase = create_client(SUPABASE_URL, SUPABASE_KEY) if SUPABASE_URL and SUPABASE_KEY else None
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

# 常用股票名稱對應表 (擴充輸入中文時自動換算代碼)
STOCK_NAME_TO_CODE = {
    "德微": "3675",
    "和碩": "4938",
    "台積電": "2330",
    "鴻海": "2317",
    "聯發科": "2454",
    "廣達": "2382",
    "緯創": "3231",
}

st.title("📈 台股 AI 智慧分析與籌碼決策系統")

# 初始化 Session State
if "selected_stock" not in st.session_state:
    st.session_state["selected_stock"] = "4938"

# 側邊欄：自選股管理
st.sidebar.header("📌 自選股管理")
new_stock_input = st.sidebar.text_input("輸入股票代碼或名稱 (如: 3675 或 德微)", "").strip()

if st.sidebar.button("新增自選股"):
    if new_stock_input:
        # 轉換中文名為代碼
        stock_code = STOCK_NAME_TO_CODE.get(new_stock_input, new_stock_input)
        if supabase:
            supabase.table("user_stocks").upsert({
                "stock_id": stock_code, 
                "stock_name": new_stock_input
            }).execute()
            st.sidebar.success(f"已新增 {new_stock_input} ({stock_code})")
            st.rerun()

# 抓取自選股清單
user_stocks = []
if supabase:
    try:
        user_stocks_res = supabase.table("user_stocks").select("*").execute()
        user_stocks = user_stocks_res.data if user_stocks_res.data else []
    except Exception as e:
        st.sidebar.error(f"讀取自選股失敗: {e}")

if not user_stocks:
    user_stocks = [
        {"stock_id": "4938", "stock_name": "和碩"},
        {"stock_id": "3675", "stock_name": "德微"}
    ]

# 頁面分頁設定
tab1, tab2, tab3 = st.tabs(["📊 自選股分析", "🚀 每日推薦 10 檔起漲股", "🤖 AI 智慧對話視窗"])

with tab1:
    st.subheader("我的自選股票清單")
    
    # 抓取最新的 daily_analysis 數據
    today_analysis = []
    if supabase:
        try:
            today_analysis = supabase.table("daily_analysis").select("*").execute().data
        except Exception:
            today_analysis = []
            
    analysis_dict = {item["stock_id"]: item for item in today_analysis} if today_analysis else {}

    # 顯示自選股按鈕 (每行最多 5 個)
    MAX_COLS = 5
    cols = st.columns(min(len(user_stocks), MAX_COLS))

    for idx, s in enumerate(user_stocks):
        sid = s["stock_id"]
        s_name = s.get("stock_name", sid)
        s_data = analysis_dict.get(sid, {})
        signal = s_data.get("signal", "觀望")
        
        # 根據訊號設定外觀
        badge = ""
        if signal == "買":
            badge = " 🔴 [買]"
        elif signal == "賣":
            badge = " ⬛ [賣]"
            
        btn_label = f"{s_name} ({sid}){badge}"
        col_target = cols[idx % MAX_COLS]
        
        if col_target.button(btn_label, key=f"btn_{sid}"):
            st.session_state["selected_stock"] = sid

    selected_raw = st.session_state["selected_stock"]
    # 取得標準代碼 (如: 輸入「德微」轉成「3675」)
    selected_code = STOCK_NAME_TO_CODE.get(selected_raw, selected_raw)

    st.markdown("---")
    
    if selected_code:
        st.header(f"🔍 股票分析：{selected_raw} ({selected_code})")
        
        # 抓取技術線圖資料 (依次嘗試 上櫃 .TWO 與 上市 .TW)
        df = pd.DataFrame()
        for suffix in [".TWO", ".TW"]:
            ticker = f"{selected_code}{suffix}"
            data = yf.download(ticker, period="6m", progress=False)
            if not data.empty:
                df = data
                break
            
        if not df.empty:
            # 處理 MultiIndex 欄位 (yfinance 新版回傳格式變更)
            if isinstance(df.columns, pd.MultiIndex):
                open_price = df['Open'].iloc[:, 0]
                high_price = df['High'].iloc[:, 0]
                low_price = df['Low'].iloc[:, 0]
                close_price = df['Close'].iloc[:, 0]
            else:
                open_price = df['Open']
                high_price = df['High']
                low_price = df['Low']
                close_price = df['Close']

            # 顯示最後交易日與價格
            last_date = df.index[-1].strftime('%Y-%m-%d')
            last_close = close_price.iloc[-1]
            last_open = open_price.iloc[-1]
            last_high = high_price.iloc[-1]
            last_low = low_price.iloc[-1]

            st.success(
                f"📅 **最後交易日**：{last_date} ｜ "
                f"**收盤價**：{last_close:.2f} 元 ｜ "
                f"**開盤**：{last_open:.2f} ｜ "
                f"**最高**：{last_high:.2f} ｜ "
                f"**最低**：{last_low:.2f}"
            )

            # 繪製 K 線圖
            fig = go.Figure(data=[go.Candlestick(
                x=df.index,
                open=open_price,
                high=high_price,
                low=low_price,
                close=close_price,
                name="K線"
            )])
            fig.update_layout(
                title=f"{selected_raw} ({selected_code}) 近 6 個月技術線圖", 
                yaxis_title="股價 (NTD)", 
                template="plotly_white",
                xaxis_rangeslider_visible=False
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning(f"⚠️ 查無 {selected_raw} ({selected_code}) 的股價歷史資料，請確認代碼或名稱是否正確。")
            
        # 呈現 Supabase 分析結果，若無資料則現場調用 Gemini 備援
        res_data = analysis_dict.get(selected_code, {})
        if res_data:
            conf = res_data.get("confidence", 95)
            signal = res_data.get("signal", "觀望")
            
            # 信心指數標籤
            st.markdown(f"### 信心指數：<span style='background-color:#28a745; color:white; padding:3px 8px; border-radius:5px;'>{conf}%</span>", unsafe_html=True)
            
            # 買賣區間訊號標籤
            if signal == "買":
                st.markdown(f"#### 建議買進區間：<span style='background-color:#dc3545; color:white; padding:5px 10px; border-radius:5px;'>{res_data.get('buy_range', '未提供')}</span> (安全係數>80)", unsafe_html=True)
            elif signal == "賣":
                st.markdown(f"#### 建議賣出區間：<span style='background-color:#343a40; color:white; padding:5px 10px; border-radius:5px;'>{res_data.get('sell_range', '未提供')}</span> (危險係數>80)", unsafe_html=True)
                
            st.markdown("#### 【技術面與籌碼面詳細分析】")
            st.write(res_data.get("analysis_text", "目前尚無今天 17:30 更新之分析內容。"))
        else:
            st.info("ℹ️ 資料庫尚無該股票今日之預算分析，啟動 Gemini AI 即時備援分析：")
            
            if GEMINI_API_KEY and not df.empty:
                with st.spinner("🤖 正在根據最後交易資料生成 AI 分析，請稍候..."):
                    try:
                        # 取最近 5 個交易日資料
                        recent_df = df.tail(5)
                        summary_str = f"最後交易日: {last_date}, 最新收盤價: {last_close:.2f}\n近五日走勢:\n{recent_df[['Open', 'High', 'Low', 'Close']].to_string()}"
                        
                        model = genai.GenerativeModel('gemini-1.5-flash')
                        prompt = f"你是一位專業台股分析師。請針對股票『{selected_raw} ({selected_code})』的最新交易數據進行短線技術面分析，說明當前趨勢、支撐壓力位與操作建議：\n\n{summary_str}"
                        
                        response = model.generate_content(prompt)
                        st.markdown("#### 【Gemini AI 即時分析報告】")
                        st.write(response.text)
                    except Exception as e:
                        st.error(f"即時 AI 分析失敗：{e}")
            elif not GEMINI_API_KEY:
                st.warning("未設定 GEMINI_API_KEY，無法提供即時 AI 備援分析。")

with tab2:
    st.subheader("🚀 每日完成整理準備起漲推薦股 (信心度 > 95%)")
    st.info("系統每日 17:30 自動掃描全市場，精選 10 檔型態完成、籌碼集中度高之股票。")

with tab3:
    st.subheader("🤖 AI 智慧對話助手")
    user_query = st.text_input("輸入您想詢問的台股問題（例如：德微的車用半導體展望如何？）：")
    
    if st.button("發送詢問") and user_query:
        if not GEMINI_API_KEY:
            st.error("請先設定 Streamlit Secrets 中的 GEMINI_API_KEY！")
        else:
            with st.spinner("AI 分析中，請稍候..."):
                try:
                    model = genai.GenerativeModel('gemini-1.5-flash')
                    response = model.generate_content(user_query)
                    st.write("### AI 回覆：")
                    st.write(response.text)
                except Exception as e:
                    st.error(f"Gemini API 呼叫失敗: {e}")
