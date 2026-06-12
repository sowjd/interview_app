import sys
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.roles import get_interviewer_options, get_system_prompt


def initialize_messages() -> None:
    """면접 대화 기록이 없으면 초기 안내 메시지를 준비합니다."""
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {"role": "assistant", "content": "안녕하세요. 저는 AI 면접 코치입니다."}
        ]


def handle_user_input(user_text: str) -> None:
    """사용자 입력을 받아 메시지 목록에 저장합니다."""
    user_message = {"role": "user", "content": user_text}
    st.session_state.messages.append(user_message)

    # assistant_reply = "면접 답변을 확인했습니다. (임시 응답)"
    # assistant_message = {"role": "assistant", "content": assistant_reply}
    # st.session_state.messages.append(assistant_message)


def generate_coach_reply(user_text: str, role_key: str) -> None:
    """선택한 면접관 유형에 맞는 임시 코치 응답을 만듭니다."""
    system_prompt = get_system_prompt(role_key)
    assistant_reply = f"(임시 응답) 다음 관점으로 피드백합니다: {system_prompt:30}"
    assistant_message = {"role": "assistant", "content": assistant_reply}
    st.session_state.messages.append(assistant_message)


def main():
    st.set_page_config(
        page_title="AI 면접 코치",
        page_icon="🎤",
    )

    st.title("AI 면접 코치")
    st.caption("AI와 함께 면접 연습을 해봐요~!")

    with st.sidebar:
        st.header("면접관 설정")

        if "selected_role" not in st.session_state:
            st.session_state.selected_role = "tech"

        interviewer_options = get_interviewer_options()
        interviewer_keys = list(interviewer_options.keys())
        selected_index = (
            interviewer_keys.index(st.session_state.selected_role)
            if st.session_state.selected_role in interviewer_keys
            else 0
        )
        st.session_state.selected_role = st.selectbox(
            "면접관 유형",
            interviewer_keys,
            index=selected_index,
            format_func=lambda key: interviewer_options[key],
        )

    initialize_messages()

    # 채팅 입력 위젯 — 화면 하단에 고정됩니다.
    user_input = st.chat_input("면접 답변을 입력해 주세요.")
    if user_input:
        handle_user_input(user_input)
        generate_coach_reply(user_input, st.session_state.selected_role)
        st.rerun()

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])


if __name__ == "__main__":
    main()
