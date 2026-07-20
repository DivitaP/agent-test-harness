"""Live demo UI: chat with the agent and watch tool calls stream in real time."""

import os
import sys
import uuid
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1].parent))

from support_desk.graph import build_app


st.set_page_config(page_title="Support Desk Agent", layout="wide")
st.title("Support Desk Agent")

mode = st.sidebar.selectbox(
    "Failure mode", ["none", "skip_policy", "vague_answers", "flaky_lookup"]
)
if st.sidebar.button("Rebuild agent"):
    st.session_state.clear()

if "app" not in st.session_state or st.session_state.get("mode") != mode:
    os.environ["DEMO_FAILURE_MODE"] = mode
    st.session_state.app = build_app()
    st.session_state.mode = mode
    st.session_state.thread = uuid.uuid4().hex
    st.session_state.history = []

for role, text in st.session_state.history:
    st.chat_message(role).write(text)

if prompt := st.chat_input("e.g. I want a refund for order #4412, it arrived damaged"):
    st.chat_message("user").write(prompt)
    st.session_state.history.append(("user", prompt))

    final = ""
    with st.chat_message("assistant"):
        with st.status("Agent working...", expanded=True) as status:
            config = {"configurable": {"thread_id": st.session_state.thread}}
            for update in st.session_state.app.stream(
                {"messages": [("user", prompt)]}, config, stream_mode="updates"
            ):
                if "agent" in update:
                    message = update["agent"]["messages"][-1]
                    for tool_call in getattr(message, "tool_calls", None) or []:
                        st.write(f"🔧 calling `{tool_call['name']}` with `{tool_call['args']}`")
                    if message.content and not getattr(message, "tool_calls", None):
                        final = message.content
                if "tools" in update:
                    for tool_message in update["tools"]["messages"]:
                        st.write(f"📄 `{tool_message.name}` returned:")
                        st.code(str(tool_message.content)[:400], language="json")
            status.update(label="Done", state="complete", expanded=True)
        st.write(final)
    st.session_state.history.append(("assistant", final))
