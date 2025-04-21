from fastapi import FastAPI, Request
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import requests
import xml.etree.ElementTree as ET

app = FastAPI()

@app.post("/scrape")
async def scrape(request: Request):
    body = await request.json()
    domain = body["domain"]
    max_pages = int(body.get("max_pages", 10))

    # Step 1: Get sitemap URLs
    sitemap_url = f"https://{domain}/sitemap.xml"
    sitemap_xml = requests.get(sitemap_url).text
    urls = []
    try:
        root = ET.fromstring(sitemap_xml)
        urls = [loc.text for loc in root.iter("{http://www.sitemaps.org/schemas/sitemap/0.9}loc")]
    except:
        urls = [sitemap_url]

    # Step 2: Scrape each URL
    results = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        for url in urls[:max_pages]:
            try:
                await page.goto(url, wait_until="domcontentloaded")
                html = await page.content()
                soup = BeautifulSoup(html, "html.parser")
                results.append({
                    "url": url,
                    "title": soup.title.string if soup.title else None,
                    "h1": [h.get_text(strip=True) for h in soup.find_all("h1")],
                    "h2": [h.get_text(strip=True) for h in soup.find_all("h2")],
                    "h3": [h.get_text(strip=True) for h in soup.find_all("h3")],
                    "p": [p.get_text(strip=True) for p in soup.find_all("p")],
                })
            except Exception as e:
                results.append({ "url": url, "error": str(e) })
        await browser.close()

    return { "results": results }
