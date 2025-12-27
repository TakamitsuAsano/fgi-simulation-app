import streamlit as st
from openai import OpenAI
import pandas as pd
import datetime
import time

# --- ページ設定 ---
st.set_page_config(page_title="AI FGI Simulator", layout="wide")

st.title("👥 AI Focus Group Interview Simulator")
st.markdown("""
設定したペルソナとAIモデレーターによるFGIシミュレーションアプリです。
設定した「所要時間」に合わせて、AIが議論のペース配分（導入→深掘り→まとめ）をコントロールします。
""")

# --- サイドバー設定 ---
with st.sidebar:
    st.header("🔧 設定")
    
    # APIキー設定（Secrets優先、なければ手入力）
    if "OPENAI_API_KEY" in st.secrets:
        api_key = st.secrets["OPENAI_API_KEY"]
    else:
        api_key = st.text_input("OpenAI API Key", type="password")

    if not api_key:
        st.warning("APIキーが設定されていません。")
        st.stop()
    
    client = OpenAI(api_key=api_key)

    # テーマ設定
    topic = st.text_input("インタビューのテーマ", value="新しいコーヒーブランドのコンセプト受容性")
    
    # 時間設定（New!）
    target_duration = st.slider("想定インタビュー時間（分）", 30, 120, 60, step=10)
    
    # モデレーターの設定
    moderator_style = st.slider("モデレーターの深掘り度", 1, 5, 2, help="1:雑談重視 ↔ 5:分析重視")
    
    # 参加者設定
    default_participants = """
田中さん: 40歳、既婚、子供1人（7歳小学一年生女子）。キャリアウーマンで年収800万。忙しいが週末は家族との時間を大切にしたい。少し疲れ気味。
佐藤さん: 28歳、独身、男性。IT企業勤務、年収500万。趣味はキャンプとサウナ。効率重視だが、アナログな体験も好き。
鈴木さん: 55歳、既婚、子供独立済み。専業主婦。夫と二人暮らし。健康と老後の資金が悩み。時間はたっぷりある。
"""
    participants_input = st.text_area("参加者プロファイル", value=default_participants.strip(), height=200)

    # リセットボタン
    if st.button("設定を保存してリセット"):
        st.session_state.messages = []
        st.session_state.turn_count = 0
        st.session_state.participants_data = {}
        
        # 参加者情報のパース
        lines = participants_input.strip().split('\n')
        for line in lines:
            if ":" in line:
                name, profile = line.split(":", 1)
                st.session_state.participants_data[name.strip()] = profile.strip()
        st.success("リセットしました")

# --- セッション状態の初期化 ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "turn_count" not in st.session_state:
    st.session_state.turn_count = 0 # ターン数をカウント
if "participants_data" not in st.session_state:
    st.session_state.participants_data = {}
    lines = participants_input.strip().split('\n')
    for line in lines:
        if ":" in line:
            name, profile = line.split(":", 1)
            st.session_state.participants_data[name.strip()] = profile.strip()

# --- 計算ロジック: 1ターン＝約5分と仮定 ---
MINUTES_PER_TURN = 5 

def get_current_progress():
    """現在の経過時間と進捗率を計算"""
    current_min = st.session_state.turn_count * MINUTES_PER_TURN
    progress_pct = min(current_min / target_duration * 100, 100)
    return current_min, progress_pct

# --- 関数定義 ---

def get_chat_response(system_prompt, user_prompt, model="gpt-3.5-turbo"):
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7
        )
        return response.choices[0].message.content
    except Exception as e:
        st.error(f"Error: {e}")
        return None

def generate_moderator_speak(history, topic, p_data):
    """モデレーターの発言生成（時間管理意識付き）"""
    p_list_str = "\n".join([f"- {name}: {prof}" for name, prof in p_data.items()])
    
    current_min, progress_pct = get_current_progress()
    
    # 進捗に応じた指示
    time_instruction = ""
    if progress_pct < 20:
        time_instruction = "現在は【序盤（アイスブレイク）】です。まだ核心には触れず、参加者の緊張をほぐし、ラポール（信頼関係）を築くための雑談やライトな質問をしてください。"
    elif progress_pct < 80:
        time_instruction = "現在は【中盤（深掘り）】です。参加者の回答から「なぜそう思うのか？」という背景や価値観、インサイトを深く掘り下げてください。"
    else:
        time_instruction = "現在は【終盤（まとめ）】です。これまでの議論を整理し、言い残したことがないか確認し、インタビューを締めくくる方向へ進めてください。"

    system_prompt = f"""
    あなたは熟練したFGIモデレーターです。
    
    ## テーマ
    {topic}
    
    ## 時間管理情報
    - 全体予定時間: {target_duration}分
    - 現在の経過時間（目安）: {current_min}分
    - {time_instruction}
    
    ## 進行ルール
    1. 参加者との距離感を大切にする。
    2. 全員に話を振る、または特定の興味深い発言を深掘りする。
    3. 一度の発言は長すぎないように。
    
    ## 参加者情報
    {p_list_str}
    """
    
    user_prompt = f"""
    これまでの会話履歴：
    {history}
    
    現在の状況（{current_min}分経過 / {target_duration}分予定）を踏まえて、モデレーターとして次の発言をしてください。
    """
    
    return get_chat_response(system_prompt, user_prompt, model="gpt-4o")

def generate_participant_speak(name, profile, history, topic):
    """参加者の発言生成"""
    system_prompt = f"""
    あなたは以下のプロファイルを持つ人物です。FGIに参加しています。
    名前: {name}
    詳細: {profile}
    テーマ: {topic}
    
    ルール:
    - プロファイル（年齢、家族、悩み）に基づき、リアルな口調で話す。
    - 建前だけでなく、徐々に本音を出す。
    - 短すぎる回答は避け、理由やエピソードを交える。
    """
    user_prompt = f"直前の会話履歴を踏まえ、あなた（{name}）として発言してください。\n履歴:\n{history}"
    return get_chat_response(system_prompt, user_prompt)

# --- メインエリア ---

# 進捗バーの表示
curr_min, prog_pct = get_current_progress()
st.progress(int(prog_pct))
st.caption(f"⏱️ 経過時間: 約 {curr_min} 分 / {target_duration} 分 （ターン数: {st.session_state.turn_count}）")

# 1. 履歴表示
chat_container = st.container()
with chat_container:
    for msg in st.session_state.messages:
        role = msg["role"]
        avatar = "🧑‍💼" if role == "Moderator" else "👤"
        with st.chat_message(role, avatar=avatar):
            st.markdown(f"**{role}**: {msg['content']}")

# 履歴テキスト作成
history_text = ""
for msg in st.session_state.messages[-15:]:
    history_text += f"{msg['role']}: {msg['content']}\n"

# 2. アクションボタン
st.divider()

col1, col2, col3 = st.columns(3)

def run_one_cycle():
    """モデレーター発言 -> 全員回答 の1セットを実行"""
    # モデレーター
    mod_text = generate_moderator_speak(history_text, topic, st.session_state.participants_data)
    if mod_text:
        st.session_state.messages.append({"role": "Moderator", "content": mod_text})
        
        # 参加者（モデレーターの発言を含めた履歴を渡す）
        current_history = history_text + f"Moderator: {mod_text}\n"
        for p_name, p_profile in st.session_state.participants_data.items():
            p_text = generate_participant_speak(p_name, p_profile, current_history, topic)
            if p_text:
                st.session_state.messages.append({"role": p_name, "content": p_text})
                current_history += f"{p_name}: {p_text}\n"
        
        # ターン数を加算
        st.session_state.turn_count += 1

with col1:
    if st.button("🎙️ 1ターン進める (手動)", use_container_width=True):
        with st.spinner("会話を生成中..."):
            run_one_cycle()
            st.rerun()

with col2:
    # 15分相当 = 3ターンと定義
    if st.button("⏩ 15分一気に進める (自動)", type="primary", use_container_width=True):
        with st.spinner("15分分の議論をシミュレーション中...（少し時間がかかります）"):
            for _ in range(3): # 3回ループ
                # 履歴更新のため再取得
                temp_hist = ""
                for msg in st.session_state.messages[-15:]:
                    temp_hist += f"{msg['role']}: {msg['content']}\n"
                
                # サイクル実行
                # ここで関数内のhistory_textは古いままなので、修正が必要だが
                # 簡易実装としてsession_state経由で回す
                
                # モデレーター
                mod_text = generate_moderator_speak(temp_hist, topic, st.session_state.participants_data)
                if mod_text:
                    st.session_state.messages.append({"role": "Moderator", "content": mod_text})
                    temp_hist += f"Moderator: {mod_text}\n"
                    
                    # 参加者
                    for p_name, p_profile in st.session_state.participants_data.items():
                        p_text = generate_participant_speak(p_name, p_profile, temp_hist, topic)
                        if p_text:
                            st.session_state.messages.append({"role": p_name, "content": p_text})
                            temp_hist += f"{p_name}: {p_text}\n"
                    
                    st.session_state.turn_count += 1
                    time.sleep(1) # API制限回避のためのwait
            st.rerun()

with col3:
    if st.button("🔍 現時点のインサイト分析", use_container_width=True):
        with st.spinner("分析中..."):
            all_log = "\n".join([f"{m['role']}: {m['content']}" for m in st.session_state.messages])
            insight_prompt = f"""
            テーマ「{topic}」についてのFGI議事録の分析をお願いします。
            
            ## 状況
            現在は開始から{curr_min}分経過した時点です。
            
            ## 分析項目
            1. 議論の主なトピック
            2. 見えてきたインサイト（未確定でも可）
            3. モデレーターへのアドバイス（次どこを深掘りすべきか）
            
            ## 議事録
            {all_log}
            """
            insight = get_chat_response(insight_prompt, "分析してください", model="gpt-4o")
            st.session_state.messages.append({"role": "System", "content": f"【AI分析】\n{insight}"})
            st.rerun()

# 3. ダウンロード
st.divider()
if st.session_state.messages:
    df = pd.DataFrame(st.session_state.messages)
    now = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    csv = df.to_csv(index=False).encode('utf-8_sig')
    st.download_button("📝 議事録ダウンロード", data=csv, file_name=f'fgi_log_{now}.csv', mime='text/csv')
