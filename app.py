from fastapi import FastAPI, Request, Form
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
import os
import sys
import asyncio

# --- Windows fix for asyncio subprocesses ---
if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# --- Import your scraper functions ---
from tournament_scraper import age_groups_level, scrape_tournament_data

# --- FastAPI app setup ---
app = FastAPI(title='Tournament Analyzer')
templates = Jinja2Templates(directory='templates')

# --- GET route for the homepage ---
@app.get('/', response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse('index.html', {'request': request})

# --- POST route for analyzing tournaments ---
@app.post('/analyze')
async def analyze(request: Request,
                  tournament_link: str = Form(...),
                  age_group: str = Form(...),
                  draw_size: int = Form(...),
                  sort: int = Form(...),
                  ):
    try:
        # Get tournament level options
        age_options = await age_groups_level(tournament_link)
        tournament_level = age_options[0] if age_options else ''
    except Exception:
        tournament_level = ''

    # Output folder
    out_dir = os.path.join(os.getcwd(), 'output')
    os.makedirs(out_dir, exist_ok=True)

    # Run your Playwright scraper (make sure headless=True inside scrape_tournament_data)
    pdf_path = await scrape_tournament_data(
        tournament_link, age_group, draw_size, sort, tournament_level, pdf_dir=out_dir
    )

    if not os.path.exists(pdf_path):
        return {'error': 'PDF generation failed. Check server logs.'}

    filename = os.path.basename(pdf_path)
    return FileResponse(pdf_path, media_type='application/pdf', filename=filename)

# --- Entry point for local testing or Render deployment ---
if __name__ == "__main__":
    import uvicorn

    # Use the PORT environment variable (Render provides it)
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port, reload=True)