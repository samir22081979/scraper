from fastapi import FastAPI, Request
from pydantic import BaseModel
import requests
from bs4 import BeautifulSoup
import re
import asyncio
from playwright.async_api import async_playwright

app = FastAPI()

class ScrapeRequest(BaseModel):
    domain: str
    max_pages: int

@app.post("/scrape")
async def scrape(req: ScrapeRequest):
    domain = req.domain
    max_pages = req.max_pages

    sitemap_url = f"https://{domain}/sitemap.xml"
    sitemap = requests.get(sitemap_url).text
    locs = re.findall(r"<loc>(https?://[^<]+)</loc>", sitemap)

    urls = locs[:max_pages]
    scraped_data = []

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        for url in urls:
            await page.goto(url, wait_until="domcontentloaded")
            html = await page.content()
            soup = BeautifulSoup(html, "html.parser")

            data = {
                "url": url,
                "title": soup.title.string if soup.title else "",
                "h1": [h.get_text(strip=True) for h in soup.find_all("h1")],
                "h2": [h.get_text(strip=True) for h in soup.find_all("h2")],
                "h3": [h.get_text(strip=True) for h in soup.find_all("h3")],
                "p": [p.get_text(strip=True) for p in soup.find_all("p")],
            }
            scraped_data.append(data)

        await browser.close()

    return {"results": scraped_data}
