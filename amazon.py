#!/usr/bin/python
#vim:fileencoding=utf-8

import urllib2
import re

WISHID_LIST_URL = u'http://www.amazon.co.jp/gp/registry/search.html?type=wishlist&field-name=【被災地】&page=%d'
RE_LIST_COUNT = re.compile(u'- (\d+) 件が一致しました。')
RE_WISHID = re.compile('<a href="/registry/wishlist/([0-9A-Z]+)">')

WISH_LIST_URL = u'http://www.amazon.co.jp/registry/wishlist/%s?reveal=all&filter=all&sort=date-added&layout=compact'
RE_OWNER = re.compile('<tr><th>For</th><td class="profileInfoField" id="profile-name-Field">([^<]*)</td></tr>')
RE_ALL_ITEMS_COUNT = re.compile('<span id="topItemCount">(\d+)</span>')
RE_WISH_ITEMS_COUNT = re.compile('<span class="regListCount">(\d+)</span>')
RE_ITEM = re.compile('<td class="tiny">(.*)</td>\s*<td align="center" class="tiny">(\d*)</td>\s*<td align="center" class="tiny">(\d*)</td>\s*<td align="center" class="tiny">([^<]*)</td>')
RE_PRICE = re.compile('\.JPY\.(\d+)"')

WISH_LIST_PAGE = u'http://www.amazon.co.jp/registry/wishlist/%s'

RE_ENTITY = re.compile('&#(\d+);')

def entity_helper(m):
  id = m.group(1)
  try:
    return unichr(int(id))
  except:
    return '&#%s;' % id

def decode_entity(s):
  return RE_ENTITY.sub(entity_helper, s)

def get_page_text(url):
  page = urllib2.urlopen(url.encode('utf-8'))
  page = page.read()
  page = page.decode('cp932')
  return page

def get_wishid_list():
  page = 0
  while True:
    page += 1
    text = get_page_text(WISHID_LIST_URL % page)
    m = RE_LIST_COUNT.search(text)
    count = int(m.group(1))
    for m in RE_WISHID.finditer(text):
      yield m.group(1)
    if page * 25 >= count:
      break

def get_wish_list(id):
  text = get_page_text(WISH_LIST_URL % id)
  m = RE_OWNER.search(text)
  owner = decode_entity(m.group(1))

  #m = RE_ALL_ITEMS_COUNT.search(text)
  #all_items = int(m.group(1)) if m else 0
  #m = RE_WISH_ITEMS_COUNT.search(text)
  #wish_items = int(m.group(1)) if m else 0

  wish_pieces = got_pieces = 0
  wish_amount = got_amount = 0
  # XXX 複数ページの処理が必要。
  for m in RE_ITEM.finditer(text):
    mm = RE_PRICE.search(m.group(1))
    price = int(mm.group(1)) if mm else 0
    all_ = int(m.group(2))
    got = int(m.group(3))
    #priority = m.group(4)
    if all_ > got:
      wish_pieces += all_ - got
      wish_amount += (all_ - got) * price
    got_pieces += got
    got_amount += got * price

  return owner, wish_pieces, got_pieces, wish_amount, got_amount

def wish_list_page_from_id(id):
  return WISH_LIST_PAGE % id

def main(ids):
  if not ids:
    ids = get_wishid_list()
  for id in ids:
    owner, wp, gp, wa, ga = get_wish_list(id)
    print owner.encode('utf-8')
    print wp, gp, wa, ga

if __name__ == '__main__':
  import sys
  main(sys.argv[1:])
