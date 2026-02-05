import os
from dotenv import load_dotenv
from openai import OpenAI
import gradio as gr
import sqlite3
import uuid
from datetime import datetime, timezone
import json

#### LOAD ENVIRONMENT VARIABLES & SET CONSTANTS ####
load_dotenv(override=True)

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
DB_PATH = os.getenv("DB_PATH")

MODEL = "gemini-2.5-flash-lite"

CURRENT_SESSION_ID = str(uuid.uuid4())
IS_SAVED_SESSION = False

#### LOAD SECOND NIGHT TEXT ####
with open("white_nights_second_night.txt", "r", encoding="utf-8") as f:
    second_night = f.read()


#### SYSTEM PROMPT ####
SYSTEM_PROMPT = f"""
You are a professor with expertise in literature and human psychology answering questions strictly about
Fyodor Dostoevsky’s short story *White Nights*, focusing ONLY on
the section titled “Second Night”.

For context, here is the full text of the Second Night:

{second_night}

You have tools available:

1) If the user says:
   "save this conversation as X"
   → generate a 1–2 line summary
   → call save_conversation(name=X, summary=generated_summary)

2) If user asks:
   "show previous conversations"
   → call list_conversations

3) If user says:
   "load conversation 2"
   → call load_conversation(index=2)

4) If the user says:
   "start a new conversation"
   → call start_new_conversation

Rules:
- Do NOT reference events from the First Night beyond minimal context
- Do NOT reference anything from the Third or Fourth Night
- If a question requires knowledge outside the Second Night, say:
  "That is not addressed in the Second Night."
- Answer in a literary-analytical tone
- Focus on emotional subtext, symbolism, and character psychology
"""


#### DATABASE SETUP ####
def init_db():
    print(f"[DB] Initializing database at {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            session_id TEXT PRIMARY KEY,
            name TEXT,
            summary TEXT,
            created_at TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            role TEXT,
            content TEXT,
            created_at TEXT
        )
    """)

    conn.commit()
    conn.close()
    print("[DB] Database initialization complete")


init_db()

#### DATABSE FUNCTIONS ####
def save_conversation(session_id, name, summary):
    print(f"[DB] Saving conversation: name={name}, session_id={session_id}")
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute("""
        INSERT OR REPLACE INTO conversations (session_id, name, summary, created_at)
        VALUES (?, ?, ?, ?)
    """, (session_id, name, summary, datetime.now(timezone.utc).isoformat()))

    conn.commit()
    conn.close()
    print(f"[DB] Conversation saved successfully")


def list_conversations():
    print("[DB] Listing all conversations")
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute("SELECT session_id, name, summary FROM conversations ORDER BY created_at DESC")
    rows = c.fetchall()
    conn.close()
    print(f"[DB] Found {len(rows)} conversations")
    return rows


def load_conversation_by_index(index):
    print(f"[DB] Loading conversation at index {index}")
    rows = list_conversations()
    if index < 1 or index > len(rows):
        print(f"[DB] Invalid index {index}. Total conversations: {len(rows)}")
        return None
    session_id = rows[index - 1][0]
    print(f"[DB] Loaded session_id: {session_id}")
    return session_id


def save_message(session_id, role, content): 
    print(f"[DB] Saving message - role: {role}, session_id: {session_id[:8]}..., content_len: {len(content)}")
    conn = sqlite3.connect(DB_PATH) 
    c = conn.cursor() 
    c.execute( "INSERT INTO messages (session_id, role, content, created_at) VALUES (?, ?, ?, ?)", 
              (session_id, role, content, datetime.now(timezone.utc).isoformat()) )
    
    conn.commit() 
    conn.close()
    print(f"[DB] Message saved")


def load_history(session_id): 
    print(f"[DB] Loading history for session_id: {session_id[:8]}...")
    conn = sqlite3.connect(DB_PATH) 
    c = conn.cursor() 
    c.execute( "SELECT role, content FROM messages WHERE session_id=? ORDER BY id ASC", (session_id,) ) 
    
    rows = c.fetchall() 
    conn.close()
    print(f"[DB] Loaded {len(rows)} messages from history")
    
    return [{"role": role, "content": content} for role, content in rows]


#### TOOL DEFINITIONS ####
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "save_conversation",
            "description": "Save the current conversation with a name and summary",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "summary": {"type": "string"}
                },
                "required": ["name", "summary"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_conversations",
            "description": "List all saved conversations"
        }
    },
    {
        "type": "function",
        "function": {
            "name": "load_conversation",
            "description": "Load a saved conversation by its index number",
            "parameters": {
                "type": "object",
                "properties": {
                    "index": {"type": "integer"}
                },
                "required": ["index"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "start_new_conversation",
            "description": "Start a brand new conversation session with a new session ID"
        }
    }
]


### OPENAI CLIENT SETUP ####
client = OpenAI(
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
    api_key=GOOGLE_API_KEY
)


#### FUNCTION TO HANDLE CHAT WITH STREAMING RESPONSE ####
def ask_second_night(question: str, history, session_state):
    print(f"\n[CHAT] New question received. Session: {session_state['id'][:8]}..., Saved: {session_state['is_saved']}")
    print(f"[CHAT] Question: {question[:100]}..." if len(question) > 100 else f"[CHAT] Question: {question}")

    past_messages = [{"role": h["role"], "content": h["content"]} for h in history]
    print(f"[CHAT] History has {len(past_messages)} messages")

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(past_messages)
    messages.append({"role": "user", "content": question})

    print(f"[API] Calling {MODEL} with {len(messages)} messages")
    response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        tools=TOOLS,
        tool_choice="auto"
    )

    response_message = response.choices[0].message
    print(f"[API] Response received")
    print(f"[API] Finish reason: {response.choices[0].finish_reason}")

    # TOOL CALL HANDLING
    if response_message.tool_calls:
        print(f"[TOOL] Detected {len(response_message.tool_calls)} tool call(s)")
        for tool_call in response_message.tool_calls:
            name = tool_call.function.name
            args = json.loads(tool_call.function.arguments)
            print(f"[TOOL] Executing: {name} with args: {args}")

            result_content = ""
            if name == "save_conversation":
                print(f"[TOOL] save_conversation handler called")
                if not session_state["is_saved"]:
                    print(f"[TOOL] Saving new conversation: {args['name']}")
                    save_conversation(session_state['id'], args["name"], args["summary"])

                    for msg in past_messages:
                        content = normalize_content(msg["content"])
                        save_message(session_state['id'], msg["role"], content)

                    session_state["is_saved"] = True
                    result_content = f"SUCCESS: Saved as {args['name']}"
                    print(f"[TOOL] Conversation marked as saved")
                else :
                    result_content = "This conversation is already saved."
                    print(f"[TOOL] Conversation already saved, skipping")

            elif name == "list_conversations":
                print(f"[TOOL] list_conversations handler called")
                rows = list_conversations()
                if not rows:
                    result_content = "No saved conversations."
                    print(f"[TOOL] No conversations found")
                else:
                    text = ""
                    for i, (_, n, s) in enumerate(rows, 1):
                        text += f"{i}. {n} — {s}\n"
                    result_content = text
                    print(f"[TOOL] Listed {len(rows)} conversations")

            elif name == "load_conversation":
                print(f"[TOOL] load_conversation handler called for index {args['index']}")
                session_id = load_conversation_by_index(args["index"])
                if not session_id:
                    result_content = "Invalid conversation number."
                    print(f"[TOOL] Failed to load conversation")
                else:
                    history = load_history(session_id) # load the message history of the selected conversation
                    print(f"[TOOL] Loaded {len(history)} messages from conversation")
                    session_state['id'] = session_id
                    session_state["is_saved"] = True
                    result_content = f"Loaded conversation {args['index']}."
                    print(f"[TOOL] Conversation loaded successfully")

            elif name == "start_new_conversation":
                print(f"[TOOL] start_new_conversation handler called")

                new_session_id = str(uuid.uuid4())
                session_state["id"] = new_session_id
                session_state["is_saved"] = False

                result_content = f"Started a new conversation (session {new_session_id[:8]}...)."
                print(f"[TOOL] New session created: {new_session_id[:8]}...")

            # Send the tool response back to the model for further processing
            messages.append(response_message) # Add assistant's tool call
            messages.append({
                "tool_call_id": tool_call.id,
                "role": "tool",
                "name": name,
                "content": result_content
            }) # Add tool response
            print(f"[TOOL] Tool response added to message chain")
            
        print(f"[API] Calling {MODEL} again with tool responses")
        final_response = client.chat.completions.create(model=MODEL, messages=messages)
        answer = final_response.choices[0].message.content or ""
        print(f"[API] Final response received from model")
    else:
        answer = response_message.content or ""
        print(f"[API] No tool calls, using direct response")
        

    if session_state['is_saved']:
        print(f"[CHAT] Saving messages to database")
        save_message(session_state['id'], "user", question)
        save_message(session_state['id'], "assistant", answer)
    else:
        print(f"[CHAT] Session not saved, skipping message persistence")

    print(f"[CHAT] Returning answer (length: {len(answer)})\n")
    return answer


def normalize_content(content):
    if isinstance(content, str):
        return content

    if isinstance(content, list):
        texts = []
        for part in content:
            if isinstance(part, dict) and "text" in part:
                texts.append(part["text"])
            else:
                texts.append(str(part))
        return " ".join(texts)

    return str(content)


with gr.Blocks() as demo:
    session_state = gr.State({
        "id": str(uuid.uuid4()),
        "is_saved": False
    })
    print(f"[UI] Created new Gradio session with state: {session_state}")
    
    chat = gr.ChatInterface(
        fn=ask_second_night,
        additional_inputs=[session_state],
        title="White Nights — Second Night"
    )

print("[UI] Launching Gradio interface...")
demo.launch()