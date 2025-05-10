import argparse
import os
import sys

from src.db.init_db import init_db
from src.llm.rater import score_jobs
from src.orchestrator.job_scraper import search_jobs
from src.sheets.manager import sync_jobs_to_sheet
from src.utils.helpers import extract_resume_text
from src.utils.helpers import get_config


def run_init_db():
    print("Initializing database...")
    init_db()


def run_job_search():
    print("Searching for jobs...")
    search_jobs()
    print("Job search completed.")


def run_job_scoring():
    print("Running job scoring...")
    config = get_config()
    resume_path = os.path.join(os.getcwd(), config["resume_path"])
    profile = config["profile"]

    if not os.path.exists(resume_path):
        print(f"Resume not found at: {resume_path}")
        return

    resume_text = extract_resume_text(resume_path)
    if not resume_text:
        print("Failed to extract resume text.")
        return

    score_jobs(profile, resume_text)
    print("Job scoring completed.")


def run_sync_sheet():
    print("Syncing jobs to Google Sheet...")
    sync_jobs_to_sheet()
    print("Sync complete.")


def main():
    parser = argparse.ArgumentParser(description="Run a single task from the job pipeline.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--init-db", action="store_true", help="Initialize the database")
    group.add_argument("--search-jobs", action="store_true", help="Search for jobs")
    group.add_argument("--score-jobs", action="store_true", help="Score jobs with resume and profile")
    group.add_argument("--sync-sheet", action="store_true", help="Sync jobs table to Google Sheet")

    args = parser.parse_args()

    try:
        if args.init_db:
            run_init_db()
        elif args.search_jobs:
            run_job_search()
        elif args.score_jobs:
            run_job_scoring()
        elif args.sync_sheet:
            run_sync_sheet()
    except Exception as e:
        print(f"Error in task execution: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
