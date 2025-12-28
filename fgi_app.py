import streamlit as st
from openai import OpenAI
import pandas as pd
import datetime
import time

# --- ページ設定 ---
st.set_page_config(page_title="AI FGI Simulator", layout="wide")

st.title("👥 AI Focus Group Interview Simulator")

# --- セッション状態の初期化 ---
if "app_phase" not in st.session_state:
    st.session_state.app_phase = "strategy" 

# 参加者データ
if "participants_data" not in st.session_state:
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

if "analysis_result" not in st.session_state:
    st.session_state.analysis_result = ""

# --- サイドバー設定 ---
with st.sidebar:
    st.header("🔧 設定")
    
    if "OPENAI_API_KEY" in st.secrets:
        api_key = st.secrets["OPENAI_API_KEY"]
    else:
        api_key = st.text_input("OpenAI API Key", type="password")

    if not api_key:
        st.warning("APIキーが設定されていません。")
        st.stop()
    
    client = OpenAI(api_key=api_key)

    topic = st.text_input("インタビューのテーマ", value="新しいコーヒーブランドのコンセプト受容性")
    target_duration = st.slider("想定インタビュー時間（分）", 30, 120, 60, step=10)
    
    st.write("---")
    st.subheader("🤖 モデレーター設定")
    moderator_style = st.slider("深掘り度", 1, 5, 3, help="1:優しく ~ 5:厳しく")
    
    # --- 参加者管理 ---
    st.write("---")
    st.subheader("👥 参加者の管理")
    
    with st.expander("➕ 参加者を追加する", expanded=False):
        new_name = st.text_input("名前", placeholder="例: 鈴木さん")
        new_profile = st.text_area("属性・ナラティブ", placeholder="詳細な属性...", height=100)
        if st.button("リストに追加"):
            if new_name and new_profile:
                st.session_state.participants_data[new_name] = new_profile
                st.success(f"{new_name} を追加しました")
                time.sleep(0.5)
                st.rerun()

    st.write(f"**現在の参加者 ({len(st.session_state.participants_data)}人)**")
    for name in list(st.session_state.participants_data.keys()):
        c1, c2 = st.columns([3, 1])
        c1.text(f"- {name}")
        if c2.button("削除", key=f"del_{name}"):
            del st.session_state.participants_data[name]
            st.rerun()
    
    st.divider()
    if st.button("🔄 システム全体をリセット"):
        for key in list(st.session_state.keys()):
            if key != "participants_data":
                del st.session_state[key]
        st.session_state.app_phase = "strategy"
        st.session_state.strategy_messages = []
        st.session_state.interview_messages = []
        st.session_state.analysis_result = ""
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
    
    if not st.session_state.strategy_messages:
        st.session_state.strategy_messages.append({
            "role": "assistant", 
            "content": f"モデレーターです。テーマ「{topic}」についてFGIを行います。参加者は{len(st.session_state.participants_data)}名です。指示があればどうぞ。"
        })

    st.subheader("📝 Phase 1: モデレーターとの作戦会議")
    
    for msg in st.session_state.strategy_messages:
        with st.chat_message(msg["role"], avatar="🤖" if msg["role"] == "assistant" else "🧑‍💻"):
            st.write(msg["content"])

    if user_input := st.chat_input("指示を入力"):
        st.session_state.strategy_messages.append({"role": "user", "content": user_input})
        system_prompt = f"あなたはFGIモデレーター。テーマ:{topic}。深掘り度:{moderator_style}。指示に対して頼もしく回答せよ。"
        api_msgs = [{"role": m["role"], "content": m["content"]} for m in st.session_state.strategy_messages]
        response = get_chat_response(system_prompt, api_msgs)
        st.session_state.strategy_messages.append({"role": "assistant", "content": response})
        st.rerun()

    st.divider()
    if st.button("🚀 作戦完了！ FGI本番を開始する", type="primary"):
        if not st.session_state.participants_data:
            st.error("参加者がいません")
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
    st.caption(f"⏱️ {current_min}分 / {target_duration}分 (深掘り度: {moderator_style})")

    chat_container = st.container()
    with chat_container:
        if not st.session_state.interview_messages:
            st.info("モデレーターに最初の発言をさせてください。")
        for msg in st.session_state.interview_messages:
            role = msg["role"]
            avatar = "🧑‍💼" if role == "Moderator" else "👤"
            with st.chat_message(role, avatar=avatar):
                st.markdown(f"**{role}**: {msg['content']}")

    # データ準備
    strategy_context = "\n".join([f"{m['role']}: {m['content']}" for m in st.session_state.strategy_messages])
    history_text = ""
    for msg in st.session_state.interview_messages[-15:]:
        history_text += f"{msg['role']}: {msg['content']}\n"

    # --- モデレーター: 通常発言生成 ---
    def generate_moderator_speak_v3(history):
        p_list_str = "\n".join([f"- {name}: {prof}" for name, prof in st.session_state.participants_data.items()])
        time_inst = "序盤" if progress_pct < 20 else "中盤" if progress_pct < 80 else "終盤"
        style_inst = "共感重視" if moderator_style <= 2 else "追求重視" if moderator_style >= 4 else "バランス重視"
        
        system_prompt = f"""
        あなたはFGIモデレーター。
        テーマ: {topic}
        状況: {current_min}分経過 ({time_inst})
        事前指示: {strategy_context}
        スタイル: {style_inst} (Lv.{moderator_style})
        参加者: {p_list_str}
        会話の流れに沿って発言せよ。
        """
        user_prompt = f"履歴:\n{history}\n\nモデレーターとして発言してください。"
        return get_chat_response(system_prompt, [{"role": "user", "content": user_prompt}], model="gpt-4o")

    # --- モデレーター: 刺激物提示生成 (New!) ---
    def generate_moderator_presentation(stimulus_type, stimulus_content, history):
        p_list_str = "\n".join([f"- {name}: {prof}" for name, prof in st.session_state.participants_data.items()])
        style_inst = "共感重視" if moderator_style <= 2 else "追求重視" if moderator_style >= 4 else "バランス重視"
        
        system_prompt = f"""
        あなたはFGIモデレーターです。
        
        【重要ミッション】
        クライアント（リサーチャー）から渡された「{stimulus_type}」を参加者に提示・説明し、感想を求めてください。
        
        提示する内容:
        {stimulus_content}
        
        スタイル: {style_inst} (Lv.{moderator_style})
        
        注意点:
        - 突然提示するのではなく、会話の流れを少し意識しつつ「さて、ここで〜を見ていただきたいと思います」と切り出してください。
        - 提示内容をわかりやすく口頭で説明してください。
        - 最後に「率直にどう思いましたか？」など、スタイルに合わせて問いかけてください。
        """
        user_prompt = f"履歴:\n{history}\n\nモデレーターとして上記資料を提示する発言をしてください。"
        return get_chat_response(system_prompt, [{"role": "user", "content": user_prompt}], model="gpt-4o")

    # --- 参加者生成 ---
    def generate_participant_speak_v3(name, profile, history):
        system_prompt = f"あなたはFGI参加者。名前:{name}, 属性:{profile}, テーマ:{topic}。履歴を踏まえ発言せよ。"
        user_prompt = f"履歴:\n{history}\n\n{name}として発言してください。"
        return get_chat_response(system_prompt, [{"role": "user", "content": user_prompt}])

    # --- UI: 刺激物の投入エリア (New!) ---
    st.markdown("---")
    with st.expander("📺 コンセプト・資料を提示する（刺激物の投入）", expanded=False):
        st.info("議論の途中で、コンセプトボードや動画などの「刺激物」を参加者に見せることができます。")
        stimulus_type = st.selectbox("資料の種類", ["コンセプトボード", "動画コンテ", "製品画像", "キャッチコピー", "価格表"])
        stimulus_content = st.text_area("資料の内容（できるだけ正確に文字で描写してください）", height=100, 
                                        placeholder="例：『朝専用の無糖コーヒー。カフェイン2倍でシャキッとする。黒いスリムな缶ボトル。価格は150円』というコンセプトボード")
        
        if st.button("📢 この資料を提示して議論してもらう"):
            if not stimulus_content:
                st.error("内容を入力してください。")
            else:
                with st.spinner("モデレーターが資料を提示中..."):
                    # モデレーターが資料提示発言をする
                    mod_text = generate_moderator_presentation(stimulus_type, stimulus_content, history_text)
                    if mod_text:
                        st.session_state.interview_messages.append({"role": "Moderator", "content": f"【資料提示: {stimulus_type}】\n{mod_text}"})
                        st.session_state.turn_count += 1
                        st.rerun()

    # --- UI: 操作ボタン ---
    st.markdown("---")
    c1, c2, c3 = st.columns(3)
    with c1:
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
    with c2:
        if st.button("⏩ 15分一気に進める", use_container_width=True):
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
    
    # 終了ボタン
    st.markdown("---")
    st.markdown("### 🏁 セッション終了と分析")
    if st.button("議論を終了し、インサイトを分析する", type="primary", use_container_width=True):
        st.session_state.app_phase = "report"
        st.rerun()

# --- Phase 3: インサイト分析レポート ---

elif st.session_state.app_phase == "report":
    st.subheader("📊 Phase 3: インサイト分析レポート")
    
    if not st.session_state.analysis_result:
        with st.spinner("AIリサーチャーが分析中...（提示された資料への反応も含めて分析します）"):
            full_log = "\n".join([f"{m['role']}: {m['content']}" for m in st.session_state.interview_messages])
            profiles_str = "\n".join([f"- {name}: {prof}" for name, prof in st.session_state.participants_data.items()])

            analysis_system_prompt = f"""
            あなたはFGI分析のプロです。議事録と参加者プロファイルを読み込み、インサイトを導出してください。
            
            ## テーマ
            {topic}
            
            ## 参加者
            {profiles_str}
            
            ## 分析のポイント
            - 議論の途中で「コンセプト」や「資料」が提示されている場合、それに対する**受容性（好き/嫌い）とその理由**を重点的に分析してください。
            - 表面的な賛同だけでなく、プロファイルに基づく本音や懸念点（インサイト）を発掘してください。
            
            ## 出力構成（マークダウン）
            1. エグゼクティブ・サマリー
            2. 提示された刺激物（コンセプト）への反応評価
            3. 参加者別の深層分析
            4. 主要インサイト・仮説
            5. マーケティング提言
            """

            analysis_user_prompt = f"以下の議事録を分析してください:\n\n{full_log}"
            result = get_chat_response(analysis_system_prompt, [{"role": "user", "content": analysis_user_prompt}], model="gpt-4o")
            st.session_state.analysis_result = result
            st.rerun()

    st.markdown(st.session_state.analysis_result)
    st.divider()
    
    # ダウンロード
    now = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    st.download_button(label="📥 分析レポート (Text)", data=st.session_state.analysis_result, file_name=f'insight_report_{now}.md', mime='text/markdown')
    
    df = pd.DataFrame(st.session_state.interview_messages)
    csv = df.to_csv(index=False).encode('utf-8_sig')
    st.download_button(label="📥 議事録データ (CSV)", data=csv, file_name=f'fgi_log_{now}.csv', mime='text/csv')
    
    st.divider()
    if st.button("🔄 最初からやり直す（リセット）"):
        st.session_state.app_phase = "strategy"
        st.session_state.strategy_messages = []
        st.session_state.interview_messages = []
        st.session_state.analysis_result = ""
        st.session_state.turn_count = 0
        st.rerun()
