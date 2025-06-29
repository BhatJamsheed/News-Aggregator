import argparse
from datetime import datetime
import feedparser
from pymongo import MongoClient

# --- FEEDS DEFINITION (copy from main.py) ---
FEEDS = [
    # (url, category, continent)
    ('https://www.cnbc.com/id/100003114/device/rss/rss.html', 'stockmarket', 'North America'),
    ('https://www.ft.com/?format=rss', 'stockmarket', 'Europe'),
    ('https://www.japantimes.co.jp/news_category/business/feed/', 'stockmarket', 'Asia'),
    ('https://allafrica.com/tools/headlines/rdf/business/headlines.rdf', 'stockmarket', 'Africa'),
    ('https://www.buenosairesherald.com/rss', 'stockmarket', 'South America'),
    ('https://www.asx.com.au/rss-feeds', 'stockmarket', 'Australia'),
    ('https://cointelegraph.com/rss', 'crypto', 'North America'),
    ('https://news.bitcoin.com/feed/', 'crypto', 'North America'),
    ('https://cryptonews.com/news/feed', 'crypto', 'Europe'),
    ('https://cryptoslate.com/feed/', 'crypto', 'Asia'),
    ('https://bitcoinmagazine.com/.rss/full/', 'crypto', 'Africa'),
    ('https://criptonoticias.com/feed/', 'crypto', 'South America'),
    ('https://cryptonews.com.au/feed/', 'crypto', 'Australia'),
    ('https://www.politico.com/rss/politics08.xml', 'politics', 'North America'),
    ('https://feeds.bbci.co.uk/news/politics/rss.xml', 'politics', 'Europe'),
    ('https://www.aljazeera.com/xml/rss/all.xml', 'politics', 'Asia'),
    ('https://allafrica.com/tools/headlines/rdf/politics/headlines.rdf', 'politics', 'Africa'),
    ('https://www.buenosairesherald.com/rss', 'politics', 'South America'),
    ('https://www.abc.net.au/news/politics/feed/51120/rss.xml', 'politics', 'Australia'),
    ('https://www.aljazeera.com/xml/rss/all.xml', 'war', 'Asia'),
    ('https://www.reuters.com/rssFeed/worldNews', 'war', 'Europe'),
    ('https://www.defense.gov/Newsroom/News/Transcripts/Transcripts-RSS/', 'war', 'North America'),
    ('https://allafrica.com/tools/headlines/rdf/conflict/headlines.rdf', 'war', 'Africa'),
    ('https://www.batimes.com.ar/rss', 'war', 'South America'),
    ('https://www.sbs.com.au/news/topic/war/7e1b7b1e-6b7e-4e2e-8e2e-7e1b7b1e6b7e/feed', 'war', 'Australia'),
    # ... (add more feeds as needed)
]

# --- ARGUMENT PARSING ---
parser = argparse.ArgumentParser(description='Scrape news for a date range and all filters, and save to MongoDB.')
parser.add_argument('--start_date', required=True, help='Start date (YYYY-MM-DD)')
parser.add_argument('--end_date', required=True, help='End date (YYYY-MM-DD)')
args = parser.parse_args()

start_date = datetime.strptime(args.start_date, '%Y-%m-%d')
end_date = datetime.strptime(args.end_date, '%Y-%m-%d')

# --- MONGODB CONNECTION ---
client = MongoClient('mongodb+srv://jamsheed:jamsheed@news.zkfsvww.mongodb.net/news?retryWrites=true&w=majority&appName=news')
db = client['news']

# --- SCRAPING LOOP ---
summary = {}
for feed_url, category, continent in FEEDS:
    print(f'\nScraping {feed_url} for {category} in {continent}...')
    d = feedparser.parse(feed_url)
    available_dates = []
    matched = 0
    total = 0
    for entry in d.entries:
        pub_date = None
        if hasattr(entry, 'published_parsed') and entry.published_parsed:
            pub_date = datetime(*entry.published_parsed[:6])
        elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
            pub_date = datetime(*entry.updated_parsed[:6])
        else:
            pub_date = None
        if pub_date:
            available_dates.append(pub_date.strftime('%Y-%m-%d'))
        else:
            available_dates.append('NO_DATE')
        total += 1
        if not pub_date or pub_date < start_date or pub_date > end_date:
            continue
        title = entry.title
        summary_text = getattr(entry, 'summary', getattr(entry, 'description', ''))
        link = entry.link
        news_doc = {
            'title': title,
            'summary': summary_text,
            'link': link,
            'source': feed_url,
            'timestamp': pub_date,
            'category': category,
            'continent': continent
        }
        db.news.update_one({'title': title, 'link': link}, {'$set': news_doc}, upsert=True)
        matched += 1
    print(f'  Total articles in feed: {total}')
    print(f'  Dates found: {set(available_dates)}')
    print(f'  Articles matching range: {matched}')
    summary[(category, continent)] = matched

print('\n=== SUMMARY ===')
for (cat, cont), count in summary.items():
    print(f'{cat} | {cont}: {count} articles saved in range {args.start_date} to {args.end_date}') 