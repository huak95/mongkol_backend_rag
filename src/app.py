from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Generator
from sqlalchemy.orm import Session
import time
import os
from src.template import *
from src.models import Session as DBSession, Message, SessionLocal, init_db
from src.tarot import card_name_to_description
import json

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # List of allowed origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Initialize the database
init_db()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def generate_streaming_response(response, db_session_id: int, db: Session, request) -> Generator[str, None, None]:
    partial_message = ""
    for i, chunk in enumerate(response):
        message = chunk.choices[0].delta.content
        if message is not None:
            partial_message += message
            yield message

    # Save the complete response to the database
    db_session = db.query(DBSession).filter(DBSession.id == db_session_id).first()
    if db_session:
        db_message = Message(session_id=db_session.id, role="assistant", content=partial_message, model_id=request.model_id)
        db.add(db_message)
        db.commit()

def get_or_create_session(request, db: Session):
    # Retrieve or create session
    db_session = db.query(DBSession).filter(DBSession.session_id == request.session_id).first()
    if not db_session:
        db_session = DBSession(session_id=request.session_id)
        db.add(db_session)
        db.commit()
        db.refresh(db_session)
    return db_session

def save_user_message(db_session, request, db: Session, use_rag=False):
    # Save request message to the database

    if len(request.tarot_card) > 0:
        tarot_card_str = ", ".join(request.tarot_card)

        if use_rag:
            card_prompts = ""
            for card in request.tarot_card:
                description = card_name_to_description[card]
                card_prompts += f"{card}: {description}"

            prompt = f"ฉันเห็นว่าคุณเลือกไพ่นะคะ ไพ่ที่คุณเลือก {tarot_card_str} \n\n โดยไพ่แต่ละใบมีความหมายดังนี้ \n\n {card_prompts}"

        else:
            prompt = f"ฉันเห็นว่าคุณเลือกไพ่ ไพ่ที่คุณเลือก {tarot_card_str} นะคะ"

        db_message = Message(session_id=db_session.id, role="assistant", content=prompt, model_id=request.model_id)
        db.add(db_message)
        db_message = Message(session_id=db_session.id, role="user", content=f"เลือกไพ่เรียบร้อยแล้ว อธิบายดวงจากไพ่ให้หน่อย โดยเรื่มพูดจากประโยคหนึ่งสั้นๆที่บอกเกี่ยวกับดวง และ อธิบายเป็นอีกสามประโยค", model_id=request.model_id)
        db.add(db_message)
        db.commit()
    else:
        db_message = Message(session_id=db_session.id, role="user", content=request.messages, model_id=request.model_id)
        db.add(db_message)
        db.commit()

def get_chat_history(db_session, request, db: Session):
    # Retrieve chat history from the database
    chat_history = db.query(Message).filter(Message.session_id == db_session.id).order_by(Message.id).all()
    history_openai_format = [{"role": "system", "content": get_default_system_prompt(request.seer_name, request.seer_personality)}]
    for message in chat_history:
        history_openai_format.append({"role": message.role, "content": message.content})
    return history_openai_format

def get_chat_history_by_session_id(session_id: str, db: Session):
    # Retrieve chat history using only the session_id
    db_session = db.query(DBSession).filter(DBSession.session_id == session_id).first()
    if not db_session:
        raise HTTPException(status_code=404, detail="Session not found")

    chat_history = db.query(Message).filter(Message.session_id == db_session.id).order_by(Message.id).all()
    history = [{"role": message.role, "content": message.content, "model_id": message.model_id} for message in chat_history]
    return history

@app.post("/chat/rag")
async def chat_completions_stream(request: ChatRequest, db: Session = Depends(get_db)):
    try:
        db_session = get_or_create_session(request, db)
        save_user_message(db_session, request, db, use_rag=True)
        history_openai_format = get_chat_history(db_session, request, db)

        client = get_client(request.model_id)   
        response = client.chat.completions.create(
            model=request.model_id,
            messages=history_openai_format,
            temperature=request.temperature,
            stream=True
        )
        return StreamingResponse(generate_streaming_response(response, db_session.id, db, request), media_type="text/plain")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/chat/default")
async def chat_completions_stream(request: ChatRequest, db: Session = Depends(get_db)):
    try:
        db_session = get_or_create_session(request, db)
        save_user_message(db_session, request, db)
        history_openai_format = get_chat_history(db_session, request, db)

        client = get_client(request.model_id)   
        response = client.chat.completions.create(
            model=request.model_id,
            messages=history_openai_format,
            temperature=request.temperature,
            stream=True
        )
        return StreamingResponse(generate_streaming_response(response, db_session.id, db, request), media_type="text/plain")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/chat/memory")
async def chat_completions_with_memory_stream(request: ChatRequestWithMemory, db: Session = Depends(get_db)):
    try:
        db_session = get_or_create_session(request, db)
        save_user_message(db_session, request, db)
        history_openai_format = get_chat_history(db_session, request, db)

        client = get_client(request.model_id)
        if len(history_openai_format) > request.summary_threshold:
            # Prepare the conversation history for summarization
            system_prompt = [{'role': 'system', 'content': 'Summarize the following conversation into a paragraph that have about 300 words in Thai.'}]
            history_combine = system_prompt + [{'role': 'user', 'content': str(json.dumps(history_openai_format[1:], ensure_ascii=False))}]

            # Request summary from OpenAI
            response = client.chat.completions.create(
                model=request.model_id,
                messages=history_combine,
                temperature=request.temperature,
                stream=False
            )

            # Generate memory summary
            summarized_history = response.choices[0].message.content

            # Prepare the new history format
            history_openai_format_memory = [
                {"role": "system", "content": get_default_system_prompt(request.seer_name, request.seer_personality)},
                {"role": "system", "content": f"conversation summary: \n{summarized_history}"},
            ]
            history_openai_format_memory.extend(history_openai_format[-2:])
            # history_openai_format_memory.append({"role": "user", "content": request.messages})    

            # Remove old chat history from the database
            db.query(Message).filter(Message.session_id == db_session.id).delete()
            db.commit()

            # Save the new history to the database
            db.add_all([
                Message(session_id=db_session.id, role=msg["role"], content=msg["content"], model_id=request.model_id)
                for msg in history_openai_format_memory[1:]
            ])
            db.commit()

            # Add the new user message to the history
            response = client.chat.completions.create(
                model=request.model_id,
                messages=history_openai_format_memory,
                temperature=request.temperature,
                stream=True
            )
        else:
            response = client.chat.completions.create(
                model=request.model_id,
                messages=history_openai_format,
                temperature=request.temperature,
                stream=True
            )

        return StreamingResponse(generate_streaming_response(response, db_session.id, db, request), media_type="text/plain")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/view_history")
async def view_chat_history(session_id: str, db: Session = Depends(get_db)):
    try:
        history = get_chat_history_by_session_id(session_id, db)
        return {"session_id": session_id, "history": history}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/delete_history")
async def delete_chat_history(session_id: str, db: Session = Depends(get_db)):
    try:
        # Retrieve session
        db_session = db.query(DBSession).filter(DBSession.session_id == session_id).first()
        if not db_session:
            raise HTTPException(status_code=404, detail="Session not found")

        # Delete chat history from the database
        db.query(Message).filter(Message.session_id == db_session.id).delete()
        db.commit()

        return {"message": "Chat history deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/list_sessions")
async def list_sessions(db: Session = Depends(get_db)):
    try:
        sessions = db.query(DBSession).all()
        session_info = [
            {"session_id": session.session_id, "message_count": db.query(Message).filter(Message.session_id == session.id).count()}
            for session in sessions
        ]
        return {"sessions": session_info}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))