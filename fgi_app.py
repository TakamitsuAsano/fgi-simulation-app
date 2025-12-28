import streamlit as st
from openai import OpenAI
import pandas as pd
import datetime
import time

# --- ページ設定 ---
st.set_page_config(page_title="AI FGI Simulator", layout="wide")

st.title("👥 AI Focus Group Interview Simulator")

# --- セッション状態の初期化（最初に行う） ---
if "app_phase" not in st.session_state:
    st.session_state.app_phase = "strategy" 

if "participants_data" not in st.session_state:
    # デフォルトの参加者をセット（初回のみ）
    st.session_state.participants_data = {
        "田中さん": "40歳、既婚、子供1人（7歳女子）。年収800万。忙しいが週末は家族時間を大切にする。",
        "佐藤さん": "28歳、独身男性。IT企業、年収500万。キャンプとサウナが好き。効率重視。"
    }

if "strategy_messages" not in st.session_state:
    st.session_state.strategy_messages = []

if "interview_messages" not in st.session_state:
    st.session_state.interview_messages = []

if "turn_count" not in st.session_state:
    st.session_state.turn_count = 0

# --- サイドバー設定 ---
with st.sidebar:
    st.header("🔧 設定")
    
    # APIキー
    if "OPENAI_API_KEY" in st.secrets:
        api_key = st.secrets["OPENAI_API_KEY"]
    else:
        api_key = st.text_input("OpenAI API Key", type="password")

    if not api_key:
        st.warning("APIキーが設定されていません。")
        st.stop()
    
    client = OpenAI(api_key=api_key)

    # テーマ・時間
    topic = st.text_input("インタビューのテーマ", value="新しいコーヒーブランドのコンセプト受容性")
    target_duration = st.slider("想定インタビュー時間（分）", 30, 120, 60, step=10)
    
    # モデレーター設定
    st.write("---")
    st.subheader("🤖 モデレーター設定")
    moderator_style = st.slider("深掘り度", 1, 5, 3, help="1:優しく ~ 5:厳しく")
    
    # --- 参加者設定（改修部分） ---
    st.write("---")
    st.subheader("👥 参加者の管理")
    
    # 登録フォーム
    with st.expander("➕ 参加者を追加する", expanded=True):
        new_name = st.text_input("名前", placeholder="例: 鈴木さん")
        new_profile = st.text_area("属性・ナラティブ", placeholder="例: 55歳、専業主婦。健康が悩み...", height=100)
        
        if st.button("リストに追加"):
            if new_name and new_profile:
                st.session_state.participants_data[new_name] = new_profile
                st.success(f"{new_name} を追加しました")
                time.sleep(0.5)
                st.rerun()
            else:
                st.error("名前と属性を入力してください")

    # 現在のリスト表示
    st.write(f"**現在の参加者 ({len(st.session_state.participants_data)}人)**")
    
    # 削除用ボタンの生成
    # 辞書を直接ループ中に変更できないため、リスト化して処理
    for name in list(st.session_state.participants_data.keys()):
        col_list1, col_list2 = st.columns([3, 1])
        with col_list1:
            st.text(f"- {name}")
        with col_list2:
            if st.button("削除", key=f"del_{name}"):
                del st.session_state.participants_data[name]
                st.rerun()
    
    if st.button("🗑️ 参加者を全員削除"):
        st.session_state.participants_data = {}
        st.rerun()

    st.divider()
    
    # 全リセット
    if st.button("🔄 システム全体をリセット"):
        # APIキー以外のセッションをクリア
        keys = list(st.session_state.keys())
        for key in keys:
            if key != "participants_data": # 参加者設定は残す場合（完全に消すならここも消す）
                del st.session_state[key]
        # 参加者データも初期化したい場合は下記行を有効化
        # del st.session_state["participants_data"]
        
        # フェーズ初期化
        st.session_state.app_phase = "strategy"
        st.session_state.strategy_messages = []
        st.session_state.interview_messages = []
        st.session_state.turn_count = 0
        st.rerun()

# --- 関数定義 ---

def get_chat_response(system_prompt, messages, model="gpt-4o"):
    try:
        api_messages = [{"role": "system", "content": system_prompt}] + messages
        response = client.chat.completions.create(
            model=model,
            messages=api_messages,
            temperature=0.7
        )
        return response.choices[0].message.content
    except Exception as e:
        st.error(f"Error: {e}")
        return None

# --- Phase 1: 作戦会議 ---

if st.session_state.app_phase == "strategy":
    
    # 初回メッセージのセット
    if not st.session_state.strategy_messages:
        st.session_state.strategy_messages.append({
            "role": "assistant", 
            "content": f"モデレーターです。テーマ「{topic}」についてFGIを行います。\n参加者は現在{len(st.session_state.participants_data)}名です。事前指示があればどうぞ。"
        })

    st.subheader("📝 Phase 1: モデレーターとの作戦会議")
    st.info(f"現在登録されている参加者: {', '.join(st.session_state.participants_data.keys())}")

    for msg in st.session_state.strategy_messages:
        with st.chat_message(msg["role"], avatar="🤖" if msg["role"] == "assistant" else "🧑‍💻"):
            st.write(msg["content"])

    if user_input := st.chat_input("指示を入力（例：鈴木さんを中心に、健康意識について聞いて）"):
        st.session_state.strategy_messages.append({"role": "user", "content": user_input})
        
        system_prompt = f"""
        あなたはFGIのプロモデレーターです。
        テーマ: {topic}
        深掘り度: {moderator_style}
        参加者一覧: {', '.join(st.session_state.participants_data.keys())}
        
        ユーザーの指示を受け、「了解しました」と頼もしく回答してください。
        """
        
        api_msgs = [{"role": m["role"], "content": m["content"]} for m in st.session_state.strategy_messages]
        response = get_chat_response(system_prompt, api_msgs)
        st.session_state.strategy_messages.append({"role": "assistant", "content": response})
        st.rerun()

    st.divider()
    if st.button("🚀 作戦完了！ FGI本番を開始する", type="primary"):
        if not st.session_state.participants_data:
            st.error("参加者が一人もいません。サイドバーから追加してください。")
        else:
            st.session_state.app_phase = "interview"
            st.rerun()

# --- Phase 2: FGI本番 ---

elif st.session_state.app_phase == "interview":
    st.subheader("🎙️ Phase 2: FGI シミュレーション本番")
    
    MINUTES_PER_TURN = 5
    current_min = st.session_state.turn_count * MINUTES_PER_TURN
    progress_pct = min(current_min / target_duration * 100, 100)
    
    st.progress(int(progress_pct))
    st.caption(f"⏱️ 経過: {current_min}分 / {target_duration}分 (深掘り度: {moderator_style})")

    chat_container = st.container()
    with chat_container:
        if not st.session_state.interview_messages:
            st.info("モデレーターに最初の発言をさせてください。")
        
        for msg in st.session_state.interview_messages:
            role = msg["role"]
            avatar = "🧑‍💼" if role == "Moderator" else "👤"
            with st.chat_message(role, avatar=avatar):
                st.markdown(f"**{role}**: {msg['content']}")

    strategy_context = "\n".join([f"{m['role']}: {m['content']}" for m in st.session_state.strategy_messages])
    history_text = ""
    for msg in st.session_state.interview_messages[-15:]:
        history_text += f"{msg['role']}: {msg['content']}\n"

    # --- モデレーター生成 ---
    def generate_moderator_speak_v3(history):
        p_list_str = "\n".join([f"- {name}: {prof}" for name, prof in st.session_state.participants_data.items()])
        
        time_instruction = ""
        if progress_pct < 20: time_instruction = "現在は【序盤】。話しやすい雰囲気作り。"
        elif progress_pct < 80: time_instruction = "現在は【中盤】。核心に迫る。"
        else: time_instruction = "現在は【終盤】。まとめ。"

        style_instruction = ""
        if moderator_style <= 2: style_instruction = "【態度: 受容的】共感重視。"
        elif moderator_style >= 4: style_instruction = "【態度: 分析的】論理的背景を追求。"
        else: style_instruction = "【態度: バランス型】"

        system_prompt = f"""
        あなたはFGIモデレーターです。
        テーマ: {topic}
        時間: {current_min}分/{target_duration}分 ({time_instruction})
        指示: {strategy_context}
        スタイル: {style_instruction} (Level {moderator_style})
        参加者: {p_list_str}
        
        会話の流れに沿って次の発言を行ってください。
        """
        user_prompt = f"履歴:\n{history}\n\nモデレーターとして発言してください。"
        return get_chat_response(system_prompt, [{"role": "user", "content": user_prompt}], model="gpt-4o")

    # --- 参加者生成 ---
    def generate_participant_speak_v3(name, profile, history):
        system_prompt = f"""
        あなたはFGI参加者です。
        名前: {name}
        属性: {profile}
        テーマ: {topic}
        """
        user_prompt = f"履歴を踏まえ、あなた（{name}）として発言してください。\n履歴:\n{history}"
        return get_chat_response(system_prompt, [{"role": "user", "content": user_prompt}])

    # --- ボタンエリア ---
    st.divider()
    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("🎙️ 1ターン進める", use_container_width=True):
            with st.spinner("モデレーター思考中..."):
                mod_text = generate_moderator_speak_v3(history_text)
                if mod_text:
                    st.session_state.interview_messages.append({"role": "Moderator", "content": mod_text})
                    current_hist = history_text + f"Moderator: {mod_text}\n"
                    
                    with st.spinner("参加者回答中..."):
                        for p_name, p_profile in st.session_state.participants_data.items():
                            p_text = generate_participant_speak_v3(p_name, p_profile, current_hist)
                            if p_text:
                                st.session_state.interview_messages.append({"role": p_name, "content": p_text})
                                current_hist += f"{p_name}: {p_text}\n"
                    
                    st.session_state.turn_count += 1
                    st.rerun()

    with col2:
        if st.button("⏩ 15分一気に進める", type="primary", use_container_width=True):
            with st.spinner("議論進行中..."):
                for _ in range(3):
                    temp_hist = ""
                    for msg in st.session_state.interview_messages[-15:]:
                        temp_hist += f"{msg['role']}: {msg['content']}\n"
                    
                    mod_text = generate_moderator_speak_v3(temp_hist)
                    if mod_text:
                        st.session_state.interview_messages.append({"role": "Moderator", "content": mod_text})
                        temp_hist += f"Moderator: {mod_text}\n"
                        for p_name, p_profile in st.session_state.participants_data.items():
                            p_text = generate_participant_speak_v3(p_name, p_profile, temp_hist)
                            if p_text:
                                st.session_state.interview_messages.append({"role": p_name, "content": p_text})
                                temp_hist += f"{p_name}: {p_text}\n"
                        st.session_state.turn_count += 1
                        time.sleep(1)
                st.rerun()

    with col3:
        if st.button("📋 作戦メモを確認", use_container_width=True):
            with st.expander("事前打ち合わせ", expanded=True):
                for m in st.session_state.strategy_messages:
                    st.caption(f"{m['role']}: {m['content']}")

    st.divider()
    if st.session_state.interview_messages:
        df = pd.DataFrame(st.session_state.interview_messages)
        now = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        csv = df.to_csv(index=False).encode('utf-8_sig')
        st.download_button("📝 議事録ダウンロード", data=csv, file_name=f'fgi_log_{now}.csv', mime='text/csv')
