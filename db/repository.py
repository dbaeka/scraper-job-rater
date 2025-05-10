import sqlite3


class JobRepository:
    def __init__(self, db_path="db/job_matches.sqlite"):
        self.db_path = db_path

    def insert_job(self, job):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("""
                  INSERT
                  OR IGNORE INTO jobs 
            (
                job_id, job_title, company, location, url, pay, job_type, 
                shift_and_schedule, benefits, description, description_html, 
                match_score, match_reason
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                      job.get('reason', None)
                  ))
        conn.commit()
        conn.close()

    def job_exists(self, job_id):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM jobs WHERE job_id = ?", (job_id,))
        count = c.fetchone()[0]
        conn.close()
        return count > 0