#vim:fileencoding=utf-8

from flask import Flask, render_template, request, redirect, url_for, abort
app = Flask(__name__)
app.debug = True
from jinja2 import environment

from google.appengine.api import memcache
from google.appengine.ext import db

import datetime
import time
import operator
import amazon

CRAWL_INTERVAL = 5 * 60

################################################################################

VERY_OLD = datetime.datetime.fromtimestamp(0)

class WishListPage(db.Model):
  # key: Wishlist id
  updated = db.DateTimeProperty(default=VERY_OLD)
  owner_name = db.StringProperty()
  wish_items = db.IntegerProperty(default=0)
  wish_pieces = db.IntegerProperty(default=0)
  wish_amount = db.IntegerProperty(default=0)
  got_items = db.IntegerProperty(default=0)
  got_pieces = db.IntegerProperty(default=0)
  got_amount = db.IntegerProperty(default=0)

class Item(db.Model):
  # key: id.name
  page = db.ReferenceProperty()
  name = db.StringProperty()		# 商品名
  price = db.IntegerProperty()		# 価格
  pieces = db.IntegerProperty()		# 個数
  tweeted = db.DateTimeProperty(default=VERY_OLD)

class Config(db.Model):
  # key: config key
  value = db.StringProperty()

################################################################################

# XXX 重要度を記録するか？

# Configuration
@app.route('/config', methods=['GET', 'POST'])
def config():
  if Config.get_by_key_name('configured'):
    abort(404)
  if request.method == 'GET':
    return render_template('config.html')

  import os, base64
  Config(
    key_name='consumer_key',
    value=request.form.get('consumer_key', '').strip()
  ).put()

  Config(
    key_name='consumer_secret',
    value=request.form.get('consumer_secret', '').strip()
  ).put()

  Config(key_name='configured', value='yes').put()

  load_config()
  return redirect('/')

def load_config():
  def get(key):
    o = Config.get_by_key_name(key)
    return str(o.value) if o else ''	# DB value is unicode.

  global consumer_key, consumer_secret
  consumer_key = get('consumer_key')
  consumer_secret = get('consumer_secret')

# cronから起動する。
@app.route('/update_list')
def update_list():
  ids = list(amazon.get_wishlist_list())
  for id in ids:
    WishListPage.get_or_insert(id)
  for page in WishListPage.all():
    if page.key().name() not in ids:
      page.delete()
  return str(len(ids))

# cronから起動する。
# 30秒の時間制限いっぱいまで、クロールする。
@app.route('/update_pages')
def update_pages():
  count = 0
  older_than = datetime.datetime.fromtimestamp(time.time() - CRAWL_INTERVAL)
  pages = WishListPage.all().filter('updated <', older_than).order('updated')
  for page in pages:
    id = page.key().name()
    try:
      owner, iteritems = amazon.get_wishlist_page(id)
    except:
      page.delete()
      continue

    # items
    names = set(item.name for item in Item.all().filter('page', page))
    wi = gi = wp = gp = wa = ga = 0
    for name, price, wish, got in iteritems:
      wp += wish
      gp += got
      wa += wish * price
      ga += got * price
      if wish > 0:
	wi += 1
      if got > 0:
	gi += 1

      if wish == 0:
	continue
      Item.get_or_insert(
	key_name=('%s.%s' % (id, name)),
	page=page,
	name=name,
	price=price,
	pieces=wish,
      )
      try:
	names.remove(name)
      except KeyError:
	pass
    for name in names:
      o = Item.get_by_key_name('%s.%s' % (id, name))
      if o:
	o.delete()

    # page
    page.updated = datetime.datetime.now()
    page.owner_name = owner
    page.wish_items = wi
    page.wish_pieces = wp
    page.wish_amount = wa
    page.got_items = gi
    page.got_pieces = gp
    page.got_amount = ga
    page.put()
    memcache.flush_all()
    count += 1
  return str(count)

def page_cache(func):
  def decorated(*args, **kw):
    data = memcache.get(request.path)
    if not data or not isinstance(data, str):
      data = func(*args, **kw)
      memcache.set(request.path, data)
    return data
  return decorated

@app.route('/')
@page_cache
def top():
  pages = WishListPage.all()
  pages = pages.filter('owner_name !=', None)
  pages = list(pages)
  pages.sort(key=operator.attrgetter('owner_name'))
  pages.sort(key=operator.attrgetter('wish_pieces'), reverse=True)
  pages.sort(key=operator.attrgetter('wish_amount'), reverse=True)

  wi = gi = wp = gp = wa = ga = 0
  for page in pages:
    wi += page.wish_items
    wp += page.wish_pieces
    wa += page.wish_amount
    gi += page.got_items
    gp += page.got_pieces
    ga += page.got_amount

  return render_template('top.html',
    pages=pages,
    wi=wi, wp=wp, wa=wa, gi=gi, gp=gp, ga=ga,
  )

@app.template_filter('comma')
def comma_filter(value):
  r = ''
  while value >= 1000:
    value, tail = divmod(value, 1000)
    r = ',%03d%s' % (tail, r)
  return '%d%s' % (value, r)

@app.template_filter('minutes_ago')
def minutes_ago_filter(value):
  return ((datetime.datetime.now() - value).seconds + 30) / 60
