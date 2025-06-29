from pymongo import MongoClient
from datetime import datetime, timedelta

client = MongoClient('mongodb+srv://jamsheed:jamsheed@news.zkfsvww.mongodb.net/news?retryWrites=true&w=majority&appName=news')
db = client['news']
today = datetime.utcnow().replace(hour=0,minute=0,second=0,microsecond=0)
for i in range(1, 11):
    day = today - timedelta(days=i)
    start = day
    end = day.replace(hour=23,minute=59,second=59,microsecond=999999)
    count = db.news.count_documents({'timestamp': {'$gte': start, '$lte': end}})
    print(f'{day.strftime('%Y-%m-%d')}: {count} news') 