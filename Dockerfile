FROM node:18-slim

RUN apt-get update && apt-get install -y wget gnupg && rm -rf /var/lib/apt/lists/*
RUN npx playwright install --with-deps

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .

EXPOSE 3000
CMD ["node", "playwright-scraper.js"]
