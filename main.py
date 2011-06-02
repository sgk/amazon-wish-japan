#vim:fileencoding=utf-8

from flask import (
  Flask, render_template, request, redirect, url_for, abort,
  Response
)
from google.appengine.api import memcache

import datetime
import time
import operator
import functools
import csv

import amazon
import auth
import tzconv
from models import *

app = Flask('app')
app.debug = True

CRAWL_INTERVAL = 10 * 60

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
    count += 1
    memcache.flush_all()
  return str(count)

def page_cache(func):
  @functools.wraps(func)
  def decorated(*args, **kw):
    data = memcache.get(request.path)
    if not data or not isinstance(data, unicode):
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
    now=tzconv.jst_from_utc(datetime.datetime.now()),
  )

@app.route('/add_certifier', methods=['GET', 'POST'])
def add_certifier():
  if request.method == 'GET':
    return render_template('add_certifier.html')
  name = request.form.get('name', '').strip().lower()
  Certifier.get_or_insert(name,
    icon=request.form.get('icon', '').strip(),
    width=int(request.form.get('width', '').strip()),
    height=int(request.form.get('height', '').strip()),
    alt=request.form.get('alt', '').strip(),
    password=request.form.get('password', ''),
  )
  return redirect(url_for('edit', certifier=name))

def check_auth(username, password):
  certifier = Certifier.get_by_key_name(username)
  return certifier and certifier.password == password

@app.route('/edit/<certifier>', methods=['GET', 'POST'])
@auth.login_required(check_auth)
def edit(certifier):
  certifier = certifier.lower()
  if request.authorization.username != certifier:
    abort(401)
  certifier = Certifier.get_by_key_name(certifier)
  if not certifier:
    abort(404)

  if request.method == 'GET':
    pages = WishListPage.all()
    pages = pages.filter('owner_name !=', None)
    pages = list(pages)
    pages.sort(key=operator.attrgetter('owner_name'))
    pages.sort(key=operator.attrgetter('wish_pieces'), reverse=True)
    pages.sort(key=operator.attrgetter('wish_amount'), reverse=True)
    return render_template('edit.html', certifier=certifier, pages=pages)

  marks = request.form.getlist('marks')
  pages = WishListPage.all()
  pages = pages.filter('owner_name !=', None)
  pages = list(pages)
  for page in pages:
    if page.key().name() in marks:
      if not certifier in page.certifiers:
	PageCertifier(
	  page=page,
	  certifier=certifier,
	).put()
    else:
      if certifier in page.certifiers:
	for o in page.pagecertifier_set:
	  if o.certifier == certifier:
	    o.delete()

  return redirect(request.path)

@app.route('/download/<certifier>.csv')
@auth.login_required(check_auth)
def download_csv(certifier):
  certifier = certifier.lower()
  if request.authorization.username != certifier:
    abort(401)
  certifier = Certifier.get_by_key_name(certifier)
  if not certifier:
    abort(404)

  response = Response(
    headers={'content-disposition': 'attachment; filename=%s.csv' % certifier.key().name()},
    content_type='text/csv; charset=sjis',
  )
  writer = csv.writer(response.stream, quoting=csv.QUOTE_NONNUMERIC)

  writer.writerow(('ID', 'name', 'wish_items', 'wish_pieces', 'wish_amount', 'got_items', 'got_pieces', 'got_amount'))
  for page in certifier.pages:
    writer.writerow((
      page.key().name(),
      page.owner_name.encode('cp932'),
      page.wish_items,
      page.wish_pieces,
      page.wish_amount,
      page.got_items,
      page.got_pieces,
      page.got_amount,
    ))

  return response

@app.route('/download/amazon.xml')
@auth.login_required(check_auth)
def download_xml():
  certifier = 'amazon'
  if request.authorization.username != certifier:
    abort(401)
  certifier = Certifier.get_by_key_name(certifier)
  if not certifier:
    abort(404)

  pages = list(certifier.pages)
  pages.sort(key=operator.attrgetter('owner_name'))
  pages.sort(key=operator.attrgetter('wish_pieces'), reverse=True)
  pages.sort(key=operator.attrgetter('wish_amount'), reverse=True)

  now = tzconv.jst_from_utc(datetime.datetime.now())

  text = render_template('wishlist.xml', pages=pages, now=now)
  text = text.encode('cp932')

  fname = certifier.key().name()
  fname += '_'
  fname += now.strftime('%Y%m%d%H%M')
  fname += '.xml'

  return Response(
    text,
    headers={'content-disposition': 'attachment; filename=%s' % fname},
    content_type='text/xml; charset=sjis',
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

@app.template_filter('strftime')
def strftime(value, fmt):
  return value.strftime(fmt)
