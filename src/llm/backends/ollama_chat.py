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
    return response['message']['content']
