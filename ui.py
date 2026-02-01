import gradio as gr
from main import ask_second_night
import re

DESCRIPTION = """
**White Nights — Second Night**

A quiet literary companion for Dostoevsky’s *White Nights*.

Ask questions, share reflections, or explore the emotional and psychological
undertones of the **Second Night**.  
Responses are grounded strictly in the text, with a literary, seminar-style tone.
"""

def highlight_quotes(text):
    # Italicize text inside quotes
    return re.sub(r'“(.*?)”', r'*“\1”*', text)

def chat_with_professor(message, history):
    history.append({"role": "user", "content": message})
    answer = ask_second_night(message)
    answer = highlight_quotes(answer)
    history.append({"role": "assistant", "content": answer})
    return history, ""

# Gradio UI
with gr.Blocks() as demo:

    gr.Markdown(
        """
        # ☕ White Nights — Second Night  
        *A quiet conversation with Dostoevsky*
        """
    )

    gr.Markdown(DESCRIPTION)

    chatbot = gr.Chatbot(label="Conversation", height=500)  # <- removed `type`
    msg = gr.Textbox(
        placeholder="Ask a question, or share a thought from the Second Night…",
        label="Your message"
    )
    clear = gr.Button("Clear conversation")

    msg.submit(chat_with_professor, [msg, chatbot], [chatbot, msg])
    clear.click(lambda: [], None, chatbot)

# Launch with theme and CSS (Gradio 6+)
demo.launch(
    theme=gr.themes.Soft(
        primary_hue="amber",
        secondary_hue="orange",
        neutral_hue="stone",
        font=["Georgia", "serif"]
    ),
    css="""
        body {
            background-color: #f5efe6;
            font-family: Georgia, serif;
        }
        .gr-chatbot {
            background-color: #fffaf3;
            border-radius: 12px;
            padding: 12px;
            box-shadow: inset 0 0 10px #f0e5d8;
        }
        .gr-button {
            background-color: #d6b48c;
            border: none;
            color: #2f1e13;
            font-weight: bold;
        }
        .gr-button:hover {
            background-color: #caa472;
        }
        .gr-textbox textarea {
            background-color: #fdf6ec;
            border-radius: 6px;
            border: 1px solid #e0d5c2;
            padding: 6px;
        }
    """
)
