# Free Loss + Positive CFO Stock Screener

Run:

```bash
pip install -r requirements.txt
streamlit run app.py
```

Enter NSE tickers with `.NS` or BSE tickers with `.BO`, or upload a CSV with a `Symbol` column. Click **Run free online screening**. The application retrieves annual income and cash flow statements via the unofficial yfinance Yahoo Finance client, checks negative PAT and positive CFO for each of the selected periods, and exports matches to Excel.

**Limitations:** Free data can be incomplete, rate-limited or inaccurate. Fiscal year-ends and consolidated vs standalone bases are not assured. The screener checks only supplied symbols; it does not automatically discover all listed companies. Confirm all matches against published exchange filings.
