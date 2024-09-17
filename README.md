# Backend

This guide provides instructions on how to install dependencies, run the API server, and invoke the API using cURL.

## Install Dependencies

To set up the Python environment and install all required dependencies, follow these steps:

```bash
conda create -n raghack python=3.10 -y
conda activate raghack
pip install -r requirements.txt
```

## Run API

To start the API server, use the following command:

```bash
uvicorn main:app --reload

# and run gradio to test out api
gradio gradio_app.py
```

- The `--reload` flag allows the server to automatically reload if there are code changes, which is helpful for development.

## Invoke API

You can invoke the API to test its functionality using `curl`. Below is an example of how to send a streaming request to the API:

### Field Explanation
- `messages`: This field contains the user's message. In this example, it is a greeting in Thai: "สวัสดีครับ ผมมีเรื่องมาปรึกษา".

- `seer_name`: This field specifies the name of the seer or the assistant. In this example, it is "แม่หมอแพตตี้".

- `seer_personality`: This field specifies the personality of the seer or the assistant. In this example, it is "You are a friend who is always ready to help."

- `session_id`: This field is a unique identifier for the session. It can be any string, but it is typically a UUID (Universally Unique Identifier). In this example, it is represented as "<uuid4>_memory" indicating a session with memory capabilities.

- `model_id`: This field specifies the model to be used for generating responses. In this example, it is "llama-3.1-8b-instant," which is a hypothetical model identifier.

- `temperature`: This field controls the randomness of the model's responses. A lower value (e.g., 0.6) makes the output more deterministic, while a higher value makes it more random.

- `summary_threshold`: This field specifies the number of messages after which the conversation history should be summarized. In this example, the threshold is set to 10 messages. This is only applicable memory api route.

- `tarot_card`: This optional field contains the name of the tarot card selected by the user. In this example, it is "The Fool." If no tarot card is selected, this field can be left empty or omitted.

```bash
# Chat Default
curl --location 'http://127.0.0.1:8000/chat/default' \
--header 'Content-Type: application/json' \
--data '{
    "messages": "สวัสดีครับ ผมมีเรื่องมาปรึกษา",
    "seer_name": "แม่หมอแพตตี้",
    "seer_personality": "You are a friend who is always ready to help.",
    "session_id": "<uuid4>_default",
    "model_id": "llama-3.1-8b-instant",
    "temperature": 0.6,
    "tarot_card": ["The Fool", "The Magician"] # optional
}'

# Chat Rag
curl --location 'http://127.0.0.1:8000/chat/rag' \
--header 'Content-Type: application/json' \
--data '{
    "messages": "สวัสดีครับ ผมมีเรื่องมาปรึกษา",
    "seer_name": "แม่หมอแพตตี้",
    "seer_personality": "You are a friend who is always ready to help.",
    "session_id": "<uuid4>_rag",
    "model_id": "llama-3.1-8b-instant",
    "temperature": 0.6,
    "tarot_card": ["The Fool", "The Magician"] # optional
}'


# Chat with memory
curl --location 'http://127.0.0.1:8000/chat/memory' \
--header 'Content-Type: application/json' \
--data '{
    "messages": "สวัสดีครับ ผมมีเรื่องมาปรึกษา",
    "seer_name": "แม่หมอแพตตี้",
    "seer_personality": "You are a friend who is always ready to help.",
    "session_id": "<uuid4>_memory",
    "model_id": "llama-3.1-8b-instant",
    "temperature": 0.6,
    "summary_threshold": 10,
    "tarot_card": ["The Fool", "The Magician"] # optional
}'

# View history
curl -X GET "http://127.0.0.1:8000/view_history?session_id=1234"

# Delete History
curl -X DELETE "http://127.0.0.1:8000/delete_history?session_id=1234"

# List Sessions
curl -X GET http://127.0.0.1:8080/list_sessions
```

# Total Model ID Supported

- `llama-3.1-8b-instant` (groq)
- `llama-3.1-70b-versatile` (groq)
- `gemma2-9b-it` (groq)
- `typhoon-v1.5-instruct` (open typhoon)
- `typhoon-v1.5x-70b-instruct` (open typhoon)