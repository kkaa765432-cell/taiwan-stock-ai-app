import os
import datetime
import json
import yfinance as yf
import google.generativeai as genai
from supabase import create_client, Client

# 1. 初始化環境變數
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.5-flash')

def get_stock_data(stock_id):
    """抓取 yfinance 技術面與籌碼面基本資料"""
    ticker_symbol = f"{stock_id}.TW"
    stock = yf.Ticker(ticker_symbol)
    
    # 若上市沒抓到，嘗試上櫃 (.TWO)
    hist = stock.history(period="6m")
    if hist.empty:
        ticker_symbol = f"{stock_id}.TWO"
        stock = yf.Ticker(ticker_symbol)
        hist = stock.history(period="6m")
        
    if hist.empty:
        return None

    # 最新收盤資訊
    latest = hist.iloc[-1]
    prev_close = hist.iloc[-2]['Close'] if len(hist) > 1 else latest['Close']
    
    # 籌碼與法人資料 (yfinance 近期 institutional_holders / major_holders)
    info = stock.info
    
    data_summary = {
        "stock_id": stock_id,
        "name": info.get("shortName", stock_id),
        "current_price": round(latest['Close'], 2),
        "high_52w": info.get("fiftyTwoWeekHigh", "N/A"),
        "low_52w": info.get("fiftyTwoWeekLow", "N/A"),
        "volume": int(latest['Volume']),
        "pe_ratio": info.get("forwardPE", "N/A"),
        "pb_ratio": info.get("priceToBook", "N/A"),
        "recent_history": hist.tail(10).to_dict()
    }
    return data_summary

def fetch_ai_learning_context():
    """檢索 Supabase 中過去 AI 自主學習的歷史經驗，供本次分析參考"""
    res = supabase.table("ai_learning_memory").select("*").order("created_at", desc=True).limit(5).execute()
    memory_text = ""
    if res.data:
        memory_text = "【過去預測校正與自主學習經驗】:\n" + "\n".join(
            [f"- 股票{m['stock_id']}: 預測{m['predicted_signal']}，檢討：{m['reflection_notes']}" for m in res.data]
        )
    return memory_text

def analyze_stock_with_gemini(stock_data, learning_context):
    """呼叫 Gemini 2.5 Flash 進行信心度 >95% 的籌碼與技術面深度分析"""
    
    prompt = f"""
你是一位勝率極高的台股籌碼與技術面分析專家。請依據以下個股最新數據與學習經驗進行深度綜合分析。

{learning_context}

個股數據：
- 股票代碼與名稱：{stock_data['stock_id']} ({stock_data['name']})
- 當前股價：{stock_data['current_price']}
- 近期最高/最低：{stock_data['high_52w']} / {stock_data['low_52w']}
- 本益比(PE)/股價淨值比(PB)：{stock_data['pe_ratio']} / {stock_data['pb_ratio']}
- 近10日走勢數據：{stock_data['recent_history']}

請嚴格遵循以下輸出格式規範（以 JSON 格式回應）：
{{
  "confidence": 96, // 綜合分析信心指數 (必須為數字，若分析完整度高且符合強勢/築底條件請給出 >95 的數值)
  "signal": "買", // 填寫 "買"、"賣" 或 "觀望" (當安全係數>80時給"買"，危險係數>80時給"賣")
  "buy_range": "85.0 元 ～ 87.0 元", // 若建議買進區間，否則填 "無"
  "sell_range": "90.0 元 ～ 91.0 元", // 若建議賣出區間，否則填 "無"
  "support_price": "85.0 元 (近端) / 75.8 元 (中線)",
  "pressure_price": "90.0 元 ～ 91.0 元",
  "analysis_text": "請詳細撰寫法人外資買賣情形（土洋對作狀況）、技術面高點壓力與低點支撐價位解析、近期接單與營運展望、以及未來3大具體操作策略。"
}}
"""

    response = model.generate_content(
        prompt,
        generation_config={"response_mime_type": "application/json"}
    )
    return json.loads(response.text)

def run_daily_pipeline():
    """每日 17:30 執行的主要自動化流程"""
    today = datetime.date.today().isoformat()
    learning_context = fetch_ai_learning_context()
    
    # 1. 抓取使用者設定的自選股
    user_stocks_res = supabase.table("user_stocks").select("stock_id").execute()
    stock_list = [item['stock_id'] for item in user_stocks_res.data]
    
    # 如果自選股為空，預設包含和碩 (4938) 與台積電 (2330)
    if not stock_list:
        stock_list = ["4938", "2330"]
        
    for stock_id in stock_list:
        data = get_stock_data(stock_id)
        if data:
            analysis = analyze_stock_with_gemini(data, learning_context)
            # 存入 Supabase 每日分析表
            record = {
                "date": today,
                "stock_id": stock_id,
                "confidence": analysis.get("confidence", 95),
                "signal": analysis.get("signal", "觀望"),
                "buy_range": analysis.get("buy_range", "無"),
                "sell_range": analysis.get("sell_range", "無"),
                "support_price": analysis.get("support_price", ""),
                "pressure_price": analysis.get("pressure_price", ""),
                "analysis_text": analysis.get("analysis_text", ""),
                "is_top10": False
            }
            supabase.table("daily_analysis").upsert(record).execute()
            print(f"[{stock_id}] 分析完成並已儲存。")

if __name__ == "__main__":
    run_daily_pipeline()
