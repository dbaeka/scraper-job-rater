import os
import sys

from db.init_db import init_db
from src.llm.ollama_backend import match_jobs
from src.orchestrator.job_scraper import search_jobs
from src.utils.helpers import extract_resume_text
from src.utils.helpers import get_config


def main():
    try:
        config = get_config()

        # Initialize database
        print("Initializing database...")
        init_db()

        # Search for jobs
        print("Searching for jobs...")
        jobs = search_jobs()

        if not jobs or len(jobs) == 0:
            print("No jobs found. Exiting.")
            return None

        print(f"Found {len(jobs)} jobs")

        # Extract resume text
        print("Extracting resume text...")
        resume_path = os.path.join(os.getcwd(), config["resume_path"])
        if not os.path.exists(resume_path):
            print(f"Resume not found at: {resume_path}")
            return None

        resume_text = extract_resume_text(resume_path)
        if not resume_text:
            print("Failed to extract resume text")
            return None

        # Match jobs against resume
        print("Matching jobs against resume...")
        matched_jobs = match_jobs(jobs, resume_text)

        print(f"Job matching complete. Found {len(matched_jobs) if matched_jobs else 0} matches.")

    except Exception as e:
        print(f"Error in main program: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
