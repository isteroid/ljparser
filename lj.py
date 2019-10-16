import os
import time
import json
import random
import datetime
import requests
from bs4 import BeautifulSoup
from pathlib import Path


def title(title: str):
	print('='*40)
	print(title)
	print('-'*40)

def extractpostid(url: str) -> str:
	# извлекаем  '745676'   из 'https://evo-lutio.livejournal.com/745676.html?skip=10'
	return str.split(str.split(url, '.html')[0], '/')[-1]


def extractljname(url: str) -> str:
	# извлекаем 'evo-lutio' из 'https://evo-lutio.livejournal.com/745676.html?skip=10'
	return str.split(str.split(url, '.livejournal.com')[0], '//')[1]


def checkpath(filename: str):
	if filename.startswith('http'):
		a = 1 / 0
	filepath = os.path.dirname(filename)
	if filepath:
		os.makedirs(filepath, exist_ok=True)


def savetofile(data, filename, mode='w'):
	if filename[-5:] == '.json':
		try:
			data = json.dumps(data, indent=4, sort_keys=False)
		except:
			pass
	elif filename[-4:] in ['.raw', 'html', '.htm']:
		try:
			data = data.prettify()
		except:
			pass
	checkpath(filename)
	with open(filename, mode) as file:
		file.write(str(data))


def loadfromfile(filename: str, lines=False) -> str or list:
	with open(filename, 'r') as file:
		if lines:
			return list(map(str.strip, file.readlines()))
		else:
			return file.read()


def checkfileexist(filename: str) -> bool:
	checkpath(filename)
	checkfile = Path(filename)
	if checkfile.is_file():
		return True
	else:
		return False


def jsontextfromscript(source: str, jsonvariablename: str) -> str:
	# из тэга <script> извлекаем json по имени переменной из { ... }
	depth = 0
	slider = str.find(source, jsonvariablename)
	if slider > 0:
		slider = str.find(source, '{', slider + len(jsonvariablename) + 1)
		if slider > 0:
			depth += 1
			start = slider
			while depth > 0:
				closeslider = str.find(source, '}', slider + 1)
				if closeslider > 0:
					depth += source.count('{', slider + 1, closeslider) - 1
					slider = closeslider
				else:
					raise ValueError('Не корректный код JSON - не закрываются скобки!')
			if slider > start:
				return source[start:(slider + 1)]  # да, этот [:] метод вовращает на 1 символ меньше указанного


def extractjson(soup: BeautifulSoup) -> dict:
	scripts = soup.find_all('script')
	for script in scripts:
		txt = jsontextfromscript(str(script), 'Site.page')
		if txt:
			jsondata = json.loads(txt)
			entry = jsondata.get('entry')
			if entry:
				return jsondata
	savetofile(soup.prettify(), 'attention.html')
	url = soup.find('meta', property='og:url')
	print(url)
	raise Exception


def getsoup(url: str) -> BeautifulSoup:
	ljname = extractljname(url)
	postid = extractpostid(url)
	time.sleep(0.21)  # Пауза 0.21сек. Важно! При запросах чаще чем 5 раз в секунду, ЖЖ забанит ваш IP
	httpheaders = { 'GET': '/{postid}.html HTTP/1.1'.format(postid=postid),
					'Host': '{ljname}.livejournal.com'.format(ljname=ljname),
					'Connection': 'keep-alive',
					'Upgrade-Insecure-Requests': '1',
					'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/69.0.3497.100 Safari/537.36',
					'DNT': '1',
					'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
					'Accept-Encoding': 'gzip, deflate, br',
					'Accept-Language': 'ru,en-US;q=0.9,en;q=0.8',
					'Cookie': 'adult_explicit=1'}  # adult_explicit=1 - важен! иначе не скачаются некоторые посты, отмеченные 18+!
	respnse = requests.get(url, headers=httpheaders)
	soup = BeautifulSoup(respnse.text, features='html.parser')
	return soup


def loadcommentspage(ljname: str, postid: str or int, page=1) -> dict:
	# загружает ВСЕ комменты с ОДНОЙ указанной страницы комментов (их бывает несколько страниц)
	time.sleep(0.21)  # Пауза 0.21сек. Важно! При запросах чаще чем 5 раз в секунду, ЖЖ забанит ваш IP
	ljtime = int(time.time()) * 1000 + random.randint(100, 999) + 1
	url = 'https://{ljname}.livejournal.com/{ljname}/__rpc_get_thread?journal={ljname}&itemid={postid}&flat=&skip=&media=&page={page}&expand_all=1&_={time}'.format(ljname=ljname, postid=postid, page=page, time=ljtime)
	shorturl = url.split('.livejournal.com', 1)[1]
	httpheaders = { 'GET': shorturl,
					'Host': '{}.livejournal.com'.format(ljname),
					'Connection': 'keep-alive',
					'Accept': 'application/json, text/javascript, */*; q=0.01',
					'DNT': '1',
					'X-Requested-With': 'XMLHttpRequest',
					'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/69.0.3497.100 Safari/537.36',
					'Referer': 'https://{ljname}.livejournal.com/{postid}.html?page={page}'.format(ljname=ljname, postid=postid, page=page),
					'Accept-Encoding': 'gzip, deflate, br',
					'Accept-Language': 'ru,en-US;q=0.9,en;q=0.8'}
	respnse = requests.get(url, headers=httpheaders)
	jsondata = respnse.json()
	return jsondata


def getcomments(soup: BeautifulSoup) -> dict:
	# получает все комменты к ОДНОМУ посту. Если страниц с комментариями несколько - обходит их и собирает со всех
	jsoncomments = json.loads('{"comments":[]}')
	jsondata = extractjson(soup)
	ljname = jsondata.get('entry')['journal'].replace('_', '-')
	postid = jsondata.get('entry')['ditemid']
	title = jsondata.get('entry')['title']
	if not soup.find('li', class_='b-xylem-cell-amount') or not jsondata['replycount']:
		print('{} {} / pages: 1 / comments: 0'.format(postid, title))
		return jsoncomments
	pagelist = soup.find('ul', class_='b-pager-pages')
	if pagelist:
		pages = pagelist.find_all('li', class_='b-pager-page')
	else:
		pages = ['1']
	print(
		'{} {} / pages: {} / comments: {}'.format(postid, title, len(pages), jsondata['replycount']))
	jsoncomments = loadcommentspage(ljname, postid, 1)
	if len(pages) > 1:
		for page in range(2, len(pages) + 1):
			jsoncomments['comments'] += loadcommentspage(ljname, postid, page)['comments']
	return jsoncomments


def dwnldljpost(url: str, nav: dict, forced: bool):
	#  парсинг страницы отдельного поста
	#  -----------------------------------
	#  получить исходный код поста
	#  получить комментарии
	#  получить тэги
	#  извлечь статью + очистить от лишних тегов и картинок
	#  создать (если нужно) структуру каталогов для сохранения
	#  скачать картинки из статьи + обновить ссылки ни картинки
	#  скачать картинки из коммен + обновить ссылки ни картинки
	#  скачать юзерпики из статьи + обновить ссылки ни картинки
	#  скачать юзерпики из коммен + обновить ссылки ни картинки
	#
	filename = '{ljname}/raw/{postid}'.format(ljname=extractljname(url), postid=extractpostid(url))
	if (not forced) and checkfileexist(filename + '.raw'):
		return
	soup = getsoup(url)
	jsondata = extractjson(soup)
	jsondata['entry']['url'] = url
	jsondata['entry']['nav'] = nav
	jsondata['comments'] = getcomments(soup)['comments']
	savetofile(jsondata, filename + '.raw.json')
	savetofile(soup    , filename + '.raw')


def safeget(lst: list, index: int, valueiferror=None):
	if 0 <= index < len(lst):
		return lst[index]
	else:
		return valueiferror


def getljnavigation(posts: list, index: int) -> dict:
	nav = dict()
	curr = safeget(posts, index    , None)
	next = safeget(posts, index - 1, None)
	prev = safeget(posts, index + 1, None)
	url   = lambda s: '' if not s else s.split(' ', 1)[0]
	title = lambda s: '' if not s else s.split(' ', 1)[1]
	nav['url']       = url(curr)
	nav['title']     = title(curr)
	nav['next']      = url(next)
	nav['nexttitle'] = title(next)
	nav['prev']      = url(prev)
	nav['prevtitle'] = title(prev)
	return nav


def dwnldljposts(ljname: str, skip=None or int, maxcount=None or int, loadwithoutnav=False, forced=bool):
	title('donwload raw posts & comments')
	posts = loadfromfile('{0}/calendar/_{0}_.txt'.format(ljname), lines=True)
	for i in range(len(posts)):
		if skip and i < skip:
			continue
		if maxcount and i >= maxcount:
			return
		nav = getljnavigation(posts, i)
		url = posts[i].split(' ')[0]
		if loadwithoutnav or (nav['prev'] and nav['next']):
			dwnldljpost(url, nav, forced)


def getljmonth(ljname: str, year: int, month: int, forceupdate: bool) -> list:
	filename = '{}/calendar/{:04}.{:02}.txt'.format(ljname, year, month)
	if (not forceupdate) and checkfileexist(filename):
		posts = loadfromfile(filename, True)
	else:
		posts = list()
		url = 'https://{}.livejournal.com/{:04}/{:02}'.format(ljname, year, month)
		print(url)
		soup = getsoup(url)
		entry = soup.find('div', class_='entry-text')
		for dd in entry.find_all('dd'):
			for a in dd.find_all('a', href=True):
				posts.append('{} {}'.format(a['href'], a.text.strip()))
		posts = posts[::-1]
		savetofile('\n'.join(posts), filename)
	return posts


def getljcontent(ljname: str, minyear=2013, minmonth=1) -> list:
	title('get content list')
	minyear = max(minyear, 2011)
	now = datetime.datetime.now()
	year = now.year
	month = now.month
	posts = list()
	i = 0
	while year >= minyear and month >= minmonth:
		i += 1
		posts += getljmonth(ljname, year, month, i <= 2)
		month -= 1
		if not month:
			year -= 1
			month = 12
	savetofile('\n'.join(posts), '{0}/calendar/_{0}_.txt'.format(ljname))
	print('-'*40)
	print('{} - найдено постов: {}'.format(ljname, len(posts)))
	return posts


def main():
	# скачивает указанный ЖЖ, двигаясь от новых постов к старым
	ljname = 'evo-lutio'
	maxcount = 5
	overwrite_existing = True

	getljcontent(ljname=ljname, minyear=2013, minmonth=1)
	dwnldljposts(ljname=ljname, skip=None, maxcount=maxcount, loadwithoutnav=True, forced=overwrite_existing)


# МОДУЛЬ 1      lj


if __name__ == '__main__':
	main()
