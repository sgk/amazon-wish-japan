#vim:fileencoding=utf-8

from flask import render_template, request, redirect, url_for, flash

import datetime
import tweepy
from models import *
from main import app
import shorten

# Configuration
@app.route('/config', methods=['GET', 'POST'])
def config():
  if request.method == 'GET':
    return render_template('config.html',
      consumer_key=config_get('consumer_key'),
      consumer_secret=config_get('consumer_secret'),
      google_api_key=config_get('google_api_key'),
    )

  config_set('consumer_key', request.form.get('consumer_key', '').strip())
  config_set('consumer_secret', request.form.get('consumer_secret', '').strip())
  config_set('google_api_key', request.form.get('google_api_key', '').strip())
  return redirect(url_for('top'))

@app.route('/login')
def login():
  # OAuth
  try:
    auth = tweepy.OAuthHandler(
      config_get('consumer_key'),
      config_get('consumer_secret'),
      url_for('callback', _external=True),
      # XXX callbackをつけた場合、Twitter APIのサイト上で、
      # XXX 「Browserタイプ」を選択しておかないと401になる。
    )
    authurl = auth.get_authorization_url()
    config_set('request_key', auth.request_token.key)
    config_set('request_secret', auth.request_token.secret)
  except tweepy.TweepError, e:
    flash(e)
    return render_template('login.html')
  return render_template('login.html', authurl=authurl)

@app.route('/callback')
def callback():
  oauth_token = request.args.get('oauth_token')
  oauth_verifier = request.args.get('oauth_verifier')
  if not oauth_token:
    flash('Invalid callback URL')
    return redirect(url_for('top'))

  request_token_key = config_get('request_key')
  request_token_secret = config_get('request_secret')
  if not request_token_key or not request_token_secret:
    flash('No request token')
    return redirect(url_for('top'))

  if oauth_token != request_token_key:
    flash('Invalid oauth_token')
    return redirect(url_for('top'))

  try:
    auth = tweepy.OAuthHandler(
      config_get('consumer_key'),
      config_get('consumer_secret'),
    )
    auth.set_request_token(request_token_key, request_token_secret)
    auth.get_access_token(oauth_verifier)
    config_set('access_token_key', auth.access_token.key)
    config_set('access_token_secret', auth.access_token.secret)
  except tweepy.TweepError, e:
    flash(e)
  return redirect(url_for('top'))

def tweepy_api():
  auth = tweepy.OAuthHandler(
    config_get('consumer_key'),
    config_get('consumer_secret'),
  )
  auth.set_access_token(
    config_get('access_token_key'),
    config_get('access_token_secret'),
  )
  api = tweepy.API(auth)
  return api if api.verify_credentials() else False

@app.route('/tweet_new_item')
def tweet_new_item():
  google_api_key = config_get('google_api_key')
  api = tweepy_api()
  if not api:
    return ''

  count = 0
  for item in Item.all().filter('tweeted =', None):
    if item.pieces == 0 or not item.page:
      item.tweeted = datetime.datetime.now()
      item.put()
      continue

    preamble = u'被災地必要物資：'
    item_name = item.name
    owner_name = ' ' + item.page.owner_name
    url = shorten.google(
      'http://www.amazon.co.jp/registry/wishlist/' + item.page.key().name(),
      google_api_key,
    )
    postamble = u' 一覧http://t.co/CRfM4Zy'

    n = len(preamble) + len(item_name) + len(owner_name) + len(url) + len(postamble)- 140
    if n > 0:
      item_name = item_name[:70] + u'…'
      n = len(preamble) + len(item_name) + len(owner_name) + len(url) + len(postamble)- 140
      if n > 0:
	n -= 2
	owner_name = owner_name[:-n] + u'…'

    text = preamble + item_name + owner_name + url + postamble

    try:
      api.update_status(text)
    except TweepError:
      pass
    item.tweeted = datetime.datetime.now()
    item.put()
    count += 1
  return str(count)
