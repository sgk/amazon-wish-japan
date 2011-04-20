#vim:fileencoding=utf-8

from flask import Flask, render_template, request
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
  wish_pieces = db.IntegerProperty()
  got_pieces = db.IntegerProperty()
  wish_amount = db.IntegerProperty()
  got_amount = db.IntegerProperty()

class Item(db.Model):
  page = db.ReferenceProperty()
  name = db.StringProperty()		# 商品名
  price = db.IntegerProperty()		# 価格
  pieces = db.IntegerProperty()		# 個数
  tweeted = db.DateTimeProperty(default=VERY_OLD)

################################################################################

# XXX 重要度を記録するか？

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
    wp = gp = wa = ga = 0
    for name, price, wish, got in iteritems:
      wp += wish
      gp += got
      wa += wish * price
      ga += got * price
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
    page.wish_pieces = wp
    page.got_pieces = gp
    page.wish_amount = wa
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
  return render_template('top.html', pages=pages)

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
