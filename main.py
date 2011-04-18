#vim:fileencoding=utf-8

from flask import Flask, render_template
app = Flask(__name__)
app.debug = True
from jinja2 import environment

from google.appengine.api import memcache
from google.appengine.ext import db

import datetime
import time
import amazon

CRAWL_INTERVAL = 5 * 60

################################################################################

VERY_OLD = datetime.datetime.fromtimestamp(0)

class WishId(db.Model):
  # key: Wishlist id
  updated = db.DateTimeProperty(auto_now=True)
  page_updated = db.DateTimeProperty(default=VERY_OLD)

class WishPage(db.Model):
  # key: Wishlist id
  owner_name = db.StringProperty()
  wish_items = db.IntegerProperty()
  got_items = db.IntegerProperty()
  wish_amount = db.IntegerProperty()
  got_amount = db.IntegerProperty()

################################################################################

# XXX 最終更新時刻を表示する。
# XXX 重要度を記録するか？

# cronから起動する。
@app.route('/update_wishid_list')
def update_wishid_list():
  for id in amazon.get_wishid_list():
    WishId.get_or_insert(id)
    WishPage.get_or_insert(
      id,
      owner_name=id,
    )
  # XXX 古くなったまま現れない物は削除する。
  return ''

# cronから起動する。
# 30秒の時間制限いっぱいまで、クロールする。
@app.route('/update_wish_pages')
def update_wish_pages():
  older_than = datetime.datetime.fromtimestamp(time.time() - CRAWL_INTERVAL)
  ids = WishId.all().filter('page_updated <', older_than).order('page_updated')
  for id in ids:
    try:
      owner, wp, gp, wa, ga = amazon.get_wish_list(id.key().name())
    except:
      # XXX 削除する。
      continue
    WishPage(
      key_name=id.key().name(),
      wishid=id,
      owner_name=owner,
      wish_items=wp,
      got_items=gp,
      wish_amount=wa,
      got_amount=ga,
    ).put()
    id.page_updated = datetime.datetime.now()
    id.put()
  return ''

@app.route('/')
def top():
  pages = WishPage.all().order('-wish_amount')
  return render_template('top.html', pages=pages)

@app.template_filter('comma')
def comma_filter(value):
  r = ''
  while value >= 1000:
    value, tail = divmod(value, 1000)
    r = ',%03d%s' % (tail, r)
  return '%d%s' % (value, r)
