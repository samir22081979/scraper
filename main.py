import re
import json
import asyncio
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from playwright.async_api import async_playwright
from collections import Counter
import requests
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

app = FastAPI()

# ──────────────
# 🔧 CONFIG
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}
CONCURRENCY_LIMIT = 3
semaphore = asyncio.Semaphore(CONCURRENCY_LIMIT)

# ──────────────
# 📦 Request Model
class ScrapeRequest(BaseModel):
    domain: str
    max_pages: int = 50


# ──────────────
# 📌 Sitemap Discovery
def find_sitemaps(domain):
    robots_url = f"https://{domain}/robots.txt"
    try:
        txt = requests.get(robots_url, headers=HEADERS, timeout=5).text
        hits = re.findall(r"(?im)^sitemap:\s*(https?://\S+)", txt)
        if hits:
            return hits
    except Exception:
        pass
    return [f"https://{domain}/sitemap.xml"]


def fetch_sitemap_locs(smap_url):
    try:
        r = requests.get(smap_url, headers=HEADERS, timeout=10)
        r.raise_for_status()
        root = ET.fromstring(r.content)
        ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}

        if root.tag.endswith("sitemapindex"):
            out = []
            for sm in root.findall("sm:sitemap", ns):
                loc = sm.find("sm:loc", ns).text
                out += fetch_sitemap_locs(loc)
            return out
        return [u.text for u in root.findall("sm:url/sm:loc", ns)]
    except Exception as e:
        print(f"⚠️ Error parsing sitemap: {e}")
        return []


# ──────────────
# 🧠 Playwright Scraper (Concurrent-safe)
async def fetch_with_playwright(url):
    async with semaphore:
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                await page.goto(url, wait_until="domcontentloaded", timeout=15000)
                content = await page.content()
                await browser.close()

                soup = BeautifulSoup(content, "lxml")
                return {
                    "url": url,
                    "title": soup.title.string.strip() if soup.title else "",
                    "h1": [h.get_text(strip=True) for h in soup.find_all("h1")],
                    "h2": [h.get_text(strip=True) for h in soup.find_all("h2")],
                    "h3": [h.get_text(strip=True) for h in soup.find_all("h3")],
                    "paragraphs": [p.get_text(strip=True) for p in soup.find_all("p")]
                }
        except Exception as e:
            print(f"❌ Failed to fetch {url}: {e}")
            return {"url": url, "error": str(e)}


# ──────────────
# 🧼 Clean Scraped Data
def clean_scraped_data(results):
    all_paragraphs = [p for page in results for p in page.get("paragraphs", [])]
    freq = Counter(all_paragraphs)

    cleaned = []
    for page in results:
        cleaned.append({
            "url": page.get("url"),
            "title": page.get("title", ""),
            "h1": list(set(page.get("h1", []))),
            "h2": list(set(page.get("h2", []))),
            "h3": list(set(page.get("h3", []))),
            "paragraphs": [p for p in page.get("paragraphs", []) if freq[p] <= 3]
        })
    return cleaned


# ──────────────
# 🚀 Endpoint
@app.post("/scrape")
async def scrape(request: ScrapeRequest):
    domain = request.domain.replace("https://", "").replace("http://", "").strip("/")
    max_pages = request.max_pages

    sitemaps = find_sitemaps(domain)
    urls = []
    for smap in sitemaps:
        urls += fetch_sitemap_locs(smap)

    unique_urls = list(set(urls))[:max_pages]

    tasks = [fetch_with_playwright(url) for url in unique_urls]
    raw_results = await asyncio.gather(*tasks)

    cleaned_results = clean_scraped_data(raw_results)
    return JSONResponse(content={"results": cleaned_results})
