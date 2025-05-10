import time
from datetime import datetime

import gspread
from oauth2client.service_account import ServiceAccountCredentials

from src.db.repository import JobRepository
from src.utils.helpers import get_config

config = get_config()
google_sheet_config = config.get("google_sheet")
keys_path = google_sheet_config.get("credential_path")
sheet_name = google_sheet_config.get("sheet_name")
repo = JobRepository()


def sync_jobs_to_sheet():
    while True:
        try:
            print(f"Syncing jobs to Google Sheet '{sheet_name}'...")
            scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
            creds = ServiceAccountCredentials.from_json_keyfile_name(keys_path, scope)
            client = gspread.authorize(creds)

            sheet = client.open(sheet_name).sheet1
            headers, rows = repo.get_jobs_for_sheet()

            existing = sheet.get_all_records()

            if not existing:
                sheet.insert_row(headers, 1)

            job_index_map = {row['job_id']: (idx + 2, row.get('last_synced')) for idx, row in enumerate(existing)}

            for row in rows:
                job_id = str(row[0])
                row_data = list(map(str, row))

                date_updated_str = row_data[-1]  # Assume date_updated is last field in row
                date_updated = datetime.fromisoformat(date_updated_str)

                now_iso = datetime.now().isoformat()
                row_data[-2] = now_iso

                if job_id in job_index_map:
                    row_num, sheet_synced_str = job_index_map[job_id]

                    try:
                        if sheet_synced_str:
                            sheet_last_synced = datetime.fromisoformat(sheet_synced_str)
                        else:
                            sheet_last_synced = datetime.min  # treat as never synced
                    except ValueError:
                        sheet_last_synced = datetime.min

                    if date_updated > sheet_last_synced:
                        end_cell = gspread.utils.rowcol_to_a1(row_num, len(row_data))
                        sheet.update(f"A{row_num}:{end_cell}", [row_data])
                        repo.update_last_synced(job_id)
                else:
                    sheet.append_row(row_data)
                    repo.update_last_synced(job_id)

            print(f"Synced {len(rows)} job entries to Google Sheet '{sheet_name}'.")
            break
        except gspread.exceptions.SpreadsheetNotFound:
            print(f"Spreadsheet '{sheet_name}' not found. Please check the name and try again.")
            break
        except gspread.exceptions.APIError as e:
            print(f"API error occurred: {e}")
            if e.code == 429:
                print("Rate limit exceeded. Retrying in 1 minute...")
                time.sleep(65)
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            break
