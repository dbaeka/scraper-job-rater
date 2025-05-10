import os

from openai import OpenAI

from src.utils.helpers import get_config

config = get_config()
model_config = config.get("openrouter", {})
model_name = model_config.get("model", "meta-llama/llama-4-scout:free")
temperature = model_config.get("temperature", 0.7)


def generate(prompt):
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=os.getenv("OPENROUTER_API_KEY"),
    )
    response = client.chat.completions.create(
        messages=[
            {
                "role": "user",
                "content": prompt,
            }
        ],
        model=model_name,
        temperature=temperature,
    )

    if not response.choices:
        return None

    return response.choices[0].message.content
