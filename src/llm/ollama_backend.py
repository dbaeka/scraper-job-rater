from ollama import Client

from db.repository import JobRepository
from src.utils.helpers import get_config

ollama_client = Client()
repo = JobRepository()
config = get_config()
model_config = config.get("ollama", {})
model_name = model_config.get("model", "llama3")


def ollama_prompt(job_desc, resume_text):
    prompt = f"""
Compare the following job description with the resume. Rate match from 1 (poor) to 5 (excellent). Provide a short reason.

Job:
{job_desc}

Resume:
{resume_text}
"""
    response = ollama_client.chat(
        model=model_name,
        messages=[{"role": "user", "content": prompt}],
        options={
            "temperature": model_config.get("temperature", 0.7),
            "top_p": model_config.get("top_p", 0.9),
            "frequency_penalty": model_config.get("frequency_penalty", 0.5),
            "presence_penalty": model_config.get("presence_penalty", 0.5),
            "stop": model_config.get("stop_sequences", []),
            "num_predict": model_config.get("max_tokens", 1500)
        }
    )
    return response['message']['content']


def match_jobs(jobs, resume_text):
    for job in jobs:
        job_desc = f"Sample description for {job['title']}"
        result = ollama_prompt(job_desc, resume_text)
        score, reason = 4, result  # You would extract score from result
        if score >= 4:
            job_record = {
                "title": job['title'],
                "url": job['url'],
                "description": job_desc,
                "score": score,
                "reason": reason
            }
            repo.insert_job(job_record)
