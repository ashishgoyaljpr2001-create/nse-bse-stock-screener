# NSE loss-making / positive CFO screener — V2

Streamlit Community Cloud app. Automatically retrieves the NSE equity symbol universe from NSE's published `EQUITY_L.csv`, then screens financial statements using free Yahoo Finance data.

## Deployment

Upload **app.py**, **requirements.txt**, and **README.md** to the root of your existing GitHub repository (replace older versions). Streamlit Cloud should redeploy automatically. Otherwise choose **Reboot app** from Streamlit's app management menu.

## Use

1. Click **Load all NSE equity symbols** (or upload a CSV containing `Symbol`).
2. Set the number of consecutive years, minimum CFO and batch size.
3. Click **Scan next batch** repeatedly. Results accumulate within the current browser session; download the CSV regularly. A session reset or app restart loses progress.
4. Export matches or full audit CSV.

## Limitations

- This is **not** a single unattended scan of the entire market. Batches reduce rate-limit and Streamlit session timeout risk.
- NSE's published list may be temporarily inaccessible from Streamlit Cloud; use a symbol CSV fallback.
- Yahoo Finance may omit annual statements, change field names, or report standalone rather than consolidated financials.
- The screener requires aligned year-end dates, and tests the latest available annual periods, not necessarily FY2023–FY2026.
- Free Yahoo Finance data frequently contains no more than four annual periods.
- A missing-data result is not a non-match; verify all candidates with audited exchange filings.
