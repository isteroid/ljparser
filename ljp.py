import json
import requests
import mimetypes
from bs4 import BeautifulSoup
import lj
import os
from shutil import copyfile
from ftplib import FTP
import sys

def xprint(obj, title =''):
	t = type(obj)
	if title:
		print('--- {}/{} ---'.format(title, t.__name__))
	if t == list:
		for key, value in enumerate(obj):
			print('[{}] {}'.format(key, value))
	elif t == dict:
		print('')
		for key, value in obj.items():
			print('[{}] {}'.format(key, value))
	else:
		print(t)


def gettags(soup):
	tags = []
	ljtags = soup.find('div', class_='ljtags')
	if ljtags:
		links = ljtags.find_all('a', href=True)
		for a in links:
			tags.append(a.text)
	return tags


def findextension(rqst, detectextension: bool) -> str:
	ext = ''
	url = str(rqst)
	if not detectextension:
		return ''
	if type(rqst) == requests.Response:
		url = rqst.url
		contenttype = rqst.headers.get('content-type')
		if contenttype:
			ext = mimetypes.guess_extension(contenttype)
	if not ext:
		ext = url.split('?')[0].split('.')[-1]
	ext = ext.lower()
	ext = ext if ext in ['.png', '.gif', '.svg', '.bmp'] else '.jpg'
	return ext


def download(url, filename, detectextension=False):
	lj.checkpath(filename)  # проверка существования целевой папки
	ext = findextension(url, detectextension)
	if lj.checkfileexist(filename + ext):
		return filename + ext
	try:
		rqst = requests.get(url)
	except:
		try:
			rqst = requests.get(url, verify=False)
		except:
			lj.savetofile(url + ' ' + filename + '\n', 'loaderror.log', 'a')
			return ''
	filename += findextension(rqst, detectextension)
	if not lj.checkfileexist(filename):
		with open(filename, 'wb') as file:
			print(filename + ' <- ' + url)
			file.write(rqst.content)
	return filename


def extractfilenamefromurl(url: str, extonly=False) -> str:
	filename = ('/'+url+'?').split('?', 1)[0].split('/')[-1].lower()
	ext = ('.' + filename).split('.')[-1]
	ext = 'jpg' if ext in ['jpeg','jpe','jpg'] else ext
	ext = ext if ext in ['png', 'gif', 'svg', 'bmp', 'jpg'] else ''
	if extonly:
		return ext
	return filename


def loadimagesa(ljname: str, postid: str, article: BeautifulSoup) -> BeautifulSoup:
	images = article.find_all('img', src=True)
	k = 0
	for img in images:
		url = img['src']
		if '/userinfo' in url:
			filename = '{}/images/pic/'.format(ljname) + url.split('?',1)[0].split('/')[-1]
			filename = filename.split('.')[-2]
		else:
			k += 1
			filename = '{}/images/{}-{:03}'.format(ljname, postid, k)
		ext = extractfilenamefromurl(url, extonly=True)
		if ext:
			filename += '.' + ext
		filename = download(url, filename, not ext)
		if filename:
			img['src'] = '../' + filename.split('/',1)[1]
	return article


def loadimagesc(ljname: str, postid: str, comments: json) -> json:
	for comment in comments:
		if comment.get('article'):
			k = 0
			article = comment['article']
			dtalkid = comment['dtalkid']
			soup = BeautifulSoup(article, features='html.parser')
			images = soup.find_all('img', src=True)
			for img in images:
				k += 1
				url = img['src']
				filename = '{}/images/comments/{}-{}-{:03}'.format(ljname, postid, dtalkid, k)
				ext = extractfilenamefromurl(url, extonly=True)
				if ext:
					filename += '.' + ext
				filename = download(url, filename, not ext)
				if filename:
					img['src'] = '../' + filename.split('/', 1)[1]
			comment['article'] = soup.prettify()
	return comments


def loaduserpics(ljname, postid, comments):
	for comment in comments:
		filename = ''
		url = comment.get('userpic')
		user = comment.get('uname')
		uname = user.replace('_', '-') if user else 'z-user'
		suffx = url.split('/')[-2] if url else '000'
		filename += '{}/images/userpics/{}-{}.jpg'.format(ljname,uname,suffx)
		if url:
			filename = download(url, filename)
			if filename:
				comment['userpic'] = '../' + filename.split('/', 1)[1]
	return comments


def contentstosoup(contents):
	return BeautifulSoup(''.join(map(str, contents)), features='html.parser')


def striptags(soup, goodtags=('a', 'img', 'br', 'b')):
	for tag in soup.find_all(True):
		if tag and (tag.name not in goodtags):
			tag.replaceWith(striptags(contentstosoup(tag.contents)))
	return soup


def removeattrs(soup: BeautifulSoup, goodattrs=('src', 'href', 'alt', 'title')) -> BeautifulSoup:
	for tag in soup.find_all(True):
		if tag.attrs:
			for attr in list(tag.attrs):
				if attr not in goodattrs:
					del tag.attrs[attr]
	return soup


def cleanarticle(soup: BeautifulSoup) -> BeautifulSoup:
	soup.attrs = None
	soup = removeattrs(soup)
	soup = striptags(soup)
	# dellist = soup.find_all('img', src=re.compile(r'l-stat.livejournal.net/img/userinfo'))
	# for delobj in dellist:
	# 	delobj.decompose()
	# dellist = soup.find_all('a', href=re.compile(r'livejournal.com/profile'), text=False)
	# for delobj in dellist:
	# 	delobj.decompose()
	badlinks = [None, 'https://t.me/evo_lutio', 'https://facebook.com/psychoalchemy.ru/', 'https://www.youtube.com/channel/UCjl7ABlrO8mrtdNabYGb9bQ', 'https://www.instagram.com/evo_lutio/', 'https://vk.com/psychoalchemy', 'https://twitter.com/evo_lutio']
	dellist = soup.find_all('a', href=badlinks)
	for delobj in dellist:
		delobj.decompose()
	return soup


def parseljpost(url, forced: bool):
	postid = lj.extractpostid(url)
	ljname = lj.extractljname(url)
	filename = '{}/raw/{}.raw'.format(ljname, postid)
	if not forced and lj.checkfileexist('{}/data/{}.htm.json'.format(ljname, postid)):
		return
	if lj.checkfileexist(filename):
		soup = BeautifulSoup(lj.loadfromfile(filename), features='html.parser')
		jsondata = json.loads(lj.loadfromfile(filename + '.json'))
		jsondata['entry']['tags'] = gettags(soup)
		jsondata['entry']['ljname'] = ljname
		article = cleanarticle(soup.find('article', class_='entry-content'))
		lj.savetofile(article.prettify(), '{}/data/{}.htm'.format(ljname, postid))
		article = loadimagesa(ljname, postid, article)
		jsondata['comments'] = loadimagesc(ljname, postid, jsondata['comments'])
		jsondata['comments'] = loaduserpics(ljname, postid, jsondata['comments'])
		lj.savetofile(jsondata, '{}/data/{}.htm.json'.format(ljname, postid))
		lj.savetofile(article.prettify(), '{}/data/{}.htm'.format(ljname, postid))


def testdata(ljname: str):
	lj.title('testing')
	dir = '{}/raw/'.format(ljname)
	posts = lj.loadfromfile('{0}/calendar/_{0}_.txt'.format(ljname), True)
	postsids = list(map(lj.extractpostid, posts))
	for file in os.listdir(dir):
		if file.endswith('.json'):
			postid = int(file.split('.',1)[0])
			filename = dir + file
			jsondata = json.loads(lj.loadfromfile(filename))
			nav = jsondata['entry']['nav']
			if len(nav['prev']) < 5 or len(nav['next']) < 5:
				print('{} * {} * {}'.format(nav['prev'], postid, nav['next']))
				if str(postid) in postsids:
					nav = lj.getljnavigation(posts, postsids.index(str(postid)))
					if len(nav['next']) > 5 or len(nav['prev']) > 5:
						jsondata['entry']['nav'] = nav
						lj.savetofile(jsondata, filename, 'w')
						print('Навигация успешно исправлена: {} {} {}'.format(postid, nav['prev'], nav['next']))
					else:
						print('Не удалось исправить навигацию: {}'.format(postid))
				else:
					print('Пост {} отсутствует в списке постов. Обновите список постов!'.format(postid))


def processing(ljname: str, skip=None or int, maxcount=None or int, forced=False):
	lj.title('processing raw -- to --> data')
	filename = '{0}/calendar/_{0}_.txt'.format(ljname)
	if lj.checkfileexist(filename):
		posts = lj.loadfromfile(filename, lines=True)
		for post in posts[skip:maxcount]:
			print(post)
			url = post.split(' ', 1)[0]
			parseljpost(url, forced)
		print('-'*40)
		print(len(posts))


def copyallfiles(files: list, dir1: str, dir2: str, forced: bool):
	lj.checkpath(dir1)
	lj.checkpath(dir2)
	for file in files:
		if forced or (not lj.checkfileexist(dir2 + file)):
			print('{} -> {}'.format(dir1 + file, dir2 + file))
			copyfile(dir1 + file, dir2 + file)


def getallfilesinfolder(root: str) -> list:
	lst = list()
	for path, subdirs, files in os.walk(root):
		for name in files:
			lst.append(os.path.join(path, name))
	return lst


def ftptransfer(files: list, localdir: str, uploaddir: str, force: bool):
	with FTP(host='jvladdi.beget.tech') as ftp:
		print(ftp.login(user='jvladdi_evolutio', passwd='EvolutioFtpPassword0707'))
		ftpfiles = ftp.nlst(uploaddir)
		for filename in files:
			if uploaddir + filename in ftpfiles:
				if force:
					print('REWRITE ', end='')
					# ftp.delete(uploaddir + filename)
				else:
					print(uploaddir + filename + '  is already exist on FTP')
					continue
			print('UPLOAD ' + localdir + filename + ' -> ' + uploaddir + filename)
			with open(localdir + filename, 'rb') as file:
				ftp.storbinary('STOR ' + uploaddir + filename, file)


def makeupdate(ljname: str, count: int):
	if not count:
		return
	lj.title('make web update')
	dir = lambda ljname, dir: '{ljname}/{dir}'.format(ljname=ljname, dir=dir)
	udir = lambda ljname, dir: '{ljname}/_update_/{dir}'.format(ljname=ljname, dir=dir if ljname not in dir else dir.repl(ljname, ljname+'/_update_', 1))
	# lj.checkpath(udir(ljname,'data/'))
	# lj.checkpath(udir(ljname,'images/userpics/'))
	# lj.checkpath(udir(ljname,'images/comments/'))
	posts = lj.loadfromfile('{0}/calendar/_{0}_.txt'.format(ljname), True)[:count+1]
	files = list()
	upics = list()
	ids = list()
	for post in posts:
		postid = lj.extractpostid(post)
		ids.append(postid)
		jsondata = json.loads(lj.loadfromfile('{dir}/{postid}.htm.json'.format(dir=dir(ljname, 'data'), postid=postid)))
		for comment in jsondata['comments']:
			filename = comment.get('userpic')
			if filename:
				filename = filename.split('/')[-1]
				if filename not in upics:
					upics.append(filename)
		files += [postid + '.htm', postid + '.htm.json']
	print(len(upics))
	imgext = ['.jpg', '.png', '.gif', '.svg']
	images = [file for file in os.listdir(dir(ljname, 'images/')) if file.endswith(tuple(imgext))]
	images = [file for file in images if file.split('-', 1)[0] in ids]
	cimages = [file for file in os.listdir(dir(ljname, 'images/comments/')) if file.endswith(tuple(imgext))]
	cimages = [file for file in cimages if file.split('-', 1)[0] in ids]
	# copyallfiles(files, dir(ljname, 'data/'), udir(ljname, 'data/'), True)
	# copyallfiles(images, dir(ljname, 'images/'), udir(ljname, 'images/'), False)
	# copyallfiles(upics, dir(ljname, 'images/userpics/'), udir(ljname, 'images/userpics/'), False)
	# print('creating update is complete!')
	lj.title('uploading data to ftp...')
	ftptransfer(files,  dir(ljname, 'data/'), 'data/', True)
	lj.title('uploading images to ftp...')
	ftptransfer(images, dir(ljname, 'images/'), 'images/', False)
	lj.title('uploading userpics to ftp...')
	ftptransfer(cimages, dir(ljname, 'images/comments/'), 'images/comments/', False)
	lj.title('uploading comment images to ftp...')
	ftptransfer(upics,  dir(ljname, 'images/userpics/'), 'images/userpics/', False)
	ftptransfer(['_{}_.txt'.format(ljname)], dir(ljname, 'calendar/'), 'calendar/', True)
	print('uploading is complete!')


def main():
	print(sys.version)
	ljname = 'evo-lutio'
	maxcount = 20
	forced_download = True
	forced_processing = True

	lj.getljcontent(ljname=ljname, minyear=2013, minmonth=1)
	print('downloading posts')
	lj.dwnldljposts(ljname=ljname, skip=None, maxcount=maxcount, loadwithoutnav=True, forced=forced_download)
	# testdata(ljname)
	processing(ljname=ljname, skip=None, maxcount=maxcount, forced=forced_processing)  # скачать картинки и обработать raw
	makeupdate(ljname, maxcount)
	# ftptransfer('evo-lutio/_update_/', '')


# МОДУЛЬ 2    ljp

if __name__ == '__main__':
	main()
