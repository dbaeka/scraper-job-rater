# Job Hunter

A tool for automating job search, scoring, and tracking using web scraping, LLM-based scoring, and Google Sheets
integration.

## Overview

Job Hunter helps you streamline your job search process by:

- Scraping job listings from various sources such as Indeed
- Scoring jobs based on your profile and resume using LLM
- Organizing and tracking applications in Google Sheets

## Setup

### Prerequisites

- Python 3.11+
- Ollama with llama3.1 model (for job scoring)
- Google Service Account API credentials with Sheets API access

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/dbaeka/scraper-job-rater.git
   cd scraper-job-rater
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Install Playwright browsers:
   ```bash
   python -m playwright install
   ```

4. Set up Google API:
    - Place your Google API credentials JSON file at `keys/gcreds.json`
    - Ensure the Google account has access to Google Sheets API
    - Share the Google Sheet with the service account email
    - Create a Google Sheet with the name specified in `app.yaml`

## Configuration

Configure the application through the `app.yaml` file at the project root:

### Search Criteria

- `job_titles`: List of job titles to search for
- `locations`: List of locations with date_posted filters
- `salary_min`: Minimum salary requirement
- `job_types`: Types of jobs to search for (full_time, permanent, etc.)

### Resume Configuration

- `resume_path`: Directory containing resume PDF files

### Profile

- Personal profile description used for candidate-job scoring

### Google Sheet Configuration

- `sheet_name`: Name of the Google Sheet to sync jobs to
- `credential_path`: Path to Google API credentials JSON file

### LLM Backend Configuration

- `backend`: LLM backend to use (currently supports "ollama")
- `ollama`: Configuration for Ollama backend (model, temperature)

## Usage

The application is structured with four main components that can be run independently:

1. **Initialize Database**:
   ```bash
   python main.py --init-db
   ```

2. **Search for Jobs**:
   ```bash
   python main.py --search-jobs
   ```

3. **Score Jobs**:
   ```bash
   python main.py --score-jobs
   ```

4. **Sync to Google Sheets**:
   ```bash
   python main.py --sync-sheet
   ```

## Testing

The project uses Python's built-in unittest framework:

```bash
# Run all tests
python -m unittest discover tests

# Run a specific test file
python -m unittest tests/test_file.py
```

## Project Structure

```
job-hunter/
├── db/                    # SQLite database directory
├── keys/                  # API keys and credentials
├── resumes/               # Resume PDF files
├── src/                   # Source code
│   ├── db/                # Database operations
│   ├── llm/               # LLM integration for job scoring
│   ├── orchestrator/      # Job scraping orchestration
│   ├── sheets/            # Google Sheets integration
│   └── utils/             # Utility functions
├── tests/                 # Test files
├── app.yaml               # Application configuration
├── main.py                # Application entry point
└── requirements.txt       # Python dependencies
```