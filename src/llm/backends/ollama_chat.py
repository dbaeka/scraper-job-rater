from ollama import Client

from src.utils.helpers import get_config

ollama_client = Client()
config = get_config()
model_config = config.get("ollama", {})
model_name = model_config.get("model", "llama3.1")
temperature = model_config.get("temperature", 0.7)


def generate(prompt):
    response = ollama_client.chat(
        model=model_name,
        messages=[{"role": "user", "content": prompt}],
        options={
            "temperature": temperature,
        }
    )

    is_thinking = check_is_thinking(response['message']['content'])

    return response['message']['content'] if not is_thinking else extract_non_thinking_response(
        response['message']['content'])


def check_is_thinking(message):
    if "<think>" in message.lower() or "</think>" in message.lower():
        return True
    return False


def extract_non_thinking_response(message):
    start = message.lower().find("<think>")
    end = message.lower().find("</think>")

    if start != -1 and end != -1:
        return message[:start] + message[end + len("</think>"):]
    return message
