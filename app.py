import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import yfinance as yf
from supabase import create_client
import google.generativeai as genai
import re

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

# 常用股票中文名稱對應表
STOCK_NAME_TO_CODE = {
    "德微": "3675",
    "和碩": "4938",
    "台積電": "2330",
    "鴻海": "2317",
    "聯發科": "2454",
    "廣達": "2382",
    "緯創": "3231",
}

# 建立反向對照表（代碼 -> 名稱）
CODE_TO_STOCK_NAME = {v: k for k, v in STOCK_NAME_TO_CODE.items()}

def extract_stock_code(input_str):
    """ 從輸入字串自動過濾出純數字股票代碼 """
    input_str = str(input_str).strip()
    # 先查對照表
    if input_str in STOCK_NAME_TO_CODE:
        return STOCK_NAME_TO_CODE[input_str]
    # 使用正則表達式擷取數字
    digits = re.findall(r'\d+', input_str)
    if digits:
        return digits[0]
    return input_str

def get_stock_display_name(code):
    """ 取得股票顯示名稱 (如: 4938 和碩) """
    code = extract_stock_code(code)
    name = CODE_TO_STOCK_NAME.get(code, "")
    return f"{name} ({code})" if name else code

@st.cache_data(ttl=3600)
def fetch_stock_data(stock_code):
    """ 抓取台股股價歷史資料 (.TW 上市 / .TWO 上櫃備援) """
    for suffix in [".TW", ".TWO"]:
        ticker = f"{stock_code}{suffix}"
        try:
            # progress=False 避免輸出雜訊
            data = yf.download(ticker, period="6m", progress=False)
            if not data.empty and len(data) > 0:
                # 簡化 MultiIndex 欄位 (yfinance 新版常出現 MultiIndex)
                if isinstance(data.columns, pd.MultiIndex):
                    data.columns = data.columns.get_level_values(0)
                # 確保欄位包含 Open, High, Low, Close
                if {'Open', 'High', 'Low', 'Close'}.issubset(data.columns):
                    return data
        except Exception:
            continue
    return pd.DataFrame()

st.title("📈 台股 AI 智慧分析與籌碼決策系統")

# 初始化 Session State
if "selected_stock" not in st.session_state:
    st.session_state["selected_stock"] = "4938"

# 側邊欄：自選股管理
st.sidebar.header("📌 自選股管理")
new_stock_input = st.sidebar.text_input("輸入股票代碼或名稱 (如: 3675 或 德微)", "").strip()

if st.sidebar.button("新增自選股"):
    if new_stock_input:
        stock_code = extract_stock_code(new_stock_input)
        stock_name = CODE_TO_STOCK_NAME.get(stock_code, new_stock_input)
        if supabase:
            try:
                supabase.table("user_stocks").upsert({
                    "stock_id": stock_code, 
                    "stock_name": stock_name
                }).execute()
                st.sidebar.success(f"已新增 {stock_name} ({stock_code})")
                st.rerun()
            except Exception as e:
                st.sidebar.error(f"新增自選股失敗: {e}")
        else:
            st.sidebar.warning("Supabase 未連線，僅示範操作。")

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
            
    analysis_dict = {str(item["stock_id"]): item for item in today_analysis} if today_analysis else {}

    # 顯示自選股按鈕 (每行最多 5 個)
    MAX_COLS = 5
    cols = st.columns(min(len(user_stocks), MAX_COLS))

    for idx, s in enumerate(user_stocks):
        raw_sid = str(s["stock_id"])
        sid = extract_stock_code(raw_sid)
        s_name = s.get("stock_name", CODE_TO_STOCK_NAME.get(sid, sid))
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
        
        if col_target.button(btn_label, key=f"btn_{sid}_{idx}"):
            st.session_state["selected_stock"] = sid

    selected_code = extract_stock_code(st.session_state["selected_stock"])
    display_title = get_stock_display_name(selected_code)

    st.markdown("---")
    
    if selected_code:
        st.header(f"🔍 股票分析：{display_title}")
        
        # 抓取 K 線數據（帶 Cache）
        df = fetch_stock_data(selected_code)
            
        if not df.empty:
            open_price = df['Open']
            high_price = df['High']
            low_price = df['Low']
            close_price = df['Close']

            # 抓取最新一個交易日數據
            last_date = df.index[-1].strftime('%Y-%m-%d')
            last_close = float(close_price.iloc[-1])
            last_open = float(open_price.iloc[-1])
            last_high = float(high_price.iloc[-1])
            last_low = float(low_price.iloc[-1])

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
                title=f"{display_title} 近 6 個月技術線圖", 
                yaxis_title="股價 (NTD)", 
                template="plotly_white",
                xaxis_rangeslider_visible=False
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.error(f"❌ 查無 {display_title} 的股價歷史資料，請確認代碼是否正確。")
            
        # 呈現分析結果
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
            
            if GEMINI_API_KEY:
                with st.spinner("🤖 正在調用 Gemini AI 即時分析最新交易資料中..."):
                    try:
                        if not df.empty:
                            recent_df = df.tail(5)
                            summary_str = f"最後交易日: {last_date}, 最新收盤價: {last_close:.2f}\n近五日走勢:\n{recent_df[['Open', 'High', 'Low', 'Close']].to_string()}"
                        else:
                            summary_str = f"目前暫無 yfinance 歷史 K 線數據，請基於 {display_title} 近期的市場基本面與籌碼概況進行分析。"

                        # 使用 gemini-1.5-flash
                        model = genai.GenerativeModel('gemini-1.5-flash')
                        prompt = f"你是一位專業台股分析師。請針對股票『{display_title}』進行短線與中長線技術面、籌碼面分析，說明當前趨勢、支撐壓力位與操作建議：\n\n{summary_str}"
                        
                        response = model.generate_content(prompt)
                        st.markdown("#### 【Gemini AI 即時分析報告】")
                        st.write(response.text)
                    except Exception as e:
                        st.error(f"即時 AI 分析失敗：{e}")
            else:
                st.warning("請先設定 Streamlit Secrets 中的 GEMINI_API_KEY 以開啟即時 AI 分析。")

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
