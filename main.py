import os
from dotenv import load_dotenv
from openai import OpenAI
import gradio as gr

load_dotenv(override=True)

google_api_key = os.getenv("GOOGLE_API_KEY")

# Initialize OpenAI client for Google Gemini
client = OpenAI(
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
    api_key=google_api_key
)
model = "gemini-3-flash-preview"


# Load the text of the Second Night
with open("white_nights_second_night.txt", "r", encoding="utf-8") as f:
    second_night = f.read()


# system prompt for the LLM
SYSTEM_PROMPT = f"""
You are a professor with expertise in literature and human psychology answering questions strictly about
Fyodor Dostoevsky’s short story *White Nights*, focusing ONLY on
the section titled “Second Night”.

For context, here is the full text of the Second Night:

{second_night}

Rules:
- Do NOT reference events from the First Night beyond minimal context
- Do NOT reference anything from the Third or Fourth Night
- If a question requires knowledge outside the Second Night, say:
  "That is not addressed in the Second Night."
- Answer in a literary-analytical tone
- Focus on emotional subtext, symbolism, and character psychology
"""

# Function to get streaming response from Gemini
def ask_second_night(question: str, history=None):
    stream = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": question}
        ],
        temperature=0.3,
        stream=True  # important for streaming
    )
    full_response = ""

    for chunk in stream:
        delta = chunk.choices[0].delta.content
        if delta:
            full_response += delta
            yield full_response


demo = gr.ChatInterface(fn=ask_second_night, title="White Nights — Second Night")
demo.launch()