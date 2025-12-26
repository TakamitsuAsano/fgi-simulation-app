import streamlit as st
from openai import OpenAI
import pandas as pd
import datetime

# --- ページ設定 ---
st.set_page_config(page_title="AI FGI Simulator", layout="wide")

st.title("👥 AI Focus Group Interview Simulator")
st.markdown("""
設定したペルソナ（参加者）とAIモデレーターによるグループインタビューをシミュレーションします。
日常会話から徐々に深層心理やインサイトを探るように設計されています。
""")

# --- サイドバー設定 ---
with st.sidebar:
    st.header("🔧 設定")
    
    # APIキー入力
    api_key = st.text_input("OpenAI API Key", type="password")
    if not api_key:
        st.warning("APIキーを入力してください。")
        st.stop()
    
    client = OpenAI(api_key=api_key)

    # テーマ設定
    topic = st.text_input("インタビューのテーマ", value="新しいコーヒーブランドのコンセプト受容性")
    
    # モデレーターの設定
    moderator_style = st.slider("モデレーターの深掘り度（低い＝雑談重視、高い＝分析重視）", 1, 5, 2)
    
    # 参加者設定（デフォルト値）
    default_participants = """
田中さん: 40歳、既婚、子供1人（7歳小学一年生女子）。キャリアウーマンで年収800万。忙しいが週末は家族との時間を大切にしたい。少し疲れ気味。
佐藤さん: 28歳、独身、男性。IT企業勤務、年収500万。趣味はキャンプとサウナ。効率重視だが、アナログな体験も好き。
鈴木さん: 55歳、既婚、子供独立済み。専業主婦。夫と二人暮らし。健康と老後の資金が悩み。時間はたっぷりある。
"""
    participants_input = st.text_area("参加者プロファイル（名前: 属性 の形式で改行）", value=default_participants.strip(), height=200)

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
if "participants_data" not in st.session_state:
    # 初回ロード時の処理
    st.session_state.participants_data = {}
    lines = participants_input.strip().split('\n')
    for line in lines:
        if ":" in line:
            name, profile = line.split(":", 1)
            st.session_state.participants_data[name.strip()] = profile.strip()

# --- 関数定義 ---

def get_chat_response(system_prompt, user_prompt, model="gpt-3.5-turbo"):
    """OpenAI APIを呼び出してレスポンスを取得"""
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
    """モデレーターの発言を生成"""
    # 参加者リストの文字列化
    p_list_str = "\n".join([f"- {name}: {prof}" for name, prof in p_data.items()])
    
    system_prompt = f"""
    あなたは熟練したFGI（Focus Group Interview）のモデレーターです。
    
    ## 目的
    テーマ「{topic}」について、参加者から本音や無意識のインサイトを引き出してください。
    
    ## 進行のルール
    1. いきなり核心（インサイト）に触れようとせず、まずは日常会話やアイスブレイクから始めてください。
    2. 参加者との「距離感」を大切にし、共感を示しながら信頼関係（ラポール）を築いてください。
    3. 参加者全員にまんべんなく話を振ったり、特定の回答を深掘りしたりしてください。
    4. 今の段階は「深掘り度レベル: {moderator_style}/5」です（低いほど雑談重視、高いほど核心に迫る）。
    5. 一度の発言は長すぎないようにし、必ず質問や問いかけで終わってください。
    
    ## 参加者情報
    {p_list_str}
    """
    
    user_prompt = f"""
    これまでの会話履歴：
    {history}
    
    今の会話の流れを踏まえて、モデレーターとして次の発言をしてください。
    """
    
    return get_chat_response(system_prompt, user_prompt, model="gpt-4o") # モデレーターは賢いモデル推奨

def generate_participant_speak(name, profile, history, topic):
    """参加者の発言を生成"""
    system_prompt = f"""
    あなたは以下のプロファイルを持つ人物になりきってください。
    
    名前: {name}
    属性・背景: {profile}
    
    あなたは現在、テーマ「{topic}」についてのグループインタビューに参加しています。
    
    ## 行動指針
    1. あなたの属性、年齢、家族構成、悩み、喜びに沿った自然な口調で話してください。
    2. モデレーターの問いかけに対して答えてください。
    3. 必要であれば、他の参加者の意見に同意したり、驚いたりしてください。
    4. AIであることを忘れ、完全にその人間として振る舞ってください。
    """
    
    user_prompt = f"""
    これまでの会話履歴：
    {history}
    
    直前のモデレーターや他の参加者の発言を受けて、あなた（{name}）として発言してください。
    """
    
    return get_chat_response(system_prompt, user_prompt)

# --- メインエリアの表示 ---

# 1. 履歴の表示
chat_container = st.container()
with chat_container:
    for msg in st.session_state.messages:
        role_style = "background-color: #f0f2f6;" if msg["role"] == "Moderator" else ""
        with st.chat_message(msg["role"], avatar="🧑‍💼" if msg["role"] == "Moderator" else "👤"):
            st.markdown(f"**{msg['role']}**: {msg['content']}")

# 2. 会話進行コントロール
st.divider()
col1, col2 = st.columns(2)

# 会話履歴をテキスト化（プロンプト用）
history_text = ""
for msg in st.session_state.messages[-10:]: # 直近10件のみ参照（トークン節約）
    history_text += f"{msg['role']}: {msg['content']}\n"

with col1:
    if st.button("🎙️ モデレーターが発言する", type="primary", use_container_width=True):
        with st.spinner("モデレーターが考え中..."):
            mod_text = generate_moderator_speak(history_text, topic, st.session_state.participants_data)
            if mod_text:
                st.session_state.messages.append({"role": "Moderator", "content": mod_text})
                st.rerun()

with col2:
    if st.button("🗣️ 参加者全員が回答する", use_container_width=True):
        if not st.session_state.messages or st.session_state.messages[-1]["role"] != "Moderator":
            st.warning("先にモデレーターに発言させてください。")
        else:
            with st.spinner("参加者が回答を作成中..."):
                # モデレーターの直前の発言を取得
                latest_history = history_text
                
                # 各参加者が順番に（あるいは並列に）発言を生成
                for p_name, p_profile in st.session_state.participants_data.items():
                    p_text = generate_participant_speak(p_name, p_profile, latest_history, topic)
                    if p_text:
                        st.session_state.messages.append({"role": p_name, "content": p_text})
                        # 会話履歴を更新して、次の人が前の人の発言も踏まえられるようにする（オプション）
                        latest_history += f"{p_name}: {p_text}\n"
                st.rerun()

# 3. 議事録ダウンロード
st.divider()
st.subheader("📝 議事録エクスポート")

if st.session_state.messages:
    df = pd.DataFrame(st.session_state.messages)
    # 現在時刻をファイル名に
    now = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    csv = df.to_csv(index=False).encode('utf-8_sig')
    
    st.download_button(
        label="議事録をCSVでダウンロード",
        data=csv,
        file_name=f'fgi_log_{now}.csv',
        mime='text/csv',
    )

    # インサイト分析ボタン
    if st.button("🔍 この時点までのインサイトを分析する"):
        with st.spinner("会話ログを分析中..."):
            all_log = "\n".join([f"{m['role']}: {m['content']}" for m in st.session_state.messages])
            
            insight_prompt = f"""
            あなたは優秀なマーケティングリサーチャーです。以下のFGIの議事録を読み解き、分析してください。
            
            テーマ: {topic}
            
            ## 分析してほしい項目
            1. 参加者の共通する「痛み（Pain）」や「課題」
            2. 参加者が感じている「喜び（Gain）」や「価値」
            3. 発言の背景にある心理的要因・インサイト
            4. 今後のマーケティングへの示唆
            
            ## 議事録
            {all_log}
            """
            
            insight = get_chat_response(insight_prompt, "分析をお願いします", model="gpt-4o")
            st.markdown("### 💡 AIによるインサイト分析結果")
            st.write(insight)