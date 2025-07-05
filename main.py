from flask import Flask,render_template,request,url_for,flash,redirect,get_flashed_messages,jsonify,session,current_app, send_from_directory
from unicodedata import category
import localfeeds
import database
import forms
import nationalfeeds
import worldheadlines
from database import update_news
from forms import updatepassword, addpapers, addcategories
from flask_pymongo import PyMongo
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import date, datetime, timedelta
from calendar import monthrange
import feedparser
from pywebpush import webpush, WebPushException
import json
import math
import os
import requests
from bs4 import BeautifulSoup

from apscheduler.schedulers.background import BackgroundScheduler
update_news()
schedular=BackgroundScheduler()
schedular.add_job(func=update_news,trigger='interval',minutes=1)
schedular.start()


app=Flask(__name__)
app.secret_key='123abc'
app.config['MONGO_URI'] = 'mongodb+srv://jamsheed:jamsheed@news.zkfsvww.mongodb.net/news?retryWrites=true&w=majority&appName=news'
mongo = PyMongo(app)

# VAPID keys (replace with your real keys!)
PUBLIC_VAPID_KEY = "REPLACE_WITH_YOUR_PUBLIC_KEY"
PRIVATE_VAPID_KEY = "REPLACE_WITH_YOUR_PRIVATE_KEY_PEM"

def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('user') and not session.get('admin'):
            return redirect(url_for('opening'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def root():
    if session.get('user') or session.get('admin'):
        return redirect(url_for('home'))
    return redirect(url_for('opening'))

@app.route('/home')
@login_required
def home():
    # Try to get top news from MongoDB
    news_cursor = mongo.db.news.find().sort('timestamp', -1).limit(8)
    trending_news = list(news_cursor)
    if not trending_news:
        # If DB is empty, fetch and store
        fetch_and_store_top_news()
        trending_news = list(mongo.db.news.find().sort('timestamp', -1).limit(8))

    # Fetch financial news (first page)
    financial_feeds = [
        'https://www.cnbc.com/id/10000664/device/rss/rss.html',
        'https://www.reuters.com/finance/markets/rss',
        'https://www.ft.com/?format=rss',
        'https://www.bloomberg.com/feed/podcast/etf-report.xml'
    ]
    financial_news = fetch_news(financial_feeds, page=1, page_size=8)

    # Fetch political news (first page)
    political_feeds = [
        'https://www.politico.com/rss/politics08.xml',
        'https://feeds.bbci.co.uk/news/politics/rss.xml',
        'https://www.aljazeera.com/xml/rss/all.xml',
        'https://rss.nytimes.com/services/xml/rss/nyt/Politics.xml'
    ]
    political_news = fetch_news(political_feeds, page=1, page_size=8)

    return render_template('home.html', trending_news=trending_news, financial_news=financial_news, political_news=political_news)

@app.route('/index')
@login_required
def index():
     post1 = worldheadlines.get_world('https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml')
     post2 = worldheadlines.get_world('https://www.washingtontimes.com/rss/headlines/news/world')
     post3 = worldheadlines.get_world('http://rss.cnn.com/rss/money_topstories.rss')
     return render_template('index.html', title="index page", post1=post1, post2=post2, post3=post3)

@app.route('/national')
@login_required
def national():
     # post1 = nationalfeeds.get_national('https://timesofindia.indiatimes.com/rssfeedstopstories.cms')
     # post2 = nationalfeeds.get_national('https://www.news18.com/commonfeeds/v1/eng/rss/india.xml')
     # post3 = nationalfeeds.get_national('https://www.hindustantimes.com/feeds/rss/india-news/rssfeed.xml')
     post1 = database.get_news('toi')
     post2 = database.get_news('n18')
     post3 = database.get_news('ht')
     return render_template('national.html', title="national page", post1=post1, post2=post2, post3=post3)

@app.route('/local')
@login_required
def local():
     # post1 = localfeeds.get_local('https://www.greaterkashmir.com/feed/')
     # post2 = localfeeds.get_local('https://globalkashmir.net/feed/')
     # post3 = localfeeds.get_local('https://kashmirreader.com/feed/')
     post1 = database.get_news('gk')
     post2 = database.get_news('glk')
     post3 = database.get_news('krd')
     return render_template('local.html', title="local page", post1=post1, post2=post2, post3=post3)



@app.route('/about')
@login_required
def about():
     return render_template('about.html',title="about")

@app.route('/login', methods=['GET'])
def login():
     form=forms.login()
     return render_template('login.html', title="login", form=form)

def is_admin(email):
    user = mongo.db.users.find_one({'email': email})
    return user and user.get('role') == 'admin'

@app.route('/userlogin', methods=['GET', 'POST'])
def userlogin():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = mongo.db.users.find_one({'email': email})
        if user and check_password_hash(user['password'], password):
            session.clear()
            session['user'] = email
            if is_admin(email):
                session['admin'] = email
                return redirect(url_for('admin_dashboard'))
            return redirect(url_for('home'))
        else:
            flash('Invalid email or password', 'danger')
    return render_template('userlogin.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        if not name or not email or not password or not confirm_password:
            flash('All fields are required', 'danger')
        elif password != confirm_password:
            flash('Passwords do not match', 'danger')
        elif mongo.db.users.find_one({'email': email}):
            flash('Email already registered', 'danger')
        else:
            hashed_pw = generate_password_hash(password)
            mongo.db.users.insert_one({'name': name, 'email': email, 'password': hashed_pw, 'role': 'user'})
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('userlogin'))
    return render_template('signup.html')

@app.route('/admin', methods=['POST'])
def admin():
    uname = request.form.get('username')
    password = request.form.get('password')
    user = mongo.db.users.find_one({'email': uname, 'role': 'admin'})
    if user and check_password_hash(user['password'], password):
        session.clear()
        session['admin'] = uname
        updatepassword_form = forms.updatepassword()
        papers = database.get_papers()
        categories = database.get_categories()
        addpapers = forms.addpapers()
        addcategories = forms.addcategories()
        return render_template('admin.html', title="admin page", updatepassword_form=updatepassword_form,
                              papers=papers, categories=categories, addpaper=addpapers, addcategories=addcategories)
    else:
        flash('Invalid Username or Password!', 'danger')
        return redirect('login')

@app.route('/admin_dashboard')
@login_required
def admin_dashboard():
    updatepassword_form = forms.updatepassword()
    papers = database.get_papers()
    categories = database.get_categories()
    addpapers = forms.addpapers()
    addcategories = forms.addcategories()
    return render_template('admin.html', title="admin page", updatepassword_form=updatepassword_form,
                          papers=papers, categories=categories, addpaper=addpapers, addcategories=addcategories)

@app.route('/updatepassword',methods=['POST'])
def updatepassword():
     uname = request.form.get('user_name')
     password = request.form.get('pass_word')
     cpassword = request.form.get('confirm_pass_word')
     updatepassword_form = forms.updatepassword()
     papers = database.get_papers()
     categories = database.get_categories()
     addpapers = forms.addpapers()
     addcategories = forms.addcategories()

     if password==cpassword:
          flag=database.get_updatepassword(uname,password)
          if flag:
             flash('Password Updated Sucessfully','updatepassword-success')
          else:
             flash('Username Does Not Exist','updatepassword-danger')
          return render_template('admin.html', title="admin page", updatepassword_form=updatepassword_form,
                                 papers=papers,
                                 categories=categories, addpaper=addpapers, addcategories=addcategories)
     else:
          flash('Password and Confirm Password are not same','updatepassword-danger')
     return render_template('admin.html', title="admin page", updatepassword_form=updatepassword_form, papers=papers,
                            categories=categories, addpaper=addpapers, addcategories=addcategories)


@app.route('/addpaper',methods=['POST'])
def add_paper():
     try:
          paper_type = request.form.get('paper_type')
          paper_name = request.form.get('paper_name')
          updatepassword_form = forms.updatepassword()
          categories = database.get_categories()
          addpapers = forms.addpapers()
          addcategories = forms.addcategories()
          flag = database.add_paper(paper_name, paper_type)
          papers = database.get_papers()

          if flag:
               flash('Paper Added Successfully', 'addpaper-success')
          else:
               flash('Error! Paper Not Added', 'addpaper-danger')
          return render_template('admin.html', title="admin page", updatepassword_form=updatepassword_form,
                                 papers=papers,
                                 categories=categories, addpaper=addpapers, addcategories=addcategories)
     except:
          return render_template('405.html',title='405')


@app.route('/addcategory',methods=['POST'])
def add_category():
     try:
          paper_id = request.form.get('paper_id')
          category_name = request.form.get('category_name')
          category_link = request.form.get('category_link')
          updatepassword_form = forms.updatepassword()
          addpapers = forms.addpapers()
          addcategories = forms.addcategories()
          flag = database.add_category(category_name, category_link, paper_id)
          papers = database.get_papers()
          categories = database.get_categories()
          if flag:
               flash('Category Added Successfully', 'addcategories-success')
          else:
               flash(' Error!Category Not Added', 'addcategories-danger')

          return render_template('admin.html', title="admin page", updatepassword_form=updatepassword_form,
                                 papers=papers,
                                 categories=categories, addpaper=addpapers, addcategories=addcategories)
     except:
          return render_template('errors/403.html',title='403')



@app.route('/customize', methods=['GET', 'POST'])
@login_required
def customize():
    user_email = session.get('user')
    user = mongo.db.users.find_one({'email': user_email})
    user_pref = user.get('preferences', {}) if user else {}
    posts = []
    fallback = False

    if request.method == 'POST':
        continent = request.form.get('continent')
        news_type = request.form.get('news_type')
        date_str = request.form.get('date')
        # Save preferences to user profile
        mongo.db.users.update_one({'email': user_email}, {'$set': {'preferences': {
            'continent': continent,
            'news_type': news_type,
            'date': date_str
        }}})
        user_pref = {'continent': continent, 'news_type': news_type, 'date': date_str}

    # Use preferences to filter news
    query = {}
    if user_pref.get('news_type'):
        query['category'] = user_pref['news_type']
    if user_pref.get('date'):
        try:
            day = datetime.strptime(user_pref['date'], '%Y-%m-%d')
            start = day.replace(hour=0, minute=0, second=0, microsecond=0)
            end = day.replace(hour=23, minute=59, second=59, microsecond=999999)
            query['timestamp'] = {'$gte': start, '$lte': end}
        except Exception:
            pass
    if user_pref.get('continent'):
        query['continent'] = user_pref['continent']

    news_cursor = mongo.db.news.find(query).sort('timestamp', -1).limit(8)
    posts = [[n.get('title'), n.get('summary'), n.get('link'), n.get('timestamp')] for n in news_cursor]

    # Fallback: If no news found, relax the query
    if not posts:
        fallback = True
        # Try without date
        query.pop('timestamp', None)
        news_cursor = mongo.db.news.find(query).sort('timestamp', -1).limit(8)
        posts = [[n.get('title'), n.get('summary'), n.get('link'), n.get('timestamp')] for n in news_cursor]
    if not posts:
        # Try without topic/category
        query.pop('category', None)
        news_cursor = mongo.db.news.find(query).sort('timestamp', -1).limit(8)
        posts = [[n.get('title'), n.get('summary'), n.get('link'), n.get('timestamp')] for n in news_cursor]
    if not posts:
        # Show most recent news as last resort
        news_cursor = mongo.db.news.find({}).sort('timestamp', -1).limit(8)
        posts = [[n.get('title'), n.get('summary'), n.get('link'), n.get('timestamp')] for n in news_cursor]

    return render_template('customize.html', title="Customized News", posts=posts, today=date.today(), user_pref=user_pref, fallback=fallback)




@app.route('/get_papers',methods=['GET','POST'])
def get_papers():
     try:
          if request.method == 'POST':
               zone = request.form['zone']
               papers = database.get_searched_papers(zone)

               return jsonify(papers)
     except:
          return render_template('errors/403.html',title='403')


@app.route('/get_categories',methods=['GET','POST'])
def get_categories():
     try:
          if request.method == 'POST':
               paper_id = request.form['paper_id']
               categories = database.get_searched_categories(paper_id)

               return jsonify(categories)
     except:
          return render_template('errors/403.html', title='403')

@app.errorhandler(403)
def error_403(error):
     return render_template('errors/403.html',title='403')


@app.errorhandler(404)
def error_404(error):
     return render_template('errors/404.html', title='404')


@app.errorhandler(405)
def error_405(error):
     return render_template('errors/405.html', title='405')


@app.errorhandler(500)
def error_500(error):
     return render_template('errors/403.html', title='500')

def fetch_news(feeds, page=1, page_size=8):
    news = []
    for feed in feeds:
        try:
            for item in worldheadlines.get_world(feed):
                news.append({
                    'title': item[0],
                    'summary': item[1],
                    'link': item[2]
                })
        except Exception:
            continue
    start = (page - 1) * page_size
    end = start + page_size
    return news[start:end]

@app.route('/api/news')
@login_required
def api_news():
    news_type = request.args.get('type', 'trending')
    page = int(request.args.get('page', 1))
    page_size = int(request.args.get('page_size', 8))
    feeds = []
    if news_type == 'trending':
        feeds = [
            'http://feeds.bbci.co.uk/news/rss.xml',
            'http://feeds.reuters.com/reuters/topNews',
            'https://www.aljazeera.com/xml/rss/all.xml',
            'https://feeds.foxnews.com/foxnews/latest',
            'https://www.cnbc.com/id/100003114/device/rss/rss.html'
        ]
    elif news_type == 'financial':
        feeds = [
            'https://www.cnbc.com/id/10000664/device/rss/rss.html',
            'https://www.reuters.com/finance/markets/rss',
            'https://www.ft.com/?format=rss',
            'https://www.bloomberg.com/feed/podcast/etf-report.xml'
        ]
    elif news_type == 'political':
        feeds = [
            'https://www.politico.com/rss/politics08.xml',
            'https://feeds.bbci.co.uk/news/politics/rss.xml',
            'https://www.aljazeera.com/xml/rss/all.xml',
            'https://rss.nytimes.com/services/xml/rss/nyt/Politics.xml'
        ]
    elif news_type == 'international':
        feeds = [
            'https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml',
            'https://www.washingtontimes.com/rss/headlines/news/world',
            'http://rss.cnn.com/rss/money_topstories.rss'
        ]
    elif news_type == 'national':
        feeds = [
            'https://timesofindia.indiatimes.com/rssfeedstopstories.cms',
            'https://www.news18.com/commonfeeds/v1/eng/rss/india.xml',
            'https://www.hindustantimes.com/feeds/rss/india-news/rssfeed.xml'
        ]
    elif news_type == 'local':
        feeds = [
            'https://www.greaterkashmir.com/feed/',
            'https://globalkashmir.net/feed/',
            'https://kashmirreader.com/feed/'
        ]
    else:
        return jsonify([])
    news = fetch_news(feeds, page, page_size)
    return jsonify(news)

@app.route('/opening')
def opening():
    return render_template('opening.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('opening'))

@app.route('/resetpassword', methods=['GET', 'POST'])
def resetpassword():
    return render_template('resetpassword.html')

def fetch_and_store_top_news():
    # News feeds mapped to (category, continent)
    feeds = [
        # --- STOCKMARKET ---
        ('https://www.cnbc.com/id/100003114/device/rss/rss.html', 'stockmarket', 'North America'),
        ('https://www.ft.com/?format=rss', 'stockmarket', 'Europe'),
        ('https://www.japantimes.co.jp/news_category/business/feed/', 'stockmarket', 'Asia'),
        ('https://allafrica.com/tools/headlines/rdf/business/headlines.rdf', 'stockmarket', 'Africa'),
        ('https://www.buenosairesherald.com/rss', 'stockmarket', 'South America'),
        ('https://www.asx.com.au/rss-feeds', 'stockmarket', 'Australia'),
        # --- CRYPTO ---
        ('https://cointelegraph.com/rss', 'crypto', 'North America'),
        ('https://news.bitcoin.com/feed/', 'crypto', 'North America'),
        ('https://cryptonews.com/news/feed', 'crypto', 'Europe'),
        ('https://cryptoslate.com/feed/', 'crypto', 'Asia'),
        ('https://bitcoinmagazine.com/.rss/full/', 'crypto', 'Africa'),
        ('https://criptonoticias.com/feed/', 'crypto', 'South America'),
        ('https://cryptonews.com.au/feed/', 'crypto', 'Australia'),
        # --- POLITICS ---
        ('https://www.politico.com/rss/politics08.xml', 'politics', 'North America'),
        ('https://feeds.bbci.co.uk/news/politics/rss.xml', 'politics', 'Europe'),
        ('https://www.aljazeera.com/xml/rss/all.xml', 'politics', 'Asia'),
        ('https://allafrica.com/tools/headlines/rdf/politics/headlines.rdf', 'politics', 'Africa'),
        ('https://www.buenosairesherald.com/rss', 'politics', 'South America'),
        ('https://www.abc.net.au/news/politics/feed/51120/rss.xml', 'politics', 'Australia'),
        # --- WAR ---
        ('https://www.aljazeera.com/xml/rss/all.xml', 'war', 'Asia'),
        ('https://www.reuters.com/rssFeed/worldNews', 'war', 'Europe'),
        ('https://www.defense.gov/Newsroom/News/Transcripts/Transcripts-RSS/', 'war', 'North America'),
        ('https://allafrica.com/tools/headlines/rdf/conflict/headlines.rdf', 'war', 'Africa'),
        ('https://www.batimes.com.ar/rss', 'war', 'South America'),
        ('https://www.sbs.com.au/news/topic/war/7e1b7b1e-6b7e-4e2e-8e2e-7e1b7b1e6b7e/feed', 'war', 'Australia'),
        # --- OIL PRICES ---
        ('https://www.oilprice.com/rss/main', 'oil_prices', 'North America'),
        ('https://www.energyvoice.com/feed/', 'oil_prices', 'Europe'),
        ('https://www.reuters.com/business/energy/rss', 'oil_prices', 'Asia'),
        ('https://allafrica.com/tools/headlines/rdf/oil/headlines.rdf', 'oil_prices', 'Africa'),
        ('https://www.batimes.com.ar/rss', 'oil_prices', 'South America'),
        ('https://www.energycouncil.com.au/news/feed/', 'oil_prices', 'Australia'),
        # --- TRADES ---
        ('https://www.bloomberg.com/feed/podcast/etf-report.xml', 'trades', 'North America'),
        ('https://www.ft.com/?format=rss', 'trades', 'Europe'),
        ('https://www.japantimes.co.jp/news_category/business/feed/', 'trades', 'Asia'),
        ('https://allafrica.com/tools/headlines/rdf/trade/headlines.rdf', 'trades', 'Africa'),
        ('https://www.batimes.com.ar/rss', 'trades', 'South America'),
        ('https://www.austrade.gov.au/news/news/rss', 'trades', 'Australia'),
        # --- DEFENCE DEALS ---
        ('https://www.defensenews.com/arc/outboundfeeds/rss/?outputType=xml', 'defence_deals', 'North America'),
        ('https://www.janes.com/defence-news/rss.xml', 'defence_deals', 'Europe'),
        ('https://www.armyrecognition.com/rss/news_asia.xml', 'defence_deals', 'Asia'),
        ('https://www.defenceweb.co.za/feed/', 'defence_deals', 'Africa'),
        ('https://www.infodefensa.com/latam/rss', 'defence_deals', 'South America'),
        ('https://www.australiandefence.com.au/rss', 'defence_deals', 'Australia'),
        # --- INTERNAL RELATIONS ---
        ('https://www.foreignaffairs.com/rss.xml', 'internal_relations', 'North America'),
        ('https://www.euronews.com/rss?level=theme&name=world', 'internal_relations', 'Europe'),
        ('https://www.scmp.com/rss/91/feed', 'internal_relations', 'Asia'),
        ('https://allafrica.com/tools/headlines/rdf/international_relations/headlines.rdf', 'internal_relations', 'Africa'),
        ('https://www.batimes.com.ar/rss', 'internal_relations', 'South America'),
        ('https://www.sbs.com.au/news/topic/international-relations/7e1b7b1e-6b7e-4e2e-8e2e-7e1b7b1e6b7e/feed', 'internal_relations', 'Australia'),
        # --- SOCIAL MEDIA NEWS ---
        ('https://mashable.com/feeds/social-media', 'social_media', 'North America'),
        ('https://www.euronews.com/rss?level=theme&name=technology', 'social_media', 'Europe'),
        ('https://www.scmp.com/rss/91/feed', 'social_media', 'Asia'),
        ('https://allafrica.com/tools/headlines/rdf/technology/headlines.rdf', 'social_media', 'Africa'),
        ('https://www.batimes.com.ar/rss', 'social_media', 'South America'),
        ('https://www.sbs.com.au/news/topic/social-media/7e1b7b1e-6b7e-4e2e-8e2e-7e1b7b1e6b7e/feed', 'social_media', 'Australia'),
        # --- AI RELATED NEWS ---
        ('https://www.technologyreview.com/feed/', 'ai', 'North America'),
        ('https://www.euronews.com/rss?level=theme&name=technology', 'ai', 'Europe'),
        ('https://www.scmp.com/rss/91/feed', 'ai', 'Asia'),
        ('https://allafrica.com/tools/headlines/rdf/technology/headlines.rdf', 'ai', 'Africa'),
        ('https://www.batimes.com.ar/rss', 'ai', 'South America'),
        ('https://www.sbs.com.au/news/topic/artificial-intelligence/7e1b7b1e-6b7e-4e2e-8e2e-7e1b7b1e6b7e/feed', 'ai', 'Australia'),
        # --- COMPUTER SCIENCE NEWS ---
        ('https://cacm.acm.org/news/rss', 'computer_science', 'North America'),
        ('https://www.euronews.com/rss?level=theme&name=technology', 'computer_science', 'Europe'),
        ('https://www.scmp.com/rss/91/feed', 'computer_science', 'Asia'),
        ('https://allafrica.com/tools/headlines/rdf/technology/headlines.rdf', 'computer_science', 'Africa'),
        ('https://www.batimes.com.ar/rss', 'computer_science', 'South America'),
        ('https://www.sbs.com.au/news/topic/computer-science/7e1b7b1e-6b7e-4e2e-8e2e-7e1b7b1e6b7e/feed', 'computer_science', 'Australia'),
        # --- RESEARCH NEWS ---
        ('https://www.sciencedaily.com/rss/top/science.xml', 'research', 'North America'),
        ('https://www.eurekalert.org/rss/europe.xml', 'research', 'Europe'),
        ('https://www.nature.com/subjects/research/rss', 'research', 'Asia'),
        ('https://www.scidev.net/rss/news/africa/', 'research', 'Africa'),
        ('https://www.scidev.net/rss/news/latin-america/', 'research', 'South America'),
        ('https://www.scidev.net/rss/news/oceania/', 'research', 'Australia'),
        # --- TRENDING/GENERAL ---
        ('http://feeds.bbci.co.uk/news/rss.xml', 'trending', 'Europe'),
        ('http://feeds.reuters.com/reuters/topNews', 'trending', 'Europe'),
        ('https://feeds.foxnews.com/foxnews/latest', 'trending', 'North America'),
        ('https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml', 'trending', 'North America'),
        ('https://www.aljazeera.com/xml/rss/all.xml', 'trending', 'Asia'),
        ('https://www.news24.com/news24/rss', 'trending', 'Africa'),
        ('https://www.batimes.com.ar/rss', 'trending', 'South America'),
        ('https://www.abc.net.au/news/feed/51120/rss.xml', 'trending', 'Australia'),
        # --- INTERNATIONAL ---
        ('https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml', 'international', 'North America'),
        ('https://www.washingtontimes.com/rss/headlines/news/world', 'international', 'North America'),
        ('http://rss.cnn.com/rss/money_topstories.rss', 'international', 'North America'),
        ('https://www.bbc.com/news/world/rss.xml', 'international', 'Europe'),
        ('https://www.aljazeera.com/xml/rss/all.xml', 'international', 'Asia'),
        ('https://www.news24.com/news24/rss', 'international', 'Africa'),
        ('https://www.batimes.com.ar/rss', 'international', 'South America'),
        ('https://www.abc.net.au/news/feed/51120/rss.xml', 'international', 'Australia'),
    ]
    days_ago = datetime.utcnow() - timedelta(days=10)
    for feed, category, continent in feeds:
        try:
            d = feedparser.parse(feed)
            for entry in d.entries:
                # Try to get published date
                pub_date = None
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    pub_date = datetime(*entry.published_parsed[:6])
                elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                    pub_date = datetime(*entry.updated_parsed[:6])
                else:
                    pub_date = datetime.utcnow()
                if pub_date < days_ago:
                    continue
                title = entry.title
                summary = getattr(entry, 'summary', getattr(entry, 'description', ''))
                link = entry.link
                news_doc = {
                    'title': title,
                    'summary': summary,
                    'link': link,
                    'source': feed,
                    'timestamp': pub_date,
                    'category': category,
                    'continent': continent
                }
                mongo.db.news.update_one({'title': title, 'link': link}, {'$set': news_doc}, upsert=True)
        except Exception:
            continue

@app.route('/create_user', methods=['POST'])
def create_user():
    # For dev/admin use only! Remove or protect in production.
    data = request.json
    name = data.get('name')
    email = data.get('email')
    password = data.get('password')
    role = data.get('role', 'user')
    if not name or not email or not password:
        return {'error': 'Missing fields'}, 400
    if mongo.db.users.find_one({'email': email}):
        return {'error': 'User already exists'}, 400
    hashed_pw = generate_password_hash(password)
    mongo.db.users.insert_one({'name': name, 'email': email, 'password': hashed_pw, 'role': role})
    return {'success': True}

@app.route('/update_news_db')
def update_news_db():
    fetch_and_store_top_news()
    return {'success': True, 'message': 'Top news updated in MongoDB.'}

@app.route('/sample_news')
def sample_news():
    db = mongo.db
    if db is None:
        return jsonify({'error': 'MongoDB connection not initialized'}), 500
    news_cursor = db.news.find({}, {'title':1, 'category':1, 'continent':1, 'timestamp':1, '_id':0}).sort('timestamp', -1).limit(5)
    news_list = list(news_cursor)
    for n in news_list:
        if 'timestamp' in n:
            n['timestamp'] = n['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
    return jsonify(news_list)

@app.route('/test_mongo')
def test_mongo():
    return jsonify({
        'mongo': str(mongo),
        'mongo_db': str(getattr(mongo, 'db', None)),
        'MONGO_URI': app.config.get('MONGO_URI')
    })

@app.context_processor
def inject_session():
    return dict(session=session)

@app.route('/api/customized_news')
@login_required
def api_customized_news():
    user_email = session.get('user')
    user = mongo.db.users.find_one({'email': user_email})
    user_pref = user.get('preferences', {}) if user else {}
    page_size = int(request.args.get('page_size', 8))
    last_timestamp = request.args.get('last_timestamp')
    query = {}
    if user_pref.get('news_type'):
        query['category'] = user_pref['news_type']
    if user_pref.get('date'):
        try:
            day = datetime.strptime(user_pref['date'], '%Y-%m-%d')
            start = day.replace(hour=0, minute=0, second=0, microsecond=0)
            end = day.replace(hour=23, minute=59, second=59, microsecond=999999)
            query['timestamp'] = {'$gte': start, '$lte': end}
        except Exception:
            pass
    if user_pref.get('continent'):
        query['continent'] = user_pref['continent']
    if last_timestamp:
        try:
            last_dt = datetime.strptime(last_timestamp, '%Y-%m-%d %H:%M')
            # If timestamp filter already exists, combine with $lt
            if 'timestamp' in query:
                query['timestamp']['$lt'] = last_dt
            else:
                query['timestamp'] = {'$lt': last_dt}
        except Exception:
            pass
    news_cursor = mongo.db.news.find(query).sort('timestamp', -1).limit(page_size)
    posts = []
    for n in news_cursor:
        posts.append({
            'title': n.get('title'),
            'summary': n.get('summary'),
            'link': n.get('link'),
            'timestamp': n.get('timestamp').strftime('%Y-%m-%d %H:%M') if n.get('timestamp') else ''
        })
    return jsonify(posts)

@app.route('/scrape_monthly_news')
def scrape_monthly_news():
    # Get the first day of the current month
    now = datetime.utcnow()
    first_day = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    last_day = now.replace(day=monthrange(now.year, now.month)[1], hour=23, minute=59, second=59, microsecond=999999)
    feeds = [
        # --- STOCKMARKET ---
        ('https://www.cnbc.com/id/100003114/device/rss/rss.html', 'stockmarket', 'North America'),
        ('https://www.ft.com/?format=rss', 'stockmarket', 'Europe'),
        ('https://www.japantimes.co.jp/news_category/business/feed/', 'stockmarket', 'Asia'),
        ('https://allafrica.com/tools/headlines/rdf/business/headlines.rdf', 'stockmarket', 'Africa'),
        ('https://www.buenosairesherald.com/rss', 'stockmarket', 'South America'),
        ('https://www.asx.com.au/rss-feeds', 'stockmarket', 'Australia'),
        # --- CRYPTO ---
        ('https://cointelegraph.com/rss', 'crypto', 'North America'),
        ('https://news.bitcoin.com/feed/', 'crypto', 'North America'),
        ('https://cryptonews.com/news/feed', 'crypto', 'Europe'),
        ('https://cryptoslate.com/feed/', 'crypto', 'Asia'),
        ('https://bitcoinmagazine.com/.rss/full/', 'crypto', 'Africa'),
        ('https://criptonoticias.com/feed/', 'crypto', 'South America'),
        ('https://cryptonews.com.au/feed/', 'crypto', 'Australia'),
        # --- POLITICS ---
        ('https://www.politico.com/rss/politics08.xml', 'politics', 'North America'),
        ('https://feeds.bbci.co.uk/news/politics/rss.xml', 'politics', 'Europe'),
        ('https://www.aljazeera.com/xml/rss/all.xml', 'politics', 'Asia'),
        ('https://allafrica.com/tools/headlines/rdf/politics/headlines.rdf', 'politics', 'Africa'),
        ('https://www.buenosairesherald.com/rss', 'politics', 'South America'),
        ('https://www.abc.net.au/news/politics/feed/51120/rss.xml', 'politics', 'Australia'),
        # --- WAR ---
        ('https://www.aljazeera.com/xml/rss/all.xml', 'war', 'Asia'),
        ('https://www.reuters.com/rssFeed/worldNews', 'war', 'Europe'),
        ('https://www.defense.gov/Newsroom/News/Transcripts/Transcripts-RSS/', 'war', 'North America'),
        ('https://allafrica.com/tools/headlines/rdf/conflict/headlines.rdf', 'war', 'Africa'),
        ('https://www.batimes.com.ar/rss', 'war', 'South America'),
        ('https://www.sbs.com.au/news/topic/war/7e1b7b1e-6b7e-4e2e-8e2e-7e1b7b1e6b7e/feed', 'war', 'Australia'),
        # --- OIL PRICES ---
        ('https://www.oilprice.com/rss/main', 'oil_prices', 'North America'),
        ('https://www.energyvoice.com/feed/', 'oil_prices', 'Europe'),
        ('https://www.reuters.com/business/energy/rss', 'oil_prices', 'Asia'),
        ('https://allafrica.com/tools/headlines/rdf/oil/headlines.rdf', 'oil_prices', 'Africa'),
        ('https://www.batimes.com.ar/rss', 'oil_prices', 'South America'),
        ('https://www.energycouncil.com.au/news/feed/', 'oil_prices', 'Australia'),
        # --- TRADES ---
        ('https://www.bloomberg.com/feed/podcast/etf-report.xml', 'trades', 'North America'),
        ('https://www.ft.com/?format=rss', 'trades', 'Europe'),
        ('https://www.japantimes.co.jp/news_category/business/feed/', 'trades', 'Asia'),
        ('https://allafrica.com/tools/headlines/rdf/trade/headlines.rdf', 'trades', 'Africa'),
        ('https://www.batimes.com.ar/rss', 'trades', 'South America'),
        ('https://www.austrade.gov.au/news/news/rss', 'trades', 'Australia'),
        # --- DEFENCE DEALS ---
        ('https://www.defensenews.com/arc/outboundfeeds/rss/?outputType=xml', 'defence_deals', 'North America'),
        ('https://www.janes.com/defence-news/rss.xml', 'defence_deals', 'Europe'),
        ('https://www.armyrecognition.com/rss/news_asia.xml', 'defence_deals', 'Asia'),
        ('https://www.defenceweb.co.za/feed/', 'defence_deals', 'Africa'),
        ('https://www.infodefensa.com/latam/rss', 'defence_deals', 'South America'),
        ('https://www.australiandefence.com.au/rss', 'defence_deals', 'Australia'),
        # --- INTERNAL RELATIONS ---
        ('https://www.foreignaffairs.com/rss.xml', 'internal_relations', 'North America'),
        ('https://www.euronews.com/rss?level=theme&name=world', 'internal_relations', 'Europe'),
        ('https://www.scmp.com/rss/91/feed', 'internal_relations', 'Asia'),
        ('https://allafrica.com/tools/headlines/rdf/international_relations/headlines.rdf', 'internal_relations', 'Africa'),
        ('https://www.batimes.com.ar/rss', 'internal_relations', 'South America'),
        ('https://www.sbs.com.au/news/topic/international-relations/7e1b7b1e-6b7e-4e2e-8e2e-7e1b7b1e6b7e/feed', 'internal_relations', 'Australia'),
        # --- SOCIAL MEDIA NEWS ---
        ('https://mashable.com/feeds/social-media', 'social_media', 'North America'),
        ('https://www.euronews.com/rss?level=theme&name=technology', 'social_media', 'Europe'),
        ('https://www.scmp.com/rss/91/feed', 'social_media', 'Asia'),
        ('https://allafrica.com/tools/headlines/rdf/technology/headlines.rdf', 'social_media', 'Africa'),
        ('https://www.batimes.com.ar/rss', 'social_media', 'South America'),
        ('https://www.sbs.com.au/news/topic/social-media/7e1b7b1e-6b7e-4e2e-8e2e-7e1b7b1e6b7e/feed', 'social_media', 'Australia'),
        # --- AI RELATED NEWS ---
        ('https://www.technologyreview.com/feed/', 'ai', 'North America'),
        ('https://www.euronews.com/rss?level=theme&name=technology', 'ai', 'Europe'),
        ('https://www.scmp.com/rss/91/feed', 'ai', 'Asia'),
        ('https://allafrica.com/tools/headlines/rdf/technology/headlines.rdf', 'ai', 'Africa'),
        ('https://www.batimes.com.ar/rss', 'ai', 'South America'),
        ('https://www.sbs.com.au/news/topic/artificial-intelligence/7e1b7b1e-6b7e-4e2e-8e2e-7e1b7b1e6b7e/feed', 'ai', 'Australia'),
        # --- COMPUTER SCIENCE NEWS ---
        ('https://cacm.acm.org/news/rss', 'computer_science', 'North America'),
        ('https://www.euronews.com/rss?level=theme&name=technology', 'computer_science', 'Europe'),
        ('https://www.scmp.com/rss/91/feed', 'computer_science', 'Asia'),
        ('https://allafrica.com/tools/headlines/rdf/technology/headlines.rdf', 'computer_science', 'Africa'),
        ('https://www.batimes.com.ar/rss', 'computer_science', 'South America'),
        ('https://www.sbs.com.au/news/topic/computer-science/7e1b7b1e-6b7e-4e2e-8e2e-7e1b7b1e6b7e/feed', 'computer_science', 'Australia'),
        # --- RESEARCH NEWS ---
        ('https://www.sciencedaily.com/rss/top/science.xml', 'research', 'North America'),
        ('https://www.eurekalert.org/rss/europe.xml', 'research', 'Europe'),
        ('https://www.nature.com/subjects/research/rss', 'research', 'Asia'),
        ('https://www.scidev.net/rss/news/africa/', 'research', 'Africa'),
        ('https://www.scidev.net/rss/news/latin-america/', 'research', 'South America'),
        ('https://www.scidev.net/rss/news/oceania/', 'research', 'Australia'),
        # --- TRENDING/GENERAL ---
        ('http://feeds.bbci.co.uk/news/rss.xml', 'trending', 'Europe'),
        ('http://feeds.reuters.com/reuters/topNews', 'trending', 'Europe'),
        ('https://feeds.foxnews.com/foxnews/latest', 'trending', 'North America'),
        ('https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml', 'trending', 'North America'),
        ('https://www.aljazeera.com/xml/rss/all.xml', 'trending', 'Asia'),
        ('https://www.news24.com/news24/rss', 'trending', 'Africa'),
        ('https://www.batimes.com.ar/rss', 'trending', 'South America'),
        ('https://www.abc.net.au/news/feed/51120/rss.xml', 'trending', 'Australia'),
        # --- INTERNATIONAL ---
        ('https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml', 'international', 'North America'),
        ('https://www.washingtontimes.com/rss/headlines/news/world', 'international', 'North America'),
        ('http://rss.cnn.com/rss/money_topstories.rss', 'international', 'North America'),
        ('https://www.bbc.com/news/world/rss.xml', 'international', 'Europe'),
        ('https://www.aljazeera.com/xml/rss/all.xml', 'international', 'Asia'),
        ('https://www.news24.com/news24/rss', 'international', 'Africa'),
        ('https://www.batimes.com.ar/rss', 'international', 'South America'),
        ('https://www.abc.net.au/news/feed/51120/rss.xml', 'international', 'Australia'),
    ]
    count = 0
    for feed, category, continent in feeds:
        try:
            d = feedparser.parse(feed)
            for entry in d.entries:
                pub_date = None
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    pub_date = datetime(*entry.published_parsed[:6])
                elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                    pub_date = datetime(*entry.updated_parsed[:6])
                else:
                    pub_date = datetime.utcnow()
                if pub_date < first_day or pub_date > last_day:
                    continue
                title = entry.title
                summary = getattr(entry, 'summary', getattr(entry, 'description', ''))
                link = entry.link
                news_doc = {
                    'title': title,
                    'summary': summary,
                    'link': link,
                    'source': feed,
                    'timestamp': pub_date,
                    'category': category,
                    'continent': continent
                }
                mongo.db.news.update_one({'title': title, 'link': link}, {'$set': news_doc}, upsert=True)
                count += 1
        except Exception as e:
            print(f"Error scraping {feed}: {e}")
            continue
    return {'success': True, 'message': f'Scraped and stored {count} news articles for this month.'}

def scrape_daily_news():
    now = datetime.utcnow()
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end = now.replace(hour=23, minute=59, second=59, microsecond=999999)
    feeds = [
        # --- STOCKMARKET ---
        ('https://www.cnbc.com/id/100003114/device/rss/rss.html', 'stockmarket', 'North America'),
        ('https://www.ft.com/?format=rss', 'stockmarket', 'Europe'),
        ('https://www.japantimes.co.jp/news_category/business/feed/', 'stockmarket', 'Asia'),
        ('https://allafrica.com/tools/headlines/rdf/business/headlines.rdf', 'stockmarket', 'Africa'),
        ('https://www.buenosairesherald.com/rss', 'stockmarket', 'South America'),
        ('https://www.asx.com.au/rss-feeds', 'stockmarket', 'Australia'),
        # --- CRYPTO ---
        ('https://cointelegraph.com/rss', 'crypto', 'North America'),
        ('https://news.bitcoin.com/feed/', 'crypto', 'North America'),
        ('https://cryptonews.com/news/feed', 'crypto', 'Europe'),
        ('https://cryptoslate.com/feed/', 'crypto', 'Asia'),
        ('https://bitcoinmagazine.com/.rss/full/', 'crypto', 'Africa'),
        ('https://criptonoticias.com/feed/', 'crypto', 'South America'),
        ('https://cryptonews.com.au/feed/', 'crypto', 'Australia'),
        # --- POLITICS ---
        ('https://www.politico.com/rss/politics08.xml', 'politics', 'North America'),
        ('https://feeds.bbci.co.uk/news/politics/rss.xml', 'politics', 'Europe'),
        ('https://www.aljazeera.com/xml/rss/all.xml', 'politics', 'Asia'),
        ('https://allafrica.com/tools/headlines/rdf/politics/headlines.rdf', 'politics', 'Africa'),
        ('https://www.buenosairesherald.com/rss', 'politics', 'South America'),
        ('https://www.abc.net.au/news/politics/feed/51120/rss.xml', 'politics', 'Australia'),
        # --- WAR ---
        ('https://www.aljazeera.com/xml/rss/all.xml', 'war', 'Asia'),
        ('https://www.reuters.com/rssFeed/worldNews', 'war', 'Europe'),
        ('https://www.defense.gov/Newsroom/News/Transcripts/Transcripts-RSS/', 'war', 'North America'),
        ('https://allafrica.com/tools/headlines/rdf/conflict/headlines.rdf', 'war', 'Africa'),
        ('https://www.batimes.com.ar/rss', 'war', 'South America'),
        ('https://www.sbs.com.au/news/topic/war/7e1b7b1e-6b7e-4e2e-8e2e-7e1b7b1e6b7e/feed', 'war', 'Australia'),
        # --- OIL PRICES ---
        ('https://www.oilprice.com/rss/main', 'oil_prices', 'North America'),
        ('https://www.energyvoice.com/feed/', 'oil_prices', 'Europe'),
        ('https://www.reuters.com/business/energy/rss', 'oil_prices', 'Asia'),
        ('https://allafrica.com/tools/headlines/rdf/oil/headlines.rdf', 'oil_prices', 'Africa'),
        ('https://www.batimes.com.ar/rss', 'oil_prices', 'South America'),
        ('https://www.energycouncil.com.au/news/feed/', 'oil_prices', 'Australia'),
        # --- TRADES ---
        ('https://www.bloomberg.com/feed/podcast/etf-report.xml', 'trades', 'North America'),
        ('https://www.ft.com/?format=rss', 'trades', 'Europe'),
        ('https://www.japantimes.co.jp/news_category/business/feed/', 'trades', 'Asia'),
        ('https://allafrica.com/tools/headlines/rdf/trade/headlines.rdf', 'trades', 'Africa'),
        ('https://www.batimes.com.ar/rss', 'trades', 'South America'),
        ('https://www.austrade.gov.au/news/news/rss', 'trades', 'Australia'),
        # --- DEFENCE DEALS ---
        ('https://www.defensenews.com/arc/outboundfeeds/rss/?outputType=xml', 'defence_deals', 'North America'),
        ('https://www.janes.com/defence-news/rss.xml', 'defence_deals', 'Europe'),
        ('https://www.armyrecognition.com/rss/news_asia.xml', 'defence_deals', 'Asia'),
        ('https://www.defenceweb.co.za/feed/', 'defence_deals', 'Africa'),
        ('https://www.infodefensa.com/latam/rss', 'defence_deals', 'South America'),
        ('https://www.australiandefence.com.au/rss', 'defence_deals', 'Australia'),
        # --- INTERNAL RELATIONS ---
        ('https://www.foreignaffairs.com/rss.xml', 'internal_relations', 'North America'),
        ('https://www.euronews.com/rss?level=theme&name=world', 'internal_relations', 'Europe'),
        ('https://www.scmp.com/rss/91/feed', 'internal_relations', 'Asia'),
        ('https://allafrica.com/tools/headlines/rdf/international_relations/headlines.rdf', 'internal_relations', 'Africa'),
        ('https://www.batimes.com.ar/rss', 'internal_relations', 'South America'),
        ('https://www.sbs.com.au/news/topic/international-relations/7e1b7b1e-6b7e-4e2e-8e2e-7e1b7b1e6b7e/feed', 'internal_relations', 'Australia'),
        # --- SOCIAL MEDIA NEWS ---
        ('https://mashable.com/feeds/social-media', 'social_media', 'North America'),
        ('https://www.euronews.com/rss?level=theme&name=technology', 'social_media', 'Europe'),
        ('https://www.scmp.com/rss/91/feed', 'social_media', 'Asia'),
        ('https://allafrica.com/tools/headlines/rdf/technology/headlines.rdf', 'social_media', 'Africa'),
        ('https://www.batimes.com.ar/rss', 'social_media', 'South America'),
        ('https://www.sbs.com.au/news/topic/social-media/7e1b7b1e-6b7e-4e2e-8e2e-7e1b7b1e6b7e/feed', 'social_media', 'Australia'),
        # --- AI RELATED NEWS ---
        ('https://www.technologyreview.com/feed/', 'ai', 'North America'),
        ('https://www.euronews.com/rss?level=theme&name=technology', 'ai', 'Europe'),
        ('https://www.scmp.com/rss/91/feed', 'ai', 'Asia'),
        ('https://allafrica.com/tools/headlines/rdf/technology/headlines.rdf', 'ai', 'Africa'),
        ('https://www.batimes.com.ar/rss', 'ai', 'South America'),
        ('https://www.sbs.com.au/news/topic/artificial-intelligence/7e1b7b1e-6b7e-4e2e-8e2e-7e1b7b1e6b7e/feed', 'ai', 'Australia'),
        # --- COMPUTER SCIENCE NEWS ---
        ('https://cacm.acm.org/news/rss', 'computer_science', 'North America'),
        ('https://www.euronews.com/rss?level=theme&name=technology', 'computer_science', 'Europe'),
        ('https://www.scmp.com/rss/91/feed', 'computer_science', 'Asia'),
        ('https://allafrica.com/tools/headlines/rdf/technology/headlines.rdf', 'computer_science', 'Africa'),
        ('https://www.batimes.com.ar/rss', 'computer_science', 'South America'),
        ('https://www.sbs.com.au/news/topic/computer-science/7e1b7b1e-6b7e-4e2e-8e2e-7e1b7b1e6b7e/feed', 'computer_science', 'Australia'),
        # --- RESEARCH NEWS ---
        ('https://www.sciencedaily.com/rss/top/science.xml', 'research', 'North America'),
        ('https://www.eurekalert.org/rss/europe.xml', 'research', 'Europe'),
        ('https://www.nature.com/subjects/research/rss', 'research', 'Asia'),
        ('https://www.scidev.net/rss/news/africa/', 'research', 'Africa'),
        ('https://www.scidev.net/rss/news/latin-america/', 'research', 'South America'),
        ('https://www.scidev.net/rss/news/oceania/', 'research', 'Australia'),
        # --- TRENDING/GENERAL ---
        ('http://feeds.bbci.co.uk/news/rss.xml', 'trending', 'Europe'),
        ('http://feeds.reuters.com/reuters/topNews', 'trending', 'Europe'),
        ('https://feeds.foxnews.com/foxnews/latest', 'trending', 'North America'),
        ('https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml', 'trending', 'North America'),
        ('https://www.aljazeera.com/xml/rss/all.xml', 'trending', 'Asia'),
        ('https://www.news24.com/news24/rss', 'trending', 'Africa'),
        ('https://www.batimes.com.ar/rss', 'trending', 'South America'),
        ('https://www.abc.net.au/news/feed/51120/rss.xml', 'trending', 'Australia'),
        # --- INTERNATIONAL ---
        ('https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml', 'international', 'North America'),
        ('https://www.washingtontimes.com/rss/headlines/news/world', 'international', 'North America'),
        ('http://rss.cnn.com/rss/money_topstories.rss', 'international', 'North America'),
        ('https://www.bbc.com/news/world/rss.xml', 'international', 'Europe'),
        ('https://www.aljazeera.com/xml/rss/all.xml', 'international', 'Asia'),
        ('https://www.news24.com/news24/rss', 'international', 'Africa'),
        ('https://www.batimes.com.ar/rss', 'international', 'South America'),
        ('https://www.abc.net.au/news/feed/51120/rss.xml', 'international', 'Australia'),
    ]
    count = 0
    for feed, category, continent in feeds:
        try:
            d = feedparser.parse(feed)
            for entry in d.entries:
                pub_date = None
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    pub_date = datetime(*entry.published_parsed[:6])
                elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                    pub_date = datetime(*entry.updated_parsed[:6])
                else:
                    pub_date = datetime.utcnow()
                if pub_date < start or pub_date > end:
                    continue
                title = entry.title
                summary = getattr(entry, 'summary', getattr(entry, 'description', ''))
                link = entry.link
                news_doc = {
                    'title': title,
                    'summary': summary,
                    'link': link,
                    'source': feed,
                    'timestamp': pub_date,
                    'category': category,
                    'continent': continent
                }
                mongo.db.news.update_one({'title': title, 'link': link}, {'$set': news_doc}, upsert=True)
                count += 1
        except Exception as e:
            print(f"Error scraping {feed}: {e}")
            continue
    print(f'Scraped and stored {count} news articles for today.')

# Add daily job to scheduler
schedular.add_job(func=scrape_daily_news, trigger='cron', hour=0, minute=30)

@app.route('/save-subscription', methods=['POST'])
@login_required
def save_subscription():
    sub = request.get_json()
    user_email = session.get('user')
    from datetime import datetime
    now = datetime.utcnow()
    if user_email:
        mongo.db.users.update_one(
            {'email': user_email},
            {'$set': {
                'push_subscription_status': 'subscribed',
                'push_subscription_date': now,
                'subscription': sub
            }}
        )
        mongo.db.subscriptions.update_one({'endpoint': sub['endpoint']}, {'$set': {**sub, 'user': user_email}}, upsert=True)
    else:
        mongo.db.subscriptions.update_one({'endpoint': sub['endpoint']}, {'$set': sub}, upsert=True)
    return jsonify({'success': True})

def send_push(subscription_info, data):
    try:
        print(f"Sending push to: {subscription_info.get('endpoint')}")
        print(f"Payload: {data}")
        webpush(
            subscription_info=subscription_info,
            data=json.dumps(data),
            vapid_private_key=PRIVATE_VAPID_KEY,
            vapid_claims={"sub": "mailto:admin@example.com"}
        )
        print("Push sent successfully.")
    except WebPushException as ex:
        print(f"Web push failed: {ex}")
        if hasattr(ex, 'response') and ex.response is not None:
            print(f"Response status: {ex.response.status_code}")
            print(f"Response body: {ex.response.content}")
    except Exception as e:
        print(f"General error sending push: {e}")

@app.route('/send-test-notification', methods=['POST'])
@login_required
def send_test_notification():
    user_email = session.get('user')
    if not user_email:
        return jsonify({'error': 'Unauthorized'}), 401
    user = mongo.db.users.find_one({'email': user_email})
    if not user or 'subscription' not in user:
        return jsonify({'error': 'No subscription found'}), 400
    # Send a test notification regardless of location/news
    test_data = {
        'title': 'Test Push Notification',
        'body': 'This is a test push notification from your server!',
        'url': 'https://example.com'
    }
    try:
        send_push(user['subscription'], test_data)
        return '', 200
    except Exception as e:
        print('Push error:', e)
        return jsonify({'error': str(e)}), 500

@app.route('/save-location', methods=['POST'])
def save_location():
    user_email = session.get('user')
    if not user_email:
        return 'Unauthorized', 401
    data = request.get_json()
    lat = data.get('latitude')
    lon = data.get('longitude')
    if lat is not None and lon is not None:
        mongo.db.users.update_one({'email': user_email}, {'$set': {'location': {'lat': lat, 'lon': lon}}})
        return 'OK', 200
    return 'Bad Request', 400

@app.route('/has-location')
def has_location():
    user_email = session.get('user')
    if not user_email:
        return jsonify({'has_location': False})
    user = mongo.db.users.find_one({'email': user_email})
    has_loc = bool(user and user.get('location'))
    return jsonify({'has_location': has_loc})

def load_cities():
    with open(os.path.join(os.path.dirname(__file__), 'cities.json')) as f:
        return json.load(f)

def haversine(lat1, lon1, lat2, lon2):
    R = 6371  # Earth radius in km
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

def find_nearest_city(lat, lon, cities):
    min_dist = float('inf')
    nearest = None
    for city in cities:
        dist = haversine(lat, lon, city['lat'], city['lon'])
        if dist < min_dist:
            min_dist = dist
            nearest = city
    return nearest

def send_local_news_notifications(news_items):
    cities = load_cities()
    users = list(mongo.db.users.find({'location': {'$exists': True}}))
    for item in news_items:
        headline, detail, link, city = item
        if not city:
            continue
        for user in users:
            loc = user.get('location')
            if not loc:
                continue
            user_city = find_nearest_city(loc['lat'], loc['lon'], cities)
            if user_city and user_city['name'] == city['name']:
                # Send notification
                sub = mongo.db.subscriptions.find_one({'user': user['email']})
                if sub:
                    payload = {
                        'title': f'Local News: {city["name"]}',
                        'body': headline,
                        'url': link
                    }
                    try:
                        webpush(
                            subscription_info=sub,
                            data=json.dumps(payload),
                            vapid_private_key=PRIVATE_VAPID_KEY,
                            vapid_claims={"sub": "mailto:admin@example.com"}
                        )
                    except WebPushException as ex:
                        print(f'Push failed for {user["email"]}:', ex)

def get_important_news_for_city(city_name, max_items=2):
    important_keywords = [
        'breaking', 'alert', 'emergency', 'curfew', 'shutdown', 'protest', 'accident', 'flood', 'earthquake',
        'fire', 'attack', 'violence', 'missing', 'evacuate', 'warning', 'disaster', 'major', 'critical', 'urgent', 'update'
    ]
    feeds = [
        'https://www.greaterkashmir.com/feed/',
        'https://globalkashmir.net/feed/',
        'https://kashmirreader.com/feed/'
    ]
    all_news = []
    for url in feeds:
        try:
            news_items = localfeeds.get_local(url)
            for item in news_items:
                if item[3] and item[3]['name'].lower() == city_name.lower():
                    text = (item[0] + ' ' + item[1]).lower()
                    if any(kw in text for kw in important_keywords):
                        all_news.append(item)
        except Exception as e:
            print(f'Error fetching news from {url}:', e)
    return all_news[:max_items]

def scheduled_local_news_notifications():
    cities = load_cities()
    for city in cities:
        news_items = get_important_news_for_city(city['name'], max_items=2)
        if news_items:
            send_local_news_notifications(news_items)

# Schedule the job every 4 minutes
schedular.add_job(func=scheduled_local_news_notifications, trigger='interval', minutes=4)

@app.route('/api/important-news')
@login_required
def api_important_news():
    user_email = session.get('user')
    if not user_email:
        return jsonify({'error': 'Unauthorized'}), 401
    user = mongo.db.users.find_one({'email': user_email})
    if not user or 'location' not in user:
        return jsonify({'error': 'No location found'}), 400
    loc = user['location']
    cities = load_cities()
    user_city = find_nearest_city(loc['lat'], loc['lon'], cities)
    if not user_city:
        return jsonify({'error': 'No city found'}), 400
    city_name = user_city['name']
    news_items = get_important_news_for_city(city_name, max_items=3)
    formatted = [
        {
            'title': item[0],
            'summary': item[1],
            'link': item[2],
            'city': city_name
        } for item in news_items
    ]
    return jsonify(formatted)

def scheduled_important_news_notifications():
    cities = load_cities()
    users = list(mongo.db.users.find({'location': {'$exists': True}}))
    for user in users:
        loc = user.get('location')
        if not loc:
            continue
        user_city = find_nearest_city(loc['lat'], loc['lon'], cities)
        if not user_city:
            continue
        city_name = user_city['name']
        news_items = get_important_news_for_city(city_name, max_items=3)
        if not news_items:
            continue
        sub = mongo.db.subscriptions.find_one({'user': user['email']})
        if not sub:
            continue
        for item in news_items:
            payload = {
                'title': f'Important News: {city_name}',
                'body': item[0],
                'url': item[2]
            }
            send_push(sub, payload)

# Remove old local news notification job and schedule the new one
schedular.add_job(func=scheduled_important_news_notifications, trigger='interval', minutes=4)

@app.route('/sw.js')
def sw():
    return send_from_directory('.', 'sw.js', mimetype='application/javascript')

@app.route('/vapid-public-key')
def vapid_public_key():
    return PUBLIC_VAPID_KEY

def scrape_trends24_india(page=1, page_size=6):
    url = 'https://trends24.in/india/'
    try:
        response = requests.get(url, timeout=10)
        if response.status_code != 200:
            print(f"Failed to fetch trends24.in/india: {response.status_code}")
            return []
        soup = BeautifulSoup(response.text, 'html.parser')
        trends = []
        trend_list = soup.find('ol', class_='trend-card__list')
        if not trend_list:
            print("No trend list found on trends24.in/india")
            return []
        for li in trend_list.find_all('li'):
            a = li.find('a')
            if a:
                trends.append({
                    'name': a.get_text(strip=True),
                    'url': a['href'] if a.has_attr('href') else None,
                    'tweet_volume': None
                })
        # Pagination
        start = (page - 1) * page_size
        end = start + page_size
        return trends[start:end]
    except Exception as e:
        print(f"Error scraping trends24.in/india: {e}")
        return []

@app.route('/api/twitter-trends')
def api_twitter_trends():
    try:
        page = int(request.args.get('page', 1))
        page_size = int(request.args.get('page_size', 6))
    except Exception:
        page, page_size = 1, 6
    trends = scrape_trends24_india(page, page_size)
    return jsonify(trends)

@app.route('/twitter-trending')
@login_required
def twitter_trending():
    trends = scrape_trends24_india(page=1, page_size=6)
    return render_template('twitter_trends.html', trends=trends)

if __name__ == '__main__':
    app.run(debug=False, port=5033, host='0.0.0.0')











