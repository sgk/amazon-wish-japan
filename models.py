#vim:fileencoding=utf-8

import datetime
from google.appengine.ext import db

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

  @property
  def certifiers(self):
    return (o.certifier for o in self.pagecertifier_set)

class Certifier(db.Model):
  # key: lower case name		# 'amazon'
  icon = db.StringProperty()		# アイコンファイルのURL
  width = db.IntegerProperty()
  height = db.IntegerProperty()
  alt = db.StringProperty()		# iconのaltテキスト
  password = db.StringProperty()

  @property
  def pages(self):
    return (o.page for o in self.pagecertifier_set)

  def __eq__(self, arg):
    return self.key() == arg.key()

class PageCertifier(db.Model):
  page = db.ReferenceProperty(WishListPage)
  certifier = db.ReferenceProperty(Certifier)

class Item(db.Model):
  # key: id.name
  page = db.ReferenceProperty()
  name = db.StringProperty()		# 商品名
  price = db.IntegerProperty()		# 価格
  pieces = db.IntegerProperty()		# 個数
  tweeted = db.DateTimeProperty()

class Config(db.Model):
  # key: config key
  value = db.StringProperty()

def config_set(key, value):
  Config(key_name=key, value=value).put()

def config_get(key):
  o = Config.get_by_key_name(key)
  return str(o.value) if o else ''	# DB value is unicode.
