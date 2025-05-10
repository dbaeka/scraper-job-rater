import os
import sqlite3


class JobRepository:
    def __init__(self, db_path="db/job_matches.sqlite"):
        self.db_path = os.path.abspath(db_path)

    def _connect(self):
        return sqlite3.connect(self.db_path)

    def insert_job(self, job):
        conn = self._connect()
        c = conn.cursor()
        c.execute("""
                  INSERT
                  OR IGNORE INTO jobs 
            (
                job_id, job_title, company, location, url, pay, job_type, 
                shift_and_schedule, benefits, description, description_html, 
                match_score, match_reason, likelihood_score
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                  """, (
                      job.get('job_id'),
                      job.get('title_right_pane') or job.get('title_from_card_left_pane'),
                      job.get('company_name', 'Unknown'),
                      job.get('location', 'Unknown'),
                      job.get('job_url', 'Unknown'),
                      job.get('pay'),
                      job.get('job_type'),
                      job.get('shift_and_schedule'),
                      job.get('benefits'),
                      job.get('full_job_description_text'),
                      job.get('full_job_description_html'),
                      job.get('score', None),
                      job.get('reason', None),
                      job.get('likelihood_score', None)
                  ))
        conn.commit()
        conn.close()

    def job_exists(self, job_id):
        conn = self._connect()
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM jobs WHERE job_id = ?", (job_id,))
        count = c.fetchone()[0]
        conn.close()
        return count > 0

    def get_unscored_jobs(self, limit=50, offset=0):
        conn = self._connect()
        c = conn.cursor()
        c.execute("""
                  SELECT job_id, job_title, description, url
                  FROM jobs
                  WHERE match_score IS NULL
                     OR likelihood_score IS NULL LIMIT ?
                  OFFSET ?
                  """, (limit, offset))
        jobs = [dict(zip([col[0] for col in c.description], row)) for row in c.fetchall()]
        conn.close()
        return jobs

    def update_job_scores(self, job_id, match_score, likelihood_score, match_reason):
        conn = self._connect()
        c = conn.cursor()
        c.execute("""
                  UPDATE jobs
                  SET match_score      = ?,
                      likelihood_score = ?,
                      match_reason     = ?
                  WHERE job_id = ?
                  """, (match_score, likelihood_score, match_reason, job_id))
        conn.commit()
        conn.close()
