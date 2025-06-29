import sqlite3
from datetime import datetime
import scrapnews

conn=sqlite3.connect('mydb')
cursor=conn.cursor()
#cursor.execute('delete from papers')
#conn.commit()
# cursor.execute("""
# create table users
# (
# username text primary key,
# password text not null
# );
# """)

# cursor.execute("insert into users values('admin','12345')")
# conn.commit()
# cursor.execute("select * from users ")
# rows=cursor.fetchall()
# print (rows)
#""")
def get_users():
    conn = sqlite3.connect('mydb')
    cursor = conn.cursor()

    cursor.execute("select * from users")
    rows=cursor.fetchall()
    return rows

def get_updatepassword(uname,password):
    conn = sqlite3.connect('mydb')
    cursor = conn.cursor()

    try:
        data=get_users()
        dbuname=data[0][0]
        if uname==dbuname:
            cursor.execute("update users set password='"+password+"'where username='"+uname+"'")
            conn.commit()
            return True
        else:
            return False
    except:
        return False
# conn = sqlite3.connect('mydb')
# cursor = conn.cursor()
# cursor.execute("delete from categories")
# conn.commit()

# cursor.execute("""
# create table papers
# (
# paper_id integer primary key autoincrement,
# paper_name text unique,
# paper_type text not null
# );
#
# """)
# print("table created successfully")
#cursor.execute(("insert into papers(paper_name,paper_type) values('Greater Kashmir', 'Local')"))
#conn.commit()

# cursor.execute("""
# create table categories
# (
# category_id integer primary key autoincrement,
# category_name text not null,
# category_link text not null,
# paper_id integer,
# foreign key(paper_id) references papers(paper_id)
# );
# """)

#cursor.execute("insert into categories(category_name,category_link,paper_id)values('top stories','https://www.greaterkashmir.com/feed/',3)")
#conn.commit()

def get_papers():
    conn = sqlite3.connect('mydb')
    cursor = conn.cursor()
    cursor.execute("select * from papers")
    rows=cursor.fetchall()
    for row in rows:
        print(row)
    return rows

def get_categories():
    conn = sqlite3.connect('mydb')
    cursor = conn.cursor()
    cursor.execute("select * from categories")
    rows=cursor.fetchall()
    return rows






def add_paper(paper_name,paper_type):
    conn = sqlite3.connect('mydb')
    cursor = conn.cursor()
    try:

        cursor.execute("insert into papers(paper_name,paper_type) values(?,?)", (paper_name, paper_type))
        conn.commit()
        return True
    except:
        return False

def add_category(category_name,category_link,paper_id):
    conn = sqlite3.connect('mydb')
    cursor = conn.cursor()
    try:
        cursor.execute("insert into categories(category_name,category_link,paper_id) values(?,?,?)",
                       (category_name, category_link, paper_id))

        conn.commit()


        return True
    except:
        return False





def get_link(category_id):
    conn = sqlite3.connect('mydb')
    cursor = conn.cursor()
    try:
        cursor.execute("select category_link from categories where category_id="+str(category_id))
        link=cursor.fetchone()[0]
        return link
    except:
        return False
def get_searched_papers(paper_type):
    conn = sqlite3.connect('mydb')
    cursor = conn.cursor()
    try:
        cursor.execute("select * from papers where paper_type='"+paper_type+"'")
        rows=cursor.fetchall()
        papers=[]
        for row in rows:
            dict={
                'id':row[0],
                'name':row[1]

            }
            papers.append(dict)
        return papers
    except:
        return False
#print(get_searched_papers('Local'))

def get_searched_categories(paper_id):
    conn = sqlite3.connect('mydb')
    cursor = conn.cursor()
    try:
        cursor.execute("select * from categories where paper_id=" +str (paper_id))
        rows = cursor.fetchall()
        categories = []
        for row in rows:
            dict = {
                'id': row[0],
                'name': row[1]

            }
            categories.append(dict)
        return categories
    except:
        return False
#print(get_searched_categories(1))

# cursor.execute("""
# create table news
# (
# id integer primary key autoincrement,
# source text,
# title text,
# description text,
# link text,
# timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
# );
# """)

News_Sources={
    'nyt':'https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml',
    'wtt':'https://www.washingtontimes.com/rss/headlines/news/world',
     'cnn':'http://rss.cnn.com/rss/money_topstories.rss',
    'toi':'https://timesofindia.indiatimes.com/rssfeedstopstories.cms',
    'n18':'https://www.news18.com/commonfeeds/v1/eng/rss/india.xml',
    'ht':'https://www.hindustantimes.com/feeds/rss/india-news/rssfeed.xml',
    'gk':'https://www.greaterkashmir.com/feed/',
    'glk':'https://globalkashmir.net/feed/',
    'krd':'https://kashmirreader.com/feed/'
}


def update_news():
    conn = sqlite3.connect('mydb')
    cursor = conn.cursor()
    cursor.execute('delete from news')
    conn.commit()
    print("updating......")
    for src,link in News_Sources.items():
        #print('updating' + src)
        try:
            rows=scrapnews.get_news(link)

            for row in rows:
             cursor.execute("insert into news(source,title,description,link,timestamp) values(?,?,?,?,?)",(src,row[0],row[1],row[2],datetime.now()))
            conn.commit()
        except:
           return False
#print(update_news())

def get_news(src):
    conn = sqlite3.connect('mydb')
    cursor = conn.cursor()
    cursor.execute("select title,description,link from news where source='"+src+"'")
    rows=cursor.fetchall()
    return rows
    #for row in rows:
        #print(row)


#get_news("ht")








