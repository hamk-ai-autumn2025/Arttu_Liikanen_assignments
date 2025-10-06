import streamlit as st
import requests
import os

LLM_ENDPOINTS = {
    "OpenAI GPT-3.5": "https://api.openai.com/v1/chat/completions",
    "Anthropic Claude": "https://api.anthropic.com/v1/messages",
    "Cohere Command": "https://api.cohere.ai/v1/chat"
}

API_KEYS = {
    "OpenAI GPT-3.5": os.getenv("OPENAI_API_KEY", ""),
    "Anthropic Claude": os.getenv("ANTHROPIC_API_KEY", ""),
    "Cohere Command": os.getenv("COHERE_API_KEY", "")
}

def query_openai(messages, api_key):
    headers = {"Authorization": f"Bearer {api_key}"}
    data = {
        "model": "gpt-3.5-turbo",
        "messages": messages,
        "max_tokens": 512
    }
    response = requests.post(LLM_ENDPOINTS["OpenAI GPT-3.5"], headers=headers, json=data)
    return response.json()["choices"][0]["message"]["content"]

def query_anthropic(messages, api_key):
    headers = {"x-api-key": api_key}
    prompt = "\n".join([f"{m['role']}: {m['content']}" for m in messages])
    data = {
        "model": "claude-2.1",
        "max_tokens_to_sample": 512,
        "prompt": prompt
    }
    response = requests.post(LLM_ENDPOINTS["Anthropic Claude"], headers=headers, json=data)
    return response.json()["completion"]

def query_cohere(messages, api_key):
    headers = {"Authorization": f"Bearer {api_key}"}
    chat_history = [{"role": m["role"], "message": m["content"]} for m in messages]
    data = {
        "chat_history": chat_history,
        "model": "command",
        "message": messages[-1]["content"],
        "max_tokens": 512
    }
    response = requests.post(LLM_ENDPOINTS["Cohere Command"], headers=headers, json=data)
    return response.json().get("text", "No response from Cohere.")

st.set_page_config(page_title="Multi-LLM Chat", layout="wide")
st.title("Multi-LLM Chat Interface")

llm_choice = st.sidebar.selectbox("Choose LLM", list(LLM_ENDPOINTS.keys()))

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "message_sent" not in st.session_state:
    st.session_state.message_sent = False

def send_message():
    st.session_state.message_sent = True

user_input = st.text_input("Your message:", key="user_input", on_change=send_message)

send_button = st.button("Send")

if (st.session_state.message_sent or send_button) and user_input:
    st.session_state.chat_history.append({"role": "user", "content": user_input})

    if llm_choice == "OpenAI GPT-3.5":
        reply = query_openai(st.session_state.chat_history, API_KEYS[llm_choice])
    elif llm_choice == "Anthropic Claude":
        reply = query_anthropic(st.session_state.chat_history, API_KEYS[llm_choice])
    elif llm_choice == "Cohere Command":
        reply = query_cohere(st.session_state.chat_history, API_KEYS[llm_choice])
    else:
        reply = "Model not supported."

    st.session_state.chat_history.append({"role": "assistant", "content": reply})
    st.session_state.message_sent = False  # Reset flag

for msg in st.session_state.chat_history:
    if msg["role"] == "user":
        st.markdown(f"**You:** {msg['content']}")
    else:
        st.markdown(f"**{llm_choice}:** {msg['content']}")
        
