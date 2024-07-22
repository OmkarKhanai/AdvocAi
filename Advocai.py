import streamlit as st
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.chains.question_answering import load_qa_chain
from langchain.prompts import PromptTemplate
from langchain_community.vectorstores import FAISS
import google.generativeai as genai
from langchain_google_genai import GoogleGenerativeAIEmbeddings
import os
from dotenv import load_dotenv
import hashlib
import time
import json
from db import create_db, add_user, get_user, add_chat, get_chat_history, clear_chat_history
import base64

# Set the page configuration at the beginning
st.set_page_config(page_title="AdvocAI", page_icon=":scales:", layout="wide")

load_dotenv()
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

create_db()

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def get_conversational_chain():
    prompt_template = """
    You are AdvocAI, a highly experienced attorney providing legal advice based on Indian laws. 
    You will respond to the user's queries by leveraging your legal expertise and the Context Provided.
    Context: {context}
    Question: {question}
    Answer:
    """
    model = ChatGoogleGenerativeAI(
        model="gemini-1.5-flash-latest", 
        temperature=0.3, 
        system_instruction="You are AdvocAI, a highly experienced attorney providing legal advice based on Indian laws.",
    )
    prompt = PromptTemplate(template=prompt_template, input_variables=["context", "question"])
    chain = load_qa_chain(model, chain_type="stuff", prompt=prompt)
    return chain

def user_input(user_question):
    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
    new_db = FAISS.load_local("Faiss", embeddings, allow_dangerous_deserialization=True)
    docs = new_db.similarity_search(user_question)
    chain = get_conversational_chain()

    response = chain({"input_documents": docs, "question": user_question}, return_only_outputs=True)
    return response["output_text"]

def display_typing_effect(response):
    output = ""
    response_container = st.empty()
    for char in response:
        output += char
        response_container.markdown(output, unsafe_allow_html=True)
        time.sleep(0.005)
    return output

def save_session(username, session_name, session_data):
    session_id = f"{username}_{session_name}.json"
    with open(f"sessions/{session_id}", "w") as file:
        json.dump(session_data, file)
    return session_id

def load_session(session_id):
    try:
        with open(f"sessions/{session_id}", "r") as file:
            session_data = json.load(file)
        return session_data
    except FileNotFoundError:
        return None

def list_sessions(username):
    sessions = []
    for file in os.listdir("sessions"):
        if file.startswith(username):
            session_name = file[len(username) + 1:-5]
            sessions.append(session_name)
    return sessions

def delete_session(session_id):
    try:
        os.remove(f"sessions/{session_id}")
    except FileNotFoundError:
        pass

def delete_all_sessions(username):
    for file in os.listdir("sessions"):
        if file.startswith(username):
            os.remove(f"sessions/{file}")

def main():
    if not os.path.exists("sessions"):
        os.makedirs("sessions")
    
    # Custom CSS to style the login/signup buttons on the top right
    st.markdown("""
    <style>
    .header-button {
        position: absolute;
        right: 20px;
        top: 20px;
    }
    .sidebar .sidebar-content {
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        height: 100%;
        background-color: #f8f9fa;
    }
    .sidebar .sidebar-content h2 {
        font-size: 1.5em;
        font-weight: bold;
        color: #343a40;
    }
    .sidebar .sidebar-content button {
        margin: 5px 0;
        padding: 10px;
        border: none;
        background-color: #007bff;
        color: #ffffff;
        border-radius: 5px;
    }
    .sidebar .sidebar-content button:hover {
        background-color: #0056b3;
    }
    .stButton>button {
        width: 100%;
    }
    header {
        background-color: #007bff;
        color: white;
        padding: 10px 0;
        text-align: center;
        font-size: 2em;
        font-weight: bold;
    }
    .chat-message-user {
        background-color: #e9ecef;
        border-radius: 5px;
        padding: 10px;
        margin: 5px 0;
    }
    .chat-message-assistant {
        background-color: #f8f9fa;
        border-radius: 5px;
        padding: 10px;
        margin: 5px 0;
    }
    .stTextInput>div>input {
        padding: 10px;
        border-radius: 5px;
        border: 1px solid #ced4da;
    }
    .stTextInput>div>input:focus {
        border-color: #007bff;
    }
    .stTextInput>div>button {
        background-color: #007bff;
        color: #ffffff;
        border: none;
        padding: 10px;
        border-radius: 5px;
        margin-top: 10px;
    }
    .profile-container {
        display: flex;
        align-items: center;
        margin-bottom: 20px;
    }
    .profile-image {
        border-radius: 50%;
        width: 50px;
        height: 50px;
        margin-right: 10px;
    }
    .session-item {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 10px;
    }
    .session-item button {
        margin-left: 5px;
    }
    </style>
    """, unsafe_allow_html=True)
    
    st.header("AdvocAI: AI Lawyer ⚖️")
    
    if "authentication_status" not in st.session_state:
        st.session_state.authentication_status = None
    
    if st.session_state.authentication_status:
        st.sidebar.markdown(f"""
        <div class="profile-container">
            <img src="data:image/png;base64,{st.session_state.profile_image}" class="profile-image"/>
            <div>{st.session_state.username}</div>
        </div>
        """, unsafe_allow_html=True)
        st.sidebar.button("Logout", on_click=lambda: st.session_state.update({"authentication_status": False, "username": None, "profile_image": None, "messages": [], "current_session": None}))
        
        if st.sidebar.button("New Session"):
            st.session_state.current_session = None
            st.session_state.messages = [{"role": "assistant", "content": "Hi, I'm AdvocAI, an AI Legal Advisor."}]
            st.rerun()

        st.sidebar.write("## Previous Conversations")
        sessions = list_sessions(st.session_state.username)
        
        if sessions:
            for session_name in sessions:
                session_id = f"{st.session_state.username}_{session_name}.json"
                with st.sidebar:
                    col1, col2 = st.columns([9, 1])
                    with col1:
                        if st.button(session_name, key=f"session_{session_name}"):
                            chat_history = load_session(session_id)
                            if chat_history:
                                st.session_state.messages = chat_history
                                st.session_state.current_session = session_name
                            st.rerun()
                    with col2:
                        if st.button("🗑️", key=f"delete_{session_name}"):
                            st.session_state[f"confirm_delete_{session_name}"] = True

                    if f"confirm_delete_{session_name}" in st.session_state and st.session_state[f"confirm_delete_{session_name}"]:
                        st.sidebar.write(f"Are you sure you want to delete the session '{session_name}'?")
                        if st.sidebar.button("Yes", key=f"confirm_yes_{session_name}"):
                            delete_session(session_id)
                            del st.session_state[f"confirm_delete_{session_name}"]
                            st.rerun()
                        if st.sidebar.button("No", key=f"confirm_no_{session_name}"):
                            del st.session_state[f"confirm_delete_{session_name}"]
                            st.rerun()
        
        st.sidebar.write("")
        st.sidebar.write("")
        st.sidebar.button("Clear History", on_click=lambda: st.session_state.update({"clear_history": True}))
        
        if st.session_state.get("clear_history"):
            delete_all_sessions(st.session_state.username)
            st.session_state.clear_history = False
            st.session_state.current_session = None
            st.session_state.messages = [{"role": "assistant", "content": "Hi, I'm AdvocAI, an AI Legal Advisor."}]
            st.rerun()
        
        if "messages" not in st.session_state:
            st.session_state.messages = [
                {"role": "assistant", "content": "Hi, I'm AdvocAI, an AI Legal Advisor."}
            ]
        
        for message in st.session_state.messages:
            if isinstance(message, dict) and "role" in message and "content" in message:
                with st.chat_message(message["role"]):
                    st.write(message["content"])
        
        prompt = st.chat_input("Type your question here...")
        
        if prompt:
            if "current_session" not in st.session_state or st.session_state.current_session is None:
                response = user_input(prompt)
                summary = response[:30] + "..." if len(response) > 30 else response
                st.session_state.current_session = summary
                st.session_state.messages = [
                    {"role": "assistant", "content": "Hi, I'm AdvocAI, an AI Legal Advisor."}
                ]
                
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.write(prompt)
                add_chat(st.session_state.username, "user", prompt)
            
            if st.session_state.messages[-1]["role"] != "assistant":
                with st.chat_message("assistant"):
                    with st.spinner("Thinking..."):
                        response = user_input(prompt)
                        response_text = display_typing_effect(response)
                        add_chat(st.session_state.username, "assistant", response_text)
                    
                    if response is not None:
                        st.session_state.messages.append({"role": "assistant", "content": response_text})
            
            save_session(st.session_state.username, st.session_state.current_session, st.session_state.messages)
    else:
        menu = ["Login", "Sign Up"]
        choice = st.sidebar.selectbox("Menu", menu)
        
        if choice == "Login":
            st.subheader("Login")
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            if st.button("Login"):
                hashed_password = hash_password(password)
                user = get_user(username, hashed_password)
                if user:
                    st.session_state.update({"authentication_status": True, "username": username, "profile_image": user['profile_image'], "messages": [], "current_session": None})
                    st.rerun()
                else:
                    st.error("Username/password is incorrect")
        
        elif choice == "Sign Up":
            st.subheader("Create a New Account")
            new_username = st.text_input("Username")
            new_password = st.text_input("Password", type="password")
            confirm_password = st.text_input("Confirm Password", type="password")
            uploaded_file = st.file_uploader("Upload Profile Image", type=["png", "jpg", "jpeg"])
            
            if st.button("Sign Up"):
                if new_password == confirm_password:
                    hashed_password = hash_password(new_password)
                    if uploaded_file is not None:
                        image_bytes = uploaded_file.read()
                        profile_image = base64.b64encode(image_bytes).decode()
                    else:
                        profile_image = None
                    success = add_user(new_username, hashed_password, profile_image)
                    if success:
                        st.success("Account created successfully!")
                    else:
                        st.error("Username already exists. Please choose a different username.")
                else:
                    st.error("Passwords do not match. Please try again.")

if __name__ == "__main__":
    main()
