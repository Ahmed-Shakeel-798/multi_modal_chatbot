import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(override=True)

google_api_key = os.getenv("GOOGLE_API_KEY")

client = OpenAI(
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
    api_key=google_api_key
)

with open("white_nights_second_night.txt", "r", encoding="utf-8") as f:
    second_night = f.read()

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

def ask_second_night(question: str) -> str:
    response = client.chat.completions.create(
        model="gemini-3-flash-preview",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": question}
        ],
        temperature=0.3
    )

    print(f"Input tokens: {response.usage.prompt_tokens}")
    print(f"Output tokens: {response.usage.completion_tokens}")
    print(f"Total tokens: {response.usage.total_tokens}")

    return response.choices[0].message.content


if __name__ == "__main__":
    print("White Nights — Second Night Analyzer\n")

    while True:
        user_input = input("> ")
        if user_input.lower() == "exit":
            break

        answer = ask_second_night(user_input)
        print("\nResult:")
        print(answer)
        print()
