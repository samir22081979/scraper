const express = require('express');
const { chromium } = require('playwright');
const app = express();

app.use(express.json());

app.post('/scrape', async (req, res) => {
  const { url } = req.body;

  if (!url) {
    return res.status(400).json({ error: 'Missing URL in request body' });
  }

  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  await page.goto(url, { waitUntil: 'domcontentloaded' });

  const data = await page.evaluate(() => {
    const structured = [];

    document.querySelectorAll('h1, h2, h3, p, table').forEach(el => {
      if (['H1', 'H2', 'H3', 'P'].includes(el.tagName)) {
        structured.push({ tag: el.tagName.toLowerCase(), content: el.innerText.trim() });
      } else if (el.tagName === 'TABLE') {
        const rows = [...el.querySelectorAll('tr')].map(row =>
          [...row.querySelectorAll('td, th')].map(cell => cell.innerText.trim())
        );
        structured.push({ tag: 'table', content: rows });
      }
    });

    return structured;
  });

  await browser.close();

  res.json({ url, data });
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => console.log(`Server running on port ${PORT}`));
