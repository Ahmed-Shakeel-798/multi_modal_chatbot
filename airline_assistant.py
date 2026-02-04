import os
import json
from openai import OpenAI
import gradio as gr
from dotenv import load_dotenv

load_dotenv(override=True)

google_api_key = os.getenv("GOOGLE_API_KEY")

# Initialize OpenAI client for Google Gemini
client = OpenAI(
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
    api_key=google_api_key
)
MODEL = "gemini-3-flash-preview"

system_message = """
You are FlightAI, an automated airline assistant.

Rules you MUST follow:
- If the user asks for a ticket price, you MUST call the get_ticket_price tool.
- Do NOT ask follow-up questions when the answer can be obtained from a tool.
- Do NOT invent booking steps, passport requests, or travel requirements unless explicitly asked.
- After a tool response, repeat ONLY the tool result as your final answer.
- Never output JSON or function names to the user.
- Keep responses to ONE short sentence.

If the user asks something you do not know and no tool applies, say:
"I’m sorry, I don’t have that information."

"""

def chat(message, history):
    history = [{"role":h["role"], "content":h["content"]} for h in history]
    messages = [{"role": "system", "content": system_message}] + history + [{"role": "user", "content": message}]
    response = client.chat.completions.create(model=MODEL, messages=messages, tools=tools, tool_choice="auto")

    if response.choices[0].finish_reason == "tool_calls":
        message = response.choices[0].message
        response = handle_tool_call(message)
        messages.append(message)
        messages.append(response)
        response = client.chat.completions.create(model=MODEL, messages=messages)

    return response.choices[0].message.content


ticket_prices = {"london": "$799", "paris": "$899", "tokyo": "$1400", "berlin": "$499"}

def get_ticket_price(destination_city):
    print(f"Tool called for city {destination_city}")
    price = ticket_prices.get(destination_city.lower(), "Unknown ticket price")
    return f"The price of a ticket to {destination_city} is {price}"


price_function = {
    "name": "get_ticket_price",
    "description": "Get the price of a return ticket to the destination city.",
    "parameters": {
        "type": "object",
        "properties": {
            "destination_city": {
                "type": "string",
                "description": "The city that the customer wants to travel to",
            },
        },
        "required": ["destination_city"],
        "additionalProperties": False
    }
}


def handle_tool_call(message):
    tool_call = message.tool_calls[0]
    if tool_call.function.name == "get_ticket_price":
        arguments = json.loads(tool_call.function.arguments)
        city = arguments.get('destination_city')
        price_details = get_ticket_price(city)
        response = {
            "role": "tool",
            "content": price_details,
            "tool_call_id": tool_call.id
        }
    return response


tools = [{"type": "function", "function": price_function}]


gr.ChatInterface(fn=chat, title="Airline Assistant").launch()