from pymongo import MongoClient
from dateutil import parser
from bson.objectid import ObjectId

client = MongoClient('mongodb+srv://jamsheed:jamsheed@news.zkfsvww.mongodb.net/news?retryWrites=true&w=majority&appName=news')
db = client['news']
news = db.news.find()
count = 0
for n in news:
    ts = n.get('timestamp')
    if isinstance(ts, str):
        try:
            dt = parser.parse(ts)
            db.news.update_one({'_id': n['_id']}, {'$set': {'timestamp': dt}})
            count += 1
        except Exception as e:
            print(f"Error parsing timestamp for _id {n['_id']}: {ts}")
print('Fixed', count, 'documents.') 