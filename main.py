
from fastapi import FastAPI, Request
from playwright.async_api import async_playwright
import uvicorn

app = FastAPI()

@app.post("/scrape")
async def scrape(request: Request):
    data = await request.json()
    url = data.get("url")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(url)
        content = await page.content()
        await browser.close()
        return {"html": content}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000)
