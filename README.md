# USTA Tournament Analyzer

This is a Streamlit-based web app that scrapes and analyzes USTA tennis tournament data, then generates a styled PDF report.

## 🚀 Deployment on Render

1. Push this repo to GitHub.
2. Create a new Web Service on [Render](https://render.com/).
3. Use these settings:
   - **Build Command**: `./build.sh`
   - **Start Command**: `streamlit run TournamentPlayersV9.py --server.port $PORT --server.address 0.0.0.0`

## ✅ Local Setup

```bash
pip install -r requirements.txt
playwright install
streamlit run TournamentPlayersV9.py
```
