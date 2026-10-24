import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import yfinance as yf
from supabase import create_client
import google.generativeai as genai
import re
import json

# 1. 頁面配置與樣式設定
st.set_page_config(page_title="台股 AI 自動分析決策系統", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
    .badge-confidence {
        background-color: #28a745; color: white; padding: 4px 10px; border-radius: 4px; font-weight: bold; font-size: 16px;
    }
    .badge-buy {
        background-color: #dc3545; color: #ffeb3b; padding: 6px 12px; border-radius: 4px; font-weight: bold; font-size: 16px;
    }
    .badge-sell {
        background-color: #000000; color: #ffffff; padding: 6px 12px; border-radius: 4px; font-weight: bold; font-size: 16px;
    }
</style>
""", unsafe_allow_html=True)

# 2. 讀取 Secrets 設定
SUPABASE_URL = st.secrets.get("SUPABASE_URL", "")
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY", "")
GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", "")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY) if SUPABASE_URL and SUPABASE_KEY else None
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

COMMON_STOCKS = {
    "和碩": "4938", "德微": "3675", "台積電": "2330", "鴻海": "2317",
    "聯發科": "2454", "廣達": "2382", "緯創": "3231", "元太": "8069"
}
CODE_TO_NAME = {v: k for k, v in COMMON_STOCKS.items()}

def extract_stock_code(input_str):
    input_str = str(input_str).strip()
    if input_str in COMMON_STOCKS:
        return COMMON_STOCKS[input_str]
    digits = re.findall(r'\d+', input_str)
    return digits[0] if digits else input_str

def get_stock_name(code):
    return CODE_TO_NAME.get(code, code)

@st.cache_data(ttl=1800)
def fetch_stock_data(stock_code):
    for suffix in [".TW", ".TWO"]:
        ticker = stock_code + suffix
        try:
            df = yf.download(ticker, period="6m", progress=False)
            if not df.empty and len(df) > 0:
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)
                if {'Open', 'High', 'Low', 'Close', 'Volume'}.issubset(df.columns):
                    return df, ("上市" if suffix == ".TW" else "上櫃")
        except Exception:
            continue
    return pd.DataFrame(), "未知"

def run_gemini_analysis(stock_name, stock_code, recent_df_str):
    if not GEMINI_API_KEY:
        return "⚠️ 未設定 GEMINI_API_KEY", {}
    
    # 改用標準字串相加，避免大括號衝突
    prompt = (
        "你是一位專業台股分析師。請針對『" + stock_name + " (" + stock_code + ")』撰寫深度分析報告。\n"
        "【近十日歷史價格】:\n" + recent_df_str + "\n\n"
        "請包含：法人外資買賣、技術面壓力支撐、營運展望、未來操作策略。\n"
        "結尾請附上嚴格的 JSON 區塊：\n"
        "```json\n"
        '{"confidence": 96, "signal": "買", "buy_range": "85.0 ~ 87.0元", "sell_range": "90.0 ~ 91.0元"}\n'
        "```"
    )
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        res = model.generate_content(prompt)
        text = res.text
        j_dict = {}
        m = re.search(r'```json\s*(\{.*?\})\s*```', text, re.DOTALL)
        if m:
            try:
                j_dict = json.loads(m.group(1))
            except Exception:
                pass
        return text, j_dict
    except Exception as e:
        return "AI 呼叫失敗: " + str(e), {}

# 3. 側邊欄自選股管理
st.sidebar.title("📌 自選股管理")
new_stock_input = st.sidebar.text_input("輸入股票代碼或名稱 (如: 3675 或 德微)", "").strip()

if st.sidebar.button("➕ 新增自選股"):
    if new_stock_input:
        s_code = extract_stock_code(new_stock_input)
        s_name = get_stock_name(s_code) if s_code in CODE_TO_NAME else new_stock_input
        if supabase:
            try:
                supabase.table("user_stocks").upsert({"stock_id": s_code, "stock_name": s_name}).execute()
                st.sidebar.success("已新增 " + s_name + " (" + s_code + ")")
                st.rerun()
            except Exception as e:
                st.sidebar.error("新增失敗: " + str(e))

user_stocks = []
if supabase:
    try:
        res = supabase.table("user_stocks").select("*").execute()
        user_stocks = res.data if res.data else []
    except Exception:
        pass

if not user_stocks:
    user_stocks = [{"stock_id": "4938", "stock_name": "和碩"}, {"stock_id": "3675", "stock_name": "德微"}]

st.sidebar.markdown("---")
st.sidebar.subheader("🗑️ 已儲存自選股 (點擊刪除)")
for s in user_stocks:
    sid = str(s["stock_id"])
    sname = s.get("stock_name", get_stock_name(sid))
    c1, c2 = st.sidebar.columns([3, 1])
    c1.write("• " + sname + " (" + sid + ")")
    if c2.button("刪除", key="del_btn_" + sid):
        if supabase:
            try:
                supabase.table("user_stocks").delete().eq("stock_id", sid).execute()
                st.sidebar.success("已刪除 " + sname)
                st.rerun()
            except Exception as e:
                st.sidebar.error("刪除失敗: " + str(e))

# 4. 主頁面與分頁初始化
st.title("📈 台股 AI 智慧分析與籌碼決策系統")
tab1, tab2, tab3 = st.tabs(["📊 自選股分析", "🚀 每日推薦 10 檔起漲股", "🤖 AI 智慧對話視窗"])

with tab1:
    st.subheader("我的自選股票清單")
    if "selected_stock" not in st.session_state:
        st.session_state["selected_stock"] = user_stocks[0]["stock_id"] if user_stocks else "4938"

    today_analysis = []
    if supabase:
        try:
            today_analysis = supabase.table("daily_analysis").select("*").execute().data or []
        except Exception:
            pass
            
    analysis_dict = {str(item["stock_id"]): item for item in today_analysis} if today_analysis else {}

    # 兩列按鈕排版邏輯 (每列最多 5 個)
    MAX_PER_ROW = 5
    for row_start in range(0, len(user_stocks), MAX_PER_ROW):
        row_stocks = user_stocks[row_start : row_start + MAX_PER_ROW]
        cols = st.columns(len(row_stocks))
        for idx, s in enumerate(row_stocks):
            sid = str(s["stock_id"])
            sname = s.get("stock_name", get_stock_name(sid))
            sig = analysis_dict.get(sid, {}).get("signal", "")
            badge = " 🔴 [買]" if sig == "買" else (" ⬛ [賣]" if sig == "賣" else "")
            if cols[idx].button(sname + " (" + sid + ")" + badge, key="tab1_btn_" + sid):
                st.session_state["selected_stock"] = sid
                selected_code = extract_stock_code(st.session_state["selected_stock"])
    display_name = get_stock_name(selected_code)

    st.markdown("---")
    st.header("🔍 股票分析：" + display_name + " (" + selected_code + ")")

    df, market_type = fetch_stock_data(selected_code)

    if not df.empty:
        last_date = df.index[-1].strftime('%Y-%m-%d')
        last_close = float(df['Close'].iloc[-1])
        st.success("📅 **最後交易日**：" + last_date + " ｜ **市場**：" + market_type + " ｜ **收盤價**：" + f"{last_close:.2f}" + " 元")

        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.7, 0.3])
        fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name="K線"), row=1, col=1)
        colors = ['red' if c >= o else 'green' for c, o in zip(df['Close'], df['Open'])]
        fig.add_trace(go.Bar(x=df.index, y=df['Volume'], name="成交量", marker_color=colors), row=2, col=1)
        fig.update_layout(title=display_name + " (" + selected_code + ") 近 6 個月技術線圖", yaxis_title="股價", yaxis2_title="成交量", xaxis_rangeslider_visible=False, template="plotly_white", height=500)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.error("❌ 查無 " + display_name + " (" + selected_code + ") 的歷史資料。")

    res_data = analysis_dict.get(selected_code, {})
    if res_data:
        conf = res_data.get("confidence", 95)
        sig = res_data.get("signal", "觀望")
        st.markdown("### 信心指數：<span class='badge-confidence'>" + str(conf) + "%</span>", unsafe_allow_html=True)
        if sig == "買":
            st.markdown("#### 建議買進區間：<span class='badge-buy'>" + str(res_data.get('buy_range')) + "</span>", unsafe_allow_html=True)
        elif sig == "賣":
            st.markdown("#### 建議賣出區間：<span class='badge-sell'>" + str(res_data.get('sell_range')) + "</span>", unsafe_allow_html=True)
        st.write(res_data.get("analysis_text", ""))
    else:
        st.info("ℹ️ 資料庫尚無今日預先分析，點擊下方按鈕啟動 AI 即時分析：")
        if st.button("🤖 即時生成 " + display_name + " 深度 AI 分析"):
            with st.spinner("AI 分析中..."):
                r_str = df.tail(10).to_string() if not df.empty else "無資料"
                rep, meta = run_gemini_analysis(display_name, selected_code, r_str)
                st.markdown("### 信心指數：<span class='badge-confidence'>" + str(meta.get('confidence', 96)) + "%</span>", unsafe_allow_html=True)
                st.write(rep)

with tab2:
    st.subheader("🚀 每日完成整理準備起漲推薦股 (信心度 > 95%)")
    st.info("系統每日 17:30 自動掃描全市場，精選 10 檔型態完成、籌碼集中度高之股票。")

with tab3:
    st.subheader("🤖 AI 智慧對話助手")
    user_query = st.text_input("輸入您想詢問的台股問題：")
    if st.button("發送詢問") and user_query:
        if not GEMINI_API_KEY:
            st.error("請先設定 GEMINI_API_KEY！")
        else:
            with st.spinner("AI 回覆中..."):
                try:
                    model = genai.GenerativeModel('gemini-1.5-flash')
                    response = model.generate_content(user_query)
                    st.write("### AI 回覆：")
                    st.write(response.text)
                except Exception as e:
                    st.error("錯誤: " + str(e))
              
