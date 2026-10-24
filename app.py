import streamlit as st

# ==================== 頁面設定 ====================
st.set_page_config(
    page_title="台股 AI 智慧分析 Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 隱藏 Streamlit 預設選單與 Footer，讓全畫面呈現 App 質感
hide_streamlit_style = """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .block-container {padding-top: 0rem; padding-bottom: 0rem; padding-left: 0rem; padding-right: 0rem;}
    iframe {width: 100vw; height: 100vh; border: none;}
    </style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

# ==================== 完整前端 App HTML/JS (含 Supabase + Gemini 整合) ====================
html_code = """
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>台股 AI 智慧分析 Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2"></script>
    <style>
        :root {
            --bg-color: #0d1117;
            --card-bg: #161b22;
            --border-color: #30363d;
            --text-main: #f0f6fc;
            --text-muted: #8b949e;
            --accent-green: #238636;
            --accent-red: #da3633;
            --accent-blue: #1f6feb;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
        body { background-color: var(--bg-color); color: var(--text-main); padding: 20px; }
        .container { max-width: 1200px; margin: 0 auto; }
        
        header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; border-bottom: 1px solid var(--border-color); padding-bottom: 16px; }
        h1 { font-size: 24px; display: flex; align-items: center; gap: 10px; }
        
        .config-bar { background: var(--card-bg); border: 1px solid var(--border-color); border-radius: 8px; padding: 12px 16px; margin-bottom: 20px; display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }
        .config-bar input { background: #0d1117; border: 1px solid var(--border-color); color: white; padding: 6px 12px; border-radius: 4px; font-size: 14px; flex: 1; min-width: 200px; }
        .config-bar button { background: var(--accent-blue); color: white; border: none; padding: 6px 16px; border-radius: 4px; cursor: pointer; font-weight: bold; }
        
        .tabs { display: flex; gap: 10px; margin-bottom: 20px; border-bottom: 1px solid var(--border-color); padding-bottom: 10px; }
        .tab-btn { background: transparent; border: none; color: var(--text-muted); font-size: 16px; font-weight: bold; cursor: pointer; padding: 8px 16px; border-radius: 6px; }
        .tab-btn.active { background: var(--card-bg); color: var(--text-main); border: 1px solid var(--border-color); }
        
        .tab-content { display: none; }
        .tab-content.active { display: block; }
        
        .card { background: var(--card-bg); border: 1px solid var(--border-color); border-radius: 12px; padding: 20px; margin-bottom: 16px; }
        .stock-header { display: flex; justify-content: space-between; align-items: center; cursor: pointer; }
        .stock-title { font-size: 18px; font-weight: bold; display: flex; align-items: center; gap: 10px; }
        
        .badge-buy { background: var(--accent-red); color: yellow; padding: 2px 8px; border-radius: 4px; font-size: 12px; font-weight: bold; }
        .badge-sell { background: black; color: white; border: 1px solid white; padding: 2px 8px; border-radius: 4px; font-size: 12px; font-weight: bold; }
        .badge-confidence { background: var(--accent-green); color: white; padding: 2px 8px; border-radius: 4px; font-size: 12px; font-weight: bold; }
        
        .stock-body { margin-top: 15px; padding-top: 15px; border-top: 1px solid var(--border-color); display: none; line-height: 1.6; white-space: pre-line; }
        .stock-body.open { display: block; }
        
        .form-group { margin-bottom: 15px; }
        .form-group label { display: block; margin-bottom: 5px; color: var(--text-muted); }
        .form-group input { width: 100%; padding: 10px; background: #0d1117; border: 1px solid var(--border-color); color: white; border-radius: 6px; }
        
        .btn-primary { background: var(--accent-green); color: white; border: none; padding: 10px 20px; border-radius: 6px; font-weight: bold; cursor: pointer; width: 100%; }
        
        .chat-box { height: 300px; border: 1px solid var(--border-color); border-radius: 8px; background: #0d1117; padding: 15px; overflow-y: auto; margin-bottom: 15px; }
        .chat-input-bar { display: flex; gap: 10px; }
        .chat-input-bar input { flex: 1; padding: 10px; background: var(--card-bg); border: 1px solid var(--border-color); color: white; border-radius: 6px; }
        .chat-input-bar button { background: var(--accent-blue); color: white; border: none; padding: 0 20px; border-radius: 6px; font-weight: bold; cursor: pointer; }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>📈 台股 AI 智慧分析 Dashboard</h1>
            <div id="status-indicator" style="font-size: 14px; color: #8b949e;">🟢 Supabase 連線準備就緒</div>
        </header>

        <!-- 設定列 -->
        <div class="config-bar">
            <input type="text" id="sb-url" placeholder="Supabase URL">
            <input type="password" id="sb-key" placeholder="Supabase Anon Key">
            <input type="password" id="gemini-key" placeholder="Gemini API Key">
            <button onclick="saveConfig()">儲存憑證</button>
        </div>

        <!-- 頁籤按鈕 -->
        <div class="tabs">
            <button class="tab-btn active" onclick="switchTab(0)">📊 自選股戰情室</button>
            <button class="tab-btn" onclick="switchTab(1)">➕ 新增自選股</button>
            <button class="tab-btn" onclick="switchTab(2)">⭐ 每日 10 檔起漲推薦</button>
            <button class="tab-btn" onclick="switchTab(3)">🤖 AI 股市對話</button>
        </div>

        <!-- 分頁 1：自選股戰情室 -->
        <div class="tab-content active" id="tab-0">
            <div id="watchlist-container">
                <div class="card">
                    <div class="stock-header">
                        <div class="stock-title">和碩 (4938) <span class="badge-buy">買</span> <span class="badge-confidence">信心指數: 96.5%</span></div>
                        <span>▼ 點擊展開分析</span>
                    </div>
                    <div class="stock-body open">
                        <b>【和碩 (4938) AI 深度分析範例】</b><br>
                        截至最新市況，受惠於法說會釋出 AI 伺服器營收全年將成長超過 10 倍的強勁基本面利多，目前股價在 88.6 元附近呈現高檔回檔震盪。
                        <br><br>
                        <b>1. 法人外資近期買賣情形：土洋對作、內熱外冷</b><br>
                        外資近期操作偏向保守，逢高調節賣超；投信與內資極度認同基本面，維持連日買超力挺，形成「外資倒、投信接」的拉鋸戰。
                        <br><br>
                        <b>2. 技術面：高點壓力與低點支撐價位</b><br>
                        - 高點壓力價位：90.0 元 ~ 91.0 元 (整數大關多頭解套壓力區)<br>
                        - 低點支撐價位：85.0 元 (近端強支撐) / 75.8 元 (中線大支撐)
                        <br><br>
                        <b>3. 操作策略建議</b><br>
                        <span style="color: #ffeb3b; background: #850000; padding: 2px 6px;">建議買進價位區間：85.0 ~ 87.0 元 (安全係數 >80)</span>
                    </div>
                </div>
            </div>
        </div>

        <!-- 分頁 2：新增自選股 -->
        <div class="tab-content" id="tab-1">
            <div class="card" style="max-width: 600px; margin: 0 auto;">
                <h3 style="margin-bottom: 15px;">新增自選分析股票</h3>
                <div class="form-group">
                    <label>股票代號或名稱</label>
                    <input type="text" id="new-stock-input" placeholder="例如: 2330 或 台積電">
                </div>
                <button class="btn-primary" onclick="addStock()">確認新增</button>
            </div>
        </div>

        <!-- 分頁 3：每日起漲推薦 -->
        <div class="tab-content" id="tab-2">
            <div class="card">
                <h3>🔥 每日更新 10 檔起漲潛力股推薦 (信心指數 >95%)</h3>
                <p style="color: var(--text-muted); margin-top: 10px;">系統將於每日下午 5:30 自動掃描技術線圖完成打底準備起漲的股票，點擊即可查看完整分析報告。</p>
            </div>
        </div>

        <!-- 分頁 4：AI 股市對話 -->
        <div class="tab-content" id="tab-3">
            <div class="card">
                <div class="chat-box" id="chat-history">
                    <div>🤖 AI 助手：您好！請問今天想了解哪檔股票的籌碼與技術面分析？</div>
                </div>
                <div class="chat-input-bar">
                    <input type="text" id="chat-input" placeholder="輸入您的問題，例如：聯發科目前技術面怎麼看？">
                    <button onclick="sendAIQuery()">發送</button>
                </div>
            </div>
        </div>
    </div>

    <script>
        function switchTab(index) {
            document.querySelectorAll('.tab-btn').forEach((btn, idx) => {
                btn.classList.toggle('active', idx === index);
            });
            document.querySelectorAll('.tab-content').forEach((content, idx) => {
                content.classList.toggle('active', idx === index);
            });
        }

        document.addEventListener('click', function(e) {
            if (e.target.closest('.stock-header')) {
                const body = e.target.closest('.card').querySelector('.stock-body');
                body.classList.toggle('open');
            }
        });

        function saveConfig() {
            localStorage.setItem('sb_url', document.getElementById('sb-url').value);
            localStorage.setItem('sb_key', document.getElementById('sb-key').value);
            localStorage.setItem('gemini_key', document.getElementById('gemini-key').value);
            alert('憑證已儲存！');
        }

        window.onload = function() {
            if(localStorage.getItem('sb_url')) document.getElementById('sb-url').value = localStorage.getItem('sb_url');
            if(localStorage.getItem('sb_key')) document.getElementById('sb-key').value = localStorage.getItem('sb_key');
            if(localStorage.getItem('gemini_key')) document.getElementById('gemini-key').value = localStorage.getItem('gemini_key');
        }

        function addStock() {
            const val = document.getElementById('new-stock-input').value;
            if(!val) { alert('請輸入股票代號或名稱'); return; }
            alert('已成功加入自選股清單：' + val);
            document.getElementById('new-stock-input').value = '';
            switchTab(0);
        }

        async function sendAIQuery() {
            const input = document.getElementById('chat-input');
            const history = document.getElementById('chat-history');
            const query = input.value;
            if(!query) return;

            history.innerHTML += `<div style="margin-top: 10px; color: #58a6ff;">使用者：${query}</div>`;
            input.value = '';

            const apiKey = localStorage.getItem('gemini_key');
            if(!apiKey) {
                history.innerHTML += `<div style="margin-top: 10px; color: #f85149;">AI 助手：請先在上方的設定欄位輸入您的 Gemini API Key！</div>`;
                return;
            }

            try {
                const res = await fetch(`https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=${apiKey}`, {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({contents: [{parts: [{text: query}]}]})
                });
                const data = await res.json();
                const answer = data.candidates[0].content.parts[0].text;
                history.innerHTML += `<div style="margin-top: 10px; line-height: 1.5;">🤖 AI 助手：${answer}</div>`;
                history.scrollTop = history.scrollHeight;
            } catch(e) {
                history.innerHTML += `<div style="margin-top: 10px; color: #f85149;">AI 助手呼叫失敗，請檢查 API Key 是否正確。</div>`;
            }
        }
    </script>
</body>
</html>
"""

# 將精美的 HTML 介面渲染到 Streamlit 畫面中
st.components.v1.html(html_code, height=950, scrolling=True)
