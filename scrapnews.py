from bs4 import BeautifulSoup
import requests
import json
import os


header={
    'User-Agent':'Mozilla/5.0 (Windows; U; Windows NT 6.1; en-US) AppleWebKit/534.20 (KHTML, like Gecko) Chrome/11.0.672.2 Safari/534.20'
}

def load_cities():
    with open(os.path.join(os.path.dirname(__file__), 'cities.json')) as f:
        return json.load(f)

def match_city(text, cities):
    text_lower = text.lower()
    for city in cities:
        if city['name'].lower() in text_lower:
            return city
    return None

def get_news(url):
    document=requests.get(url,headers=header).text
    soup = BeautifulSoup(document,'html.parser')
    items= soup.find_all('item')
    data=[]
    i=0
    cities = load_cities()
    for item in items:
        headline=item.title.text
        detail=item.description.text
        link=item.guid.text
        city = match_city(headline + ' ' + detail, cities)
        list = [headline, detail, link, city]
        data.append(list)
        i=i+1
        if(i==6):
            break
    return data;