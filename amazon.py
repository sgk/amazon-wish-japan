#!/usr/bin/python
#vim:fileencoding=utf-8

import urllib2
import re

WISHLIST_LIST_URL = u'http://www.amazon.co.jp/gp/registry/search.html?type=wishlist&field-name=【被災地】|【避難所】&page=%d'
RE_LIST_COUNT = re.compile(u'- (\d+) 件が一致しました。')
RE_WISHID = re.compile('<a href="/registry/wishlist/([0-9A-Z]+)">')

WISH_LIST_URL = u'http://www.amazon.co.jp/registry/wishlist/%s?reveal=all&filter=all&sort=date-added&layout=compact&page=%d'
RE_OWNER = re.compile(u'<tr><th>受取人</th><td class="profileInfoField" id="profile-name-Field">([^<]*)</td></tr>')
RE_ALL_ITEMS_COUNT = re.compile('<span id="topItemCount">(\d+)</span>')
RE_WISH_ITEMS_COUNT = re.compile('<span class="regListCount">(\d+)</span>')
RE_ITEM = re.compile('<strong>\s*<a href="[^"]*">(?P<name>.*)</a>\s*.*</td>\s*<td>.*</td>\s*<td class="tiny">(?P<price>.*)</td>\s*<td align="center" class="tiny">(?P<all>\d*)</td>\s*<td align="center" class="tiny">(?P<got>\d*)</td>\s*<td align="center" class="tiny">(?P<priority>[^<]*)</td>')
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
  firstpage = get_page_text(WISH_LIST_URL % (id, 1))
  m = RE_OWNER.search(firstpage)
  owner = decode_entity(m.group(1))
  owner = owner.replace(u'\u200b', '')
  owner = owner.replace(u'【被災地】', '')
  owner = owner.replace(u'【避難所】', '')

  m = RE_ALL_ITEMS_COUNT.search(firstpage)
  all_items = int(m.group(1)) if m else 0
  #m = RE_WISH_ITEMS_COUNT.search(text)
  #wish_items = int(m.group(1)) if m else 0

  def iteritem():
    # 「何でも欲しい物ボタン」の商品は無視する。
    page = 1
    text = firstpage
    while True:
      for m in RE_ITEM.finditer(text):
	name = decode_entity(m.group('name'))
	name = name.replace(u'\u200b', '')
	mm = RE_PRICE.search(m.group('price'))
	price = int(mm.group(1)) if mm else 0
	all_ = int(m.group('all'))
	got = int(m.group('got'))
	#priority = m.group('priority')
	wish = max(all_ - got, 0)
	yield name, price, wish, got
      if page * 100 >= all_items:
	break
      page += 1
      text = get_page_text(WISH_LIST_URL % (id, page))

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
