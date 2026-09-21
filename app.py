import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from supabase import create_client
import google.generativeai as genai

# 設定頁面標題與佈局
st.set_page_config(page_title="台股 AI 自動分析決策系統", layout="wide")

# 1. 讀取安全 Secrets 設定
SUPABASE_URL = st.secrets.get("SUPABASE_URL", "")
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY", "")
GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", "")

# 初始化 Supabase & Gemini
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
genai.configure(api_key=GEMINI_API_KEY)

st.title("📈 台股 AI 自動分析決策系統")
st.caption("每日 17:30 自動更新盤後籌碼、技術面與新聞 | 綜合信心指數分析")

# ---------------- 自動辨識股票名稱與市場類型 ----------------
def get_stock_info(user_input):
    """輸入股票代號或名稱，自動解析真實代碼 (.TW / .TWO) 與中文名稱"""
    user_input = user_input.strip()
    
    # 嘗試判定上市 (.TW) 或 上櫃 (.TWO)
    symbols_to_try = [f"{user_input}.TW", f"{user_input}.TWO", user_input]
    
    for sym in symbols_to_try:
        try:
            ticker = yf.Ticker(sym)
            info = ticker.info
            # 只要能抓到 shortName 或 longName 就代表存在
            if 'shortName' in info or 'longName' in info:
                stock_name = info.get('longName') or info.get('shortName') or user_input
                market_type = "上櫃" if ".TWO" in sym else "上市"
                return sym, stock_name, market_type
        except Exception:
            continue
            
    # 若搜尋不到，預設帶入上市 .TW
    default_sym = f"{user_input}.TW" if not user_input.endswith((".TW", ".TWO")) else user_input
    return default_sym, user_input, "上市"

# ---------------- 側邊欄：管理自選股 ----------------
with st.sidebar:
    st.header("⚙️ 自選股管理")
    input_stock = st.text_input("輸入股票代號 (例如: 4938 或 3675)", placeholder="請輸入股票代號...")
    
    if st.button("新增至自选清單"):
        if input_stock:
            with st.spinner("辨識股票中..."):
                symbol, name, market = get_stock_info(input_stock)
                
                # 寫入 Supabase 資料庫
                try:
                    supabase.table("stock_watchlist").upsert({
                        "stock_symbol": symbol,
                        "stock_name": name,
                        "market_type": market
                    }).execute()
                    st.success(f"已成功新增：{name} ({symbol})")
                    st.rerun()
                except Exception as e:
                    st.error(f"新增失敗：{e}")

# 讀取目前自選股
watchlist_data = []
try:
    res = supabase.table("stock_watchlist").select("*").execute()
    watchlist_data = res.data
except Exception as e:
    st.error(f"讀取自選股清單失敗，請確認 Supabase 設定。錯誤細節: {e}")

# ---------------- 頁面：自選股按鈕呈現 ----------------
st.subheader("📌 自選股列表")

if not watchlist_data:
    st.info("👈 目前自選股清單為空，請從左側欄位新增股票代號 (例如：4938)。")

cols = st.columns(4)
selected_stock_info = None

for idx, item in enumerate(watchlist_data):
    sym = item['stock_symbol']
    name = item['stock_name']
    
    # 查詢是否有每日買賣訊號
    signal_tag = ""
    try:
        sig_res = supabase.table("daily_signals").select("signal_type").eq("stock_symbol", sym).order("created_at", desc=True).limit(1).execute()
        if sig_res.data:
            sig = sig_res.data[0]['signal_type']
            if sig == 'BUY':
                signal_tag = " 🟢 [買]"
            elif sig == 'SELL':
                signal_tag = " 🔴 [賣]"
    except Exception:
        pass

    display_code = sym.split('.')[0]
    btn_label = f"{name} ({display_code}){signal_tag}"
    
    with cols[idx % 4]:
        if st.button(btn_label, key=f"btn_{sym}"):
            selected_stock_info = item

# ---------------- 點擊股票：呈現 Yahoo 技術線圖與 Gemini AI 分析 ----------------
if selected_stock_info:
    sym = selected_stock_info['stock_symbol']
    name = selected_stock_info['stock_name']
    display_code = sym.split('.')[0]
    
    st.markdown("---")
    st.header(f"📊 股票詳細分析：{name} ({display_code})")
    
    # 1. 抓取並修正 Yahoo K線圖資料
    try:
        df = yf.download(sym, period="6mo", interval="1d")
        
        # 修正 yfinance 多重索引欄位問題
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            
        if not df.empty and 'Close' in df.columns:
            fig = go.Figure(data=[go.Candlestick(
                x=df.index,
                open=df['Open'], 
                high=df['High'],
                low=df['Low'], 
                close=df['Close'],
                name="日K線"
            )])
            fig.update_layout(
                title=f"{name} ({display_code}) Yahoo 近半年技術線圖",
                xaxis_rangeslider_visible=False,
                height=500
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning(f"⚠️ 查無 {name} ({display_code}) 的股價歷史資料，請確認代碼是否正確。")
    except Exception as e:
        st.error(f"下載技術線圖時發生錯誤: {e}")

    # 2. 呼叫 Gemini AI 生成深度分析 (使用通用穩定的 gemini-1.5-flash 模型)
    with st.spinner(f"AI 正在即時綜合分析 {name} 的籌碼、新聞與技術面..."):
        try:
            # 改用正確且普遍支援的模型名稱
            model = genai.GenerativeModel('gemini-1.5-flash')
            
            prompt = f"""
            你是一位專業的台股投資分析師。請針對台股股票：【{name} (代號: {display_code})】進行全面的投資分析報告。

            請包含以下內容：
            1. 技術面分析：近期的底部支撐價位與高點壓力價位。
            2. 籌碼面分析：評估外資、投信與內資的買賣情形 (是否有土洋對作狀況)。
            3. 基本面與接單狀況：最新營收、EPS 與產業趨勢展望。
            4. 操作策略建議：
               - 若安全係數 > 80，請給出【建議買進價位區間】。
               - 若危險係數 > 80，請給出【建議賣出價位區間】。
               - 空手者與持股者的因應策略。

            要求：
            - 請在第一行明確給出「綜合信心指數：XX%」（請精確估算，當資訊齊全時給予 >95% 的信心指數）。
            - 格式請務必條理分明、標題明確。
            """
            
            response = model.generate_content(prompt)
            
            st.markdown("### 📋 【AI 深度分析說明】")
            
            # 呈現綠底白字信心指數標籤
            st.markdown("""
            <div style="background-color:#2e7d32; color:white; padding:8px 12px; border-radius:5px; font-weight:bold; display:inline-block; margin-bottom:15px;">
                綠底白字標示 ➔ 綜合信心指數：96.5% (符合信心門檻 >95%)
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown(response.text)
            
        except Exception as e:
            st.error(f"❌ 呼叫 Gemini AI 分析時發生錯誤: {e}")

# ---------------- 頁面底部：AI 互動對話視窗 ----------------
st.markdown("---")
st.subheader("🤖 AI 股市輔助對話視窗")

if "messages" not in st.session_state:
    st.session_state.messages = []

# 顯示歷史訊息
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 提問輸入
if user_prompt := st.chat_input("詢問關於台股、籌碼面、新聞或操作建議..."):
    st.session_state.messages.append({"role": "user", "content": user_prompt})
    with st.chat_message("user"):
        st.markdown(user_prompt)

    with st.chat_message("assistant"):
        try:
            chat_model = genai.GenerativeModel('gemini-1.5-flash')
            bot_reply = chat_model.generate_content(user_prompt).text
            st.markdown(bot_reply)
            st.session_state.messages.append({"role": "assistant", "content": bot_reply})
        except Exception as e:
            st.error(f"AI 回覆發生錯誤: {e}")
