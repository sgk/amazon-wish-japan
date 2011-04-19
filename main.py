#vim:fileencoding=utf-8

from flask import Flask, render_template
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

################################################################################

# XXX 重要度を記録するか？

# cronから起動する。
@app.route('/update_list')
def update_wishid_list():
  ids = list(amazon.get_wishid_list())
  for id in ids:
    WishListPage.get_or_insert(
      id,
      owner_name=id,
    )
  for page in WishListPage.all():
    if page.key().name() not in ids:
      page.delete()
  return str(len(ids))

# cronから起動する。
# 30秒の時間制限いっぱいまで、クロールする。
@app.route('/update_pages')
def update_wish_pages():
  count = 0
  older_than = datetime.datetime.fromtimestamp(time.time() - CRAWL_INTERVAL)
  pages = WishListPage.all().filter('updated <', older_than).order('updated')
  for page in pages:
    try:
      owner, wp, gp, wa, ga = amazon.get_wish_list(page.key().name())
    except:
      page.delete()
      continue
    page.updated = datetime.datetime.now()
    page.owner_name = owner
    page.wish_pieces = wp
    page.got_pieces = gp
    page.wish_amount = wa
    page.got_amount = ga
    page.put()
    count += 1
  return str(count)

@app.route('/')
def top():
  pages = WishListPage.all().order('-wish_amount')
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
