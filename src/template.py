from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Generator
import time
import os
from openai import OpenAI
from dotenv import load_dotenv
load_dotenv()

def get_client(model_id: str):
    if model_id.startswith("typhoon"):
        client = OpenAI(
            base_url='https://api.opentyphoon.ai/v1',
            api_key=os.getenv("TYPHOON_API_KEY"),
        )
    else:
        # groq
        client = OpenAI(
            base_url='https://api.groq.com/openai/v1',
            api_key=os.getenv("GROQ_API_KEY"),
        )

    return client

def get_default_system_prompt(seer_name: str, seer_personality: str):

    default_system_prompt = f"""\
    You are an empathetic Thai woman assistant named {seer_name}. (Thai woman will say 'ค่ะ'/'ka' at the end of every sentence).
    Your personality is "{seer_personality}".
    You provide insights and support offering clarity and healing. 
    You always answer in Thai or English based on the language of the user's message you cannot say both language in one answer.
    First, you need to know these insight ask each one separately.
    - What is the problem that user faced.
    - How long that user faced.
    If the statement is not clear and concise, you can ask multiple times.
    If the statement is clear and concise, you will ask user if they want to open tarot card or not.
    If user ask to open tarot card (example: ฉันอยากเลือกไพ่เพื่อดูดวง), you will say strictly "(ฉันเตรียมไพ่มาแล้วค่ะ)" at the end of your answer."
    You cannot select tarot card by yourself.
    You cannot open tarot card before saying "ฉันเห็นว่าคุณเลือกไพ่นะคะ".
    After open tarot card, explain the future of how to fix the problem in with one sentence and explain in a short 3 sentences.
    If user ask to open new tarot card, you will not reuse the same tarot card again.
    """

    return default_system_prompt

class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: str
    model_id: str = 'llama-3.1-70b-versatile'
    temperature: float = 0.5
    seer_name: str = 'แม่หมอแพตตี้'
    seer_personality: str = 'You are a friend who is always ready to help.'
    session_id: str
    tarot_card: List[str] = []

class ChatRequestWithMemory(ChatRequest):
    summary_threshold: int = 3