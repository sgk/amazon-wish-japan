#!/usr/bin/python
#vim:fileencoding=utf-8

import urllib2
import re

WISHLIST_LIST_URL = u'http://www.amazon.co.jp/gp/registry/search.html?type=wishlist&field-name=【被災地】&page=%d'
RE_LIST_COUNT = re.compile(u'- (\d+) 件が一致しました。')
RE_WISHID = re.compile('<a href="/registry/wishlist/([0-9A-Z]+)">')

WISH_LIST_URL = u'http://www.amazon.co.jp/registry/wishlist/%s?reveal=all&filter=all&sort=date-added&layout=compact'
RE_OWNER = re.compile('<tr><th>For</th><td class="profileInfoField" id="profile-name-Field">([^<]*)</td></tr>')
RE_ALL_ITEMS_COUNT = re.compile('<span id="topItemCount">(\d+)</span>')
RE_WISH_ITEMS_COUNT = re.compile('<span class="regListCount">(\d+)</span>')
RE_ITEM = re.compile('<strong>\s*<a href="[^"]*">([^<]*)</a>\s*.*</td>\s*<td>.*</td>\s*<td class="tiny">(.*)</td>\s*<td align="center" class="tiny">(\d*)</td>\s*<td align="center" class="tiny">(\d*)</td>\s*<td align="center" class="tiny">([^<]*)</td>')
RE_PRICE = re.compile('\.JPY\.(\d+)"')

################################################################################

RE_ENTITY = re.compile('&#(\d+);')

def decode_entity_helper(m):
  id = m.group(1)
  try:
    return unichr(int(id))
  except:
    return '&#%s;' % id

def decode_entity(s):
  return RE_ENTITY.sub(decode_entity_helper, s)

def get_page_text(url):
  page = urllib2.urlopen(url.encode('utf-8'))
  page = page.read()
  page = page.decode('cp932')
  return page

################################################################################

def get_wishlist_list():
  page = 0
  while True:
    page += 1
    text = get_page_text(WISHLIST_LIST_URL % page)
    m = RE_LIST_COUNT.search(text)
    count = int(m.group(1))
    for m in RE_WISHID.finditer(text):
      yield m.group(1)
    if page * 25 >= count:
      break

def get_wishlist_page(id):
  text = get_page_text(WISH_LIST_URL % id)
  m = RE_OWNER.search(text)
  owner = decode_entity(m.group(1))

  #m = RE_ALL_ITEMS_COUNT.search(text)
  #all_items = int(m.group(1)) if m else 0
  #m = RE_WISH_ITEMS_COUNT.search(text)
  #wish_items = int(m.group(1)) if m else 0

  def iteritem():
    # XXX 複数ページの処理が必要。
    # 「何でも欲しい物ボタン」の商品は無視する。
    for m in RE_ITEM.finditer(text):
      name = decode_entity(m.group(1))
      mm = RE_PRICE.search(m.group(2))
      price = int(mm.group(1)) if mm else 0
      all_ = int(m.group(3))
      got = int(m.group(4))
      #priority = m.group(5)
      wish = max(all_ - got, 0)
      yield name, price, wish, got

  return owner, iteritem()

################################################################################

def main(ids):
  if not ids:
    ids = get_wishlist_list()
  for id in ids:
    owner, iteritem = get_wishlist_page(id)
    print owner.encode('utf-8')
    for name, price, wish, got in iteritem:
      print name.encode('utf-8'), price, wish, got

if __name__ == '__main__':
  import sys
  main(sys.argv[1:])
