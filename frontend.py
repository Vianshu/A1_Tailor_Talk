import streamlit as st
import requests
import datetime # Import datetime for current time/date
from dotenv import load_dotenv
import os
# --- Configuration and Constants ---
st.set_page_config(
    page_title="Zenith Chat AI", # Catchier, more sophisticated name
    page_icon="✨", # Still a nice icon
    layout="centered",
    initial_sidebar_state="collapsed" # Start with sidebar collapsed for cleaner look
)

load_dotenv("keys.env")

# API endpoint (still using mock for now)
API_URL = os.getenv("API_URL")  # Default to local server if not set

# --- Custom CSS for Enhanced Aesthetics ---
st.markdown("""
<style>
/* General Body & Typography */
html, body, [data-testid="stAppViewContainer"] {
    background-color: var(--background-color); /* Use Streamlit's theme background */
    color: var(--text-color); /* Use Streamlit's theme text color */
    font-family: 'Segoe UI', 'Roboto', 'Helvetica Neue', Arial, sans-serif; /* Modern, readable font stack */
}

/* Header & Title */
h1 {
    color: var(--text-color);
    text-align: center;
    margin-bottom: 25px;
    font-size: 2.5em; /* Larger title */
    font-weight: 700; /* Bolder */
    letter-spacing: 0.05em; /* A little spacing for style */
    text-shadow: 1px 1px 2px rgba(0,0,0,0.1);
}
.stMarkdown p { /* For the tagline */
    text-align: center;
    color: var(--text-color);
    opacity: 0.7; /* Slightly faded tagline */
    font-size: 1.1em;
    margin-bottom: 30px;
}

/* Chat Container - The main chat window */
[data-testid="stVerticalBlock"] > [data-testid="stVerticalBlock"] > div:first-child { /* Targeting the specific block containing messages */
    min-height: 450px; /* Ensure a good minimum height */
    max-height: 60vh; /* Max height relative to viewport for responsiveness */
    overflow-y: auto; /* Scroll if content overflows */
    border: 1px solid var(--secondary-background-color); /* Subtle border */
    border-radius: 12px;
    padding: 15px;
    background-color: var(--secondary-background-color); /* Streamlit's secondary bg */
    box-shadow: 0 6px 15px rgba(0, 0, 0, 0.1); /* Softer, deeper shadow */
    margin-bottom: 20px;
    display: flex; /* Use flexbox for message alignment */
    flex-direction: column;
    gap: 10px; /* Space between messages */
}

/* Chat Bubbles */
.chat-bubble {
    padding: 12px 18px; /* Slightly more padding */
    border-radius: 25px; /* More rounded */
    max-width: 78%; /* Slightly less max-width */
    word-wrap: break-word;
    font-size: 0.98em;
    line-height: 1.5;
    box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1); /* Subtle shadow on bubbles */
}

.bot-bubble {
    background-color: #64B5F6; /* Softer, calming blue */
    color: white;
    text-align: left;
    margin-right: auto;
    border-bottom-left-radius: 5px; /* Unique shape */
    animation: slideInLeft 0.4s ease-out forwards; /* Entry animation */
    transform-origin: left center;
}

.user-bubble {
    background-color: #81C784; /* Fresh, natural green */
    color: white;
    text-align: right;
    margin-left: auto;
    border-bottom-right-radius: 5px; /* Unique shape */
    animation: slideInRight 0.4s ease-out forwards; /* Entry animation */
    transform-origin: right center;
}

/* Avatar Styling (optional, if you want custom ones) */
.st-chat-message-user > div[data-testid="stImage"] img,
.st-chat-message-assistant > div[data-testid="stImage"] img {
    border-radius: 50%; /* Make avatars round */
    border: 2px solid var(--primary-color); /* Border around avatar */
    object-fit: cover;
}

/* Input & Button Styling */
.st-chat-input input {
    border-radius: 25px;
    padding: 10px 20px; /* More internal padding */
    border: 1px solid var(--primary-color); /* Border color from theme */
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}
.st-chat-input button {
    border-radius: 25px;
    background-color: var(--primary-color); /* Use theme primary color */
    color: white;
    font-weight: bold;
    transition: background-color 0.3s ease;
}
.st-chat-input button:hover {
    background-color: var(--primary-color); /* Maintain theme color on hover */
    filter: brightness(1.1); /* Slightly brighter on hover */
}

/* Animations */
@keyframes slideInLeft {
  from { opacity: 0; transform: translateX(-20px); }
  to { opacity: 1; transform: translateX(0); }
}

@keyframes slideInRight {
  from { opacity: 0; transform: translateX(20px); }
  to { opacity: 1; transform: translateX(0); }
}

/* Scrollbar styling for a cleaner look */
::-webkit-scrollbar {
    width: 8px;
}

::-webkit-scrollbar-track {
    background: var(--secondary-background-color);
    border-radius: 10px;
}

::-webkit-scrollbar-thumb {
    background: var(--primary-color);
    border-radius: 10px;
}

::-webkit-scrollbar-thumb:hover {
    background: #555;
}

/* Streamlit's native message containers - ensure no double padding */
.st-chat-message-user, .st-chat-message-assistant {
    padding-left: 0rem !important;
    padding-right: 0rem !important;
    margin-bottom: 0px !important; /* Managed by gap in parent */
}

</style>
""", unsafe_allow_html=True)

# --- Session State Initialization ---
if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = []

# Initialize current time and date in session state
if "current_time" not in st.session_state:
    st.session_state.current_time = datetime.datetime.now()
if "current_date" not in st.session_state:
    st.session_state.current_date = datetime.date.today()


def get_bot_response(user_message: str) -> str:
    """
    Sends the user message to the FastAPI Gemini backend and returns the reply.
    """
    try:
        response = requests.post(API_URL, json={"text": user_message}, timeout=15)
        response.raise_for_status()
        return response.json().get("reply", "No reply received from AI.")
    except requests.exceptions.Timeout:
        return "The AI took too long to respond. Please try again."
    except requests.exceptions.ConnectionError:
        return "Could not connect to the AI server. Is it running?"
    except requests.exceptions.HTTPError as e:
        return f"Server error: {e}"
    except Exception as e:
        return f"Unexpected error: {e}"
# --- UI Layout ---
st.title("Calen AI Assistant")

chat_placeholder = st.container()

# Display chat messages using Streamlit's native chat elements
with chat_placeholder:
    for sender, message in st.session_state.chat_messages:
        if sender == "user":
            with st.chat_message("user", avatar="🧑"):
                # Using custom HTML for the bubble to apply specific CSS
                st.markdown(f"<div class='chat-bubble user-bubble'>{message}</div>", unsafe_allow_html=True)
        else:
            with st.chat_message("assistant", avatar="🤖"):
                # Using custom HTML for the bubble
                st.markdown(f"<div class='chat-bubble bot-bubble'>{message}</div>", unsafe_allow_html=True)

# User input at the bottom
user_input = st.chat_input("Type your message here...", key="chat_input")

if user_input:
    # Add user message to history
    st.session_state.chat_messages.append(("user", user_input))

    # Show a spinner while waiting for response
    with st.spinner("Processing..."):
        bot_reply = get_bot_response(user_input)

    # Add bot message to history
    st.session_state.chat_messages.append(("bot", bot_reply))

    st.rerun() 

