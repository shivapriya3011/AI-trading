# AI Trading Mentor

## Run locally
1. Install Python 3.10+.
2. `pip install -r requirements.txt`
3. Optional: copy `.env.example` to `.env` and set `OPENAI_API_KEY`. Without a key, the app still runs basic trade/risk-reward checks.
4. `streamlit run app.py`

The app includes Trade Analysis, your entry-model options, screenshot upload, risk/reward checks, SQLite Trade Journal, and Dashboard. Do not commit `.env` or publish your API key. Public deployment requires hosting (e.g. Streamlit Community Cloud) and adding the secret there.
