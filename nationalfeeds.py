from bs4 import BeautifulSoup
import requests


header={
    'User-Agent':'Mozilla/5.0 (Windows; U; Windows NT 6.1; en-US) AppleWebKit/534.20 (KHTML, like Gecko) Chrome/11.0.672.2 Safari/534.20'
}
def get_national(url):
    document=requests.get(url,headers=header).text
    soup = BeautifulSoup(document,'html.parser')
    items= soup.find_all('item')
    data=[]
    i=0
    for item in items:
        headline=item.title.text
        detail=item.description
        link=item.guid.text
        list = [headline, detail, link]
        data.append(list)
        i=i+1
        if(i==6):
            break
    return data;


