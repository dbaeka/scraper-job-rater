import os

from google import genai
from google.genai import types

from src.llm.model import RaterResponse
from src.utils.helpers import get_config

config = get_config()
model_config = config.get("gemini", {})
model_name = model_config.get("model", "gemma-3-27b-it")
temperature = model_config.get("temperature", 0.7)


def generate(prompt):
    client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
    response = client.models.generate_content(
        contents=prompt,
        model=model_name,
        config=types.GenerateContentConfig(
            temperature=temperature,
            # response_mime_type="application/json",
            response_schema=RaterResponse
        )
    )

    if not response.text:
        return None

    if "```json" in response.text:
        return response.text.split("```json")[1].split("```")[0].strip()
    return response.text
