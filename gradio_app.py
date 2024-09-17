import gradio as gr
import requests
import json
import uuid
import concurrent.futures
from requests.exceptions import ChunkedEncodingError
from src.tarot import card_names
import os
from dotenv import load_dotenv
load_dotenv()

# Define the endpoints
host = os.getenv("BACKEND_URL")
default_endpoint = f"{host}/chat/default"
rag_endpoint = f"{host}/chat/rag"
history_endpoint = f"{host}/view_history"

def compare_chatbots(session_id, messages, model_id, temperature, seer_name, seer_personality, tarot_card):
    # Convert messages list to a single string    
    # Prepare the payloads
    print("tarot_card", tarot_card)
    payload_default = json.dumps({
        "session_id": session_id + "_default",
        "messages": messages,
        "model_id": model_id,
        "temperature": temperature,
        "tarot_card": tarot_card,
        "seer_name": seer_name,
        "seer_personality": seer_personality,
    })
    payload_rag = json.dumps({
        "session_id": session_id + "_rag",
        "messages": messages,
        "model_id": model_id,
        "temperature": temperature,
        "tarot_card": tarot_card,
        "seer_name": seer_name,
        "seer_personality": seer_personality,
    })
    headers = {
        'Content-Type': 'application/json'
    }

    def call_endpoint(url, payload):
        try:
            response = requests.request("POST", url, headers=headers, data=payload)
            if response.status_code == 200:
                try:
                    return response.text
                except requests.exceptions.JSONDecodeError:
                    return "Error: Response is not valid JSON"
            else:
                return f"Error: {response.status_code} - {response.text}"
        except ChunkedEncodingError:
            return "Error: Response ended prematurely"

    with concurrent.futures.ThreadPoolExecutor() as executor:
        future_default = executor.submit(call_endpoint, default_endpoint, payload_default)
        future_rag = executor.submit(call_endpoint, rag_endpoint, payload_rag)
        
        response_default_text = future_default.result()
        response_rag_text = future_rag.result()

    return response_default_text, response_rag_text

# Function to handle chat interaction
def chat_interaction(session_id, message, model_id, temperature, seer_name, seer_personality, chat_history_default, chat_history_rag, tarot_card):
    response_default, response_rag = compare_chatbots(session_id, message, model_id, temperature, seer_name, seer_personality, tarot_card)
    
    chat_history_default.append((message, response_default))
    chat_history_rag.append((message, response_rag))
    
    message = ""
    tarot_card = []
    return message, chat_history_default, chat_history_rag, tarot_card

# Function to reload session ID and clear chat history
def reload_session_and_clear_chat():
    new_session_id = str(uuid.uuid4())
    new_session_id_rag = f"{new_session_id}_rag"
    return new_session_id, new_session_id_rag, [], []

# Function to load chat history
def load_chat_history(session_id):
    try:
        response = requests.get(f"{history_endpoint}?session_id={session_id}")
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": f"Error: {response.status_code} - {response.text}"}
    except Exception as e:
        return {"error": str(e)}

# Create the Gradio interface
with gr.Blocks() as demo:
    gr.Markdown("# Chatbot Comparison")
    
    with gr.Row():
        with gr.Column():
            gr.Markdown("## Default Chatbot")
            chatbot_default = gr.Chatbot(elem_id="chatbot_default")
        
        with gr.Column():
            gr.Markdown("## Rag Chatbot")
            chatbot_rag = gr.Chatbot(elem_id="chatbot_rag")
    
    with gr.Row():
        message = gr.Textbox(label="Message", show_label=False, scale=3)
        submit_button = gr.Button("Submit", scale=1, variant="primary")
    
    session_id_default = str(uuid.uuid4())

    model_id_choices = [
        "llama-3.1-8b-instant",
        "llama-3.1-70b-versatile",
        "typhoon-v1.5-instruct", 
        "typhoon-v1.5x-70b-instruct", 
        "gemma2-9b-it",
        ]

    with gr.Accordion("Settings", open=False):
        reload_button = gr.Button("Reload Session", scale=1, variant="secondary")
        session_id = gr.Textbox(label="Session ID", value=session_id_default)
        model_id = gr.Dropdown(label="Model ID", choices=model_id_choices, value=model_id_choices[0])
        temperature = gr.Slider(0, 1, step=0.1, label="Temperature", value=0.5)
        seer_name = gr.Textbox(label="Seer Name", value="แม่หมอแพตตี้")
        seer_personality = gr.Textbox(label="Seer Personality", value="You are a friend who is always ready to help.")
        tarot_card = gr.Dropdown(label="Tarot Card", value=[], choices=card_names, multiselect=True)

    with gr.Accordion("View History of Rag Chatbot", open=False):
        session_id_rag = gr.Textbox(label="Session ID", value=f"{session_id_default}_rag")
        load_history_button = gr.Button("Load Chat History", scale=1, variant="secondary")  # New button
        chat_history_json = gr.JSON(label="Chat History")  # New JSON field
    
    submit_button.click(
        lambda session_id, message, model_id, temperature, seer_name, seer_personality, chatbot_default, chatbot_rag, tarot_card: chat_interaction(
            session_id, message, model_id, temperature, seer_name, seer_personality, chatbot_default, chatbot_rag, tarot_card
        ),
        inputs=[session_id, message, model_id, temperature, seer_name, seer_personality, chatbot_default, chatbot_rag, tarot_card],
        outputs=[message, chatbot_default, chatbot_rag, tarot_card]
    )

    message.submit(
        lambda session_id, message, model_id, temperature, seer_name, seer_personality, chatbot_default, chatbot_rag, tarot_card: chat_interaction(
            session_id, message, model_id, temperature, seer_name, seer_personality, chatbot_default, chatbot_rag, tarot_card
        ),
        inputs=[session_id, message, model_id, temperature, seer_name, seer_personality, chatbot_default, chatbot_rag, tarot_card],
        outputs=[message, chatbot_default, chatbot_rag, tarot_card]
    )

    reload_button.click(
        reload_session_and_clear_chat,
        inputs=[],
        outputs=[session_id, session_id_rag, chatbot_default, chatbot_rag]
    )

    load_history_button.click(
        load_chat_history,
        inputs=[session_id_rag],
        outputs=[chat_history_json]
    )

# Launch the interface
demo.launch(show_api=False)