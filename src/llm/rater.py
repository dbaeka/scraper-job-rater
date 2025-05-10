import json

from src.db.repository import JobRepository
from src.llm.backends import ollama_chat
from src.utils.helpers import get_config

repo = JobRepository()
config = get_config()
backend = config.get("backend", "ollama")
max_retries = config.get("max_retries", 3)


def make_chat_completion(prompt):
    if backend == "ollama":
        return ollama_chat.generate(prompt)
    else:
        raise ValueError(f"Unsupported backend: {backend}")


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

            retries = 0
            parsed = None

            while retries < max_retries:
                try:
                    result = make_chat_completion(prompt)
                    parsed = json.loads(result)
                    break
                except Exception as e:
                    retries += 1
                    print(f"[Retry {retries}/3] Failed to parse response for job {job['job_id']}: {e}")

            if not parsed:
                print(f"Skipping job {job['job_id']} after 3 failed attempts.")
                continue

            try:
                match_score = int(parsed["match_score"])
                likelihood_score = int(parsed["likelihood_score"])
                reason = f"""Match Reason: {parsed["match_reason"]}\n\nLikelihood Reason: {parsed["likelihood_reason"]}"""
            except KeyError as e:
                print(f"Missing expected key {e} in parsed JSON. Skipping job {job['job_id']}.")
                continue

            repo.update_job_scores(
                job_id=job["job_id"],
                match_score=match_score,
                likelihood_score=likelihood_score,
                match_reason=reason
            )

            print(f"Scored job '{job['job_title']}' at {job['url']} with match_score: {match_score}, likelihood_score: {likelihood_score}")

        offset += batch_size
