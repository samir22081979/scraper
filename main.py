from fastapi import FastAPI, Request
from pydantic import BaseModel
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import uvicorn

app = FastAPI()

class ScrapeRequest(BaseModel):
    url: str
    max_pages: int = 10  # Optional for future pagination support

@app.post("/scrape")
async def scrape(request: ScrapeRequest):
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.goto(request.url, wait_until="domcontentloaded")
        content = await page.content()
        await browser.close()

        soup = BeautifulSoup(content, "html.parser")

        structured = []
        for tag in soup.find_all(["h1", "h2", "h3", "p", "table"]):
            if tag.name == "table":
                table_data = []
                for row in tag.find_all("tr"):
                    cells = [cell.get_text(strip=True) for cell in row.find_all(["td", "th"])]
                    if cells:
                        table_data.append(cells)
                if table_data:
                    structured.append({"type": "table", "content": table_data})
            else:
                text = tag.get_text(strip=True)
                if text:
                    structured.append({"type": tag.name, "content": text})

        return {
            "url": request.url,
            "structured_data": structured
        }

# Optional if running locally
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
