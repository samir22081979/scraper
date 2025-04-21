from fastapi import FastAPI, Request
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET
from collections import Counter
import requests
import re

app = FastAPI()

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

# ─────────────────────────────
# Sitemap Discovery

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
    except Exception:
        return []

# ─────────────────────────────
# Scrape Page

async def fetch_with_playwright(url):
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
                "p": [p.get_text(strip=True) for p in soup.find_all("p")],
            }
    except Exception as e:
        return {"url": url, "error": str(e)}

# ─────────────────────────────
# API Endpoint

@app.post("/scrape")
async def scrape(request: Request):
    body = await request.json()
    domain = body.get("domain")
    max_pages = int(body.get("max_pages", 100))

    sitemaps = find_sitemaps(domain)
    all_urls = []
    for sm in sitemaps:
        urls = fetch_sitemap_locs(sm)
        all_urls += urls
    all_urls = list(set(all_urls))[:max_pages]

    results = []
    for url in all_urls:
        data = await fetch_with_playwright(url)
        results.append(data)

    # Clean repeated paragraphs (optional)
    paragraphs = [p for page in results for p in page.get("p", [])]
    freq = Counter(paragraphs)

    cleaned_results = []
    for page in results:
        unique_p = [p for p in page.get("p", []) if freq[p] <= 3]
        cleaned_results.append({
            "url": page["url"],
            "title": page.get("title"),
            "h1": list(set(page.get("h1", []))),
            "h2": list(set(page.get("h2", []))),
            "h3": list(set(page.get("h3", []))),
            "p": unique_p
        })

    return {"results": cleaned_results}
