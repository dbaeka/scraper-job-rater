import json

from ollama import Client

from src.db.repository import JobRepository
from src.utils.helpers import get_config

ollama_client = Client()
repo = JobRepository()
config = get_config()
model_config = config.get("ollama", {})
model_name = model_config.get("model", "llama3.1")


def generate(prompt):
    response = ollama_client.chat(
        model=model_name,
        messages=[{"role": "user", "content": prompt}],
        options={
            "temperature": model_config.get("temperature", 0.7),
        }
    )
    return response['message']['content']


def score_jobs(profile, resume_text, batch_size=50):
    offset = 0
    while True:
        jobs = repo.get_unscored_jobs(limit=batch_size, offset=offset)
        if not jobs:
            break

        for job in jobs:
            job_desc = job.get("description")
            if not job_desc:
                continue

            prompt = f"""
You are a job matching assistant.

Compare the following job description with the candidate's profile and resume. Evaluate two things:

1. match_score (out of 100): How well this job aligns with the candidate's skills and preferences.
2. likelihood_score (out of 100): How likely the candidate is to actually land this job based on their qualifications.
3. match_reason: A short explanation for why you gave the match score.
4. likelihood_reason: A short explanation for your likelihood score.

Respond in valid JSON format only, like this, don't give any other text beside the JSON:

{{
  "match_score": 85,
  "likelihood_score": 90,
  "match_reason": "reason",
  "likelihood_reason": "reason"
}}

---

Profile:
{profile}

Job Description:
{job_desc}

Resume:
{resume_text}
"""

            result = generate(prompt)

            try:
                parsed = json.loads(result)
                match_score = int(parsed["match_score"])
                likelihood_score = int(parsed["likelihood_score"])
                reason = f"""Match Reason: {parsed["match_reason"]}\n\nLikelihood Reason: {parsed["likelihood_reason"]}"""
            except Exception as e:
                print(f"Failed to parse result for job {job['job_id']}: {e}")
                continue

            repo.update_job_scores(
                job_id=job["job_id"],
                match_score=match_score,
                likelihood_score=likelihood_score,
                match_reason=reason
            )

            print(f"Scored job '{job['job_title']}' at {job['url']}")

        offset += batch_size
