from fastapi import FastAPI
from pydantic import BaseModel
from playwright.async_api import async_playwright

app = FastAPI()

class ScrapeRequest(BaseModel):
    url: str
    max_pages: int = 10  # optional but not used in this simple example

@app.post("/scrape")
async def scrape(req: ScrapeRequest):
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto(req.url)
            content = await page.content()
            await browser.close()
            return {"html": content}
    except Exception as e:
        return {"error": str(e)}
