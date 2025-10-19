# Tech Contributions Monitor

This project tracks and displays campaign finance contributions from executives and corporate PACs in the tech industry.

## Overview

The site presents two main views of campaign finance data sourced from the Federal Election Commission (FEC):

- **Executive Clusters:** Highlights instances where multiple executives from the same tech company contribute to the same political candidate or committee in a short period.
- **Corporate PACs:** Shows a summary of donations made by the political action committees of major tech companies.

## How it Works

The project uses a fully automated data pipeline powered by GitHub Actions:

1.  **Fetch Data:** A scheduled GitHub Action runs a Python script (`scripts/fetch_data.py`) to query the FEC API for the latest contributions and expenditures.
2.  **Process Data:** A second Python script (`scripts/format_data.py`) cleans, normalizes, and transforms the raw data. It detects executive clusters, filters PAC donations, and structures the data for the frontend.
3.  **Build Site:** The GitHub Action then builds a static SvelteKit site.
4.  **Deploy:** The generated static files are automatically deployed to GitHub Pages.

## Running Locally

1.  **Prerequisites:**
    - Node.js and npm
    - Python and pip
    - A `pyenv` environment is recommended.

2.  **Environment Setup:**
    - Create a `.env` file in the project root.
    - Add your FEC API key to the file:
      ```
      FEC_API_KEY=YOUR_API_KEY_HERE
      ```

3.  **Installation:**
    ```bash
    # Install frontend dependencies
    npm install

    # Install python dependencies
    pip install -r scripts/requirements.txt
    ```

4.  **Run the Development Server:**
    ```bash
    npm run dev
    ```
    The site will be available at `http://localhost:5173` (or another port if 5173 is in use).

5.  **Fetching Data Locally:**
    To update the data displayed on your local site, run the data pipeline scripts:
    ```bash
    python scripts/fetch_data.py
    python scripts/format_data.py
    ```
