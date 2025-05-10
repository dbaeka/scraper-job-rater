import json
import time
from multiprocessing import Pool, cpu_count

from src.db.repository import JobRepository
from src.llm.backends import ollama_chat, openrouter_chat, gemini_chat
from src.utils.helpers import get_config

repo = JobRepository()
config = get_config()
backend = config.get("backend", "ollama")
max_retries = config.get("max_retries", 3)


def make_chat_completion(prompt):
    if backend == "ollama":
        return ollama_chat.generate(prompt)
    elif backend == "openrouter":
        return openrouter_chat.generate(prompt)
    elif backend == "gemini":
        return gemini_chat.generate(prompt)
    else:
        raise ValueError(f"Unsupported backend: {backend}")


def process_job(args):
    job, profile, resume_text = args
    job_desc = job.get("description")
    if not job_desc:
        return None

    prompt = f"""
You are a job matching assistant.

Compare the following job description with the candidate's profile and resume. Evaluate two things:

1. match_score (out of 100): How well this job aligns with the candidate's skills and preferences.
2. likelihood_score (out of 100): How likely the candidate is to actually land this job based on their qualifications.
3. match_reason: A short explanation for why you gave the match score.
4. likelihood_reason: A short explanation for your likelihood score.

Be very objective in your evaluation. If the job is not a good fit, give low scores and explain why.

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
            if not result:
                print(f"Empty response for job {job['job_id']}")
                time.sleep(5)
            parsed = json.loads(result)
            break
        except Exception as e:
            retries += 1
            print(f"[Retry {retries}/3] Failed to parse job {job['job_id']}: {e}")
            if result:
                print(f"Response: {result}")

    if not parsed:
        return None

    try:
        return {
            "job_id": job["job_id"],
            "match_score": int(parsed["match_score"]),
            "likelihood_score": int(parsed["likelihood_score"]),
            "reason": f"""Match Reason: {parsed["match_reason"]}\n\nLikelihood Reason: {parsed["likelihood_reason"]}"""
        }
    except KeyError as e:
        print(f"Missing expected key {e} for job {job['job_id']}")
        print(f"Response: {parsed}")
        return None


def score_jobs(profile, resume_text, batch_size=5):
    num_workers = min(cpu_count() - 1, batch_size)
    print(f"Using {num_workers} workers for job scoring.")

    while True:
        jobs = repo.get_unscored_jobs(limit=batch_size)
        if not jobs:
            break

        with Pool(processes=num_workers) as pool:
            job_args = [(job, profile, resume_text) for job in jobs]
            results = pool.map(process_job, job_args)

        for res in results:
            if not res:
                continue
            repo.update_job_scores(
                job_id=res["job_id"],
                match_score=res["match_score"],
                likelihood_score=res["likelihood_score"],
                match_reason=res["reason"]
            )
            print(
                f"Scored job {res['job_id']} — match_score: {res['match_score']}, likelihood_score: {res['likelihood_score']}")
