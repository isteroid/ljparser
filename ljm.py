import json
from bs4 import BeautifulSoup
import lj
import ljp
import time


def makepost(url):
	csstime = int(time.time())
	postid = lj.extractpostid(url)
	ljname = lj.extractljname(url)
	filename = '{}/data/{}.htm'.format(ljname, postid)
	if lj.checkfileexist(filename):
		article = BeautifulSoup(lj.loadfromfile(filename), features='html.parser')
		jsondata = json.loads(lj.loadfromfile(filename + '.json'))
		template = lj.loadfromfile('_post_templ.html').split('~')
		templateblocks = {'ulopen': template[2], 'comment': template[3], 'ulclose': template[4]}
		entry = jsondata['entry']
		nav = entry['nav']
		next = lj.extractpostid(nav['next'])
		prev = lj.extractpostid(nav['prev'])
		fields = {'title': entry['title'], 'article': article, 'prev': prev, 'prevtitle': nav['prevtitle'], 'next': next, 'nexttitle': nav['nexttitle'], 'postid': entry['ditemid'], 'ljname': entry['ljname'], 'time': csstime}
		html = template[0].format(**fields)
		comments = jsondata['comments']
		cids = dict()
		currentlevel = 0
		for comment in comments:
			parent = comment.get('parent', None)
			dtalkid = comment.get('dtalkid')
			if dtalkid:
				dtalkid = str(dtalkid)
				if not parent:
					comment['level'] = 0
				else:
					parent = str(parent)
					comment['level'] = cids[parent] + 1
				cids[dtalkid] = comment['level']
				cssclass = 'author' if comment['uname'] == jsondata['entry']['journal'] else ''
				cfields = {'level': comment['level'], 'userpic': comment.get('userpic'), 'user': comment['uname'], 'article': comment.get('article'), 'class': cssclass, 'userlj': comment.get('commenter_journal_base')}
				delta = comment['level'] - currentlevel
				if delta:
					tag = templateblocks['ulopen'] if delta > 0 else templateblocks['ulclose']
					html += tag * abs(delta)
				html += templateblocks['comment'].format(**cfields)
				currentlevel = comment['level']
			else:
				print('Читать комменты: ' + url)
				lj.savetofile('{} {}\n'.format(url, entry['title']), '{0}/calendar/_collapsed_.txt'.format(ljname), 'a')  # add comment error to file
		html += template[1].format(**fields)
		html = html.replace('href="https://{}.livejournal.com/'.format(ljname), 'href="')
		html = html.replace('href="http://{}.livejournal.com/'.format(ljname), 'href="')
		lj.savetofile(html, '{}/post/{}.html'.format(ljname, postid))


def makeindex(ljname, posts):
	lj.title('generate html index')
	csstime = int(time.time())
	template = lj.loadfromfile('_index_templ.html').split('~')
	templateblocks = {'start':template[0], 'ok': template[1], 'none': template[2], 'end': template[3]}
	fields = {'ljname': ljname, 'time': csstime}
	html = templateblocks['start'].format(**fields)
	for item in posts:
		post = item.split(' ', 1)
		url = post[0]
		title = post[1]
		postid = lj.extractpostid(url)
		block = 'ok' if lj.checkfileexist('{}/post/{}.html'.format(ljname, postid)) else 'none'
		html += templateblocks[block].format(postid=postid, title=title)
	html += templateblocks['end']
	lj.savetofile(html, '{}/index.html'.format(ljname))


def compare2versions():
	ljname = 'evo-lutio'
	filename1 = '{0}/calendar/_{0}_.txt'.format(ljname)
	filename2 = '{0}/calendar/_compare_.txt'.format(ljname)
	f1 = set(lj.loadfromfile(filename1, lines=True))
	f2 = set(lj.loadfromfile(filename2, lines=True))
	print('now: {}'.format(len(f1)))
	print('bef: {}'.format(len(f2)))
	print('now-bef: {}'.format(len(f1-f2)))
	print('bef-now: {}'.format(len(f2-f2)))
	print('now-bef')
	print(list(f1-f2))
	print('bef-now')
	print(list(f2-f1))


def uniqfilelines(filename, sort=False):
	lst = lj.loadfromfile(filename, True)
	lst = list(set(lst))
	lst = [l for l in lst if l]
	if sort:
		lst.sort(reverse=True, key=lambda url: int(lj.extractpostid(url)))
	lj.savetofile('\n'.join(lst), filename + '_u_.txt')


def makehtml(ljname: str, skip=None, maxcount=None, mkposts=True, mkindex=True):
	# генерирует html контент на основе обработанных данных
	lj.title('generate posts .htmls')
	filename = '{0}/calendar/_{0}_.txt'.format(ljname)
	lj.savetofile('', '{0}/calendar/_collapsed_.txt'.format(ljname), 'w')  # clear comment errors file
	if lj.checkfileexist(filename):
		posts = lj.loadfromfile(filename, lines=True)
		if mkposts:
			for post in posts[skip:maxcount]:
				print(post)
				url = post.split(' ', 1)[0]
				makepost(url)
		if mkindex:
			makeindex(ljname, posts)
	uniqfilelines('{0}/calendar/_collapsed_.txt'.format(ljname), sort=True)


def main():

	ljname = 'evo-lutio'   # собственно, имя журнала
	blogstartyear = 2013   # Год   (включительно) глубины просмотра СПИСКА постов. Рекмендуется до конца блога. Скачивание идет от новых постов к старым.
	blogstartmonth = 1     # Месяц (включительно) глубины просмотра.

	# --- Этапы обработки (вкл / выкл) --- первые буквы переменной означают имя модуля, в котором содержится код соотетствующей обработки
	lj_load_posts_list = True             # 1  Скачать список постов блога (можно всегда True - повторно не скачивает)
	lj_load_raw_post_and_comments = True  # 2  Скачать посты и комментарии, без обработки (можно всегда True - повторно не скачивает), кроме первого и последнего, у них нет навигации вперед-назад (опционально)
	ljp_parse_raw_and_load_images = True  # 3  Скачать картинки и обработь данные (повторно не качает, но проверка скачано/не скачано и обработка данных занимают время)
	ljm_make_html_pages = False           # 4  Создать html-страницы из каждого ОБРАБОТАННОГО поста
	ljm_make_content_page = False         # 5  Создать содержание (список постов)

	# --- Опции ---
	load_raw_without_nav = False # Скачивать данные для постов, у которых нет следующего или предыдущего. Нужно для скачивания журнала по частым. Устанавливаем True, когда качаем реально первый и реально последний пост журнала.
	skip_n_posts = None   # Пропустить    N постов (None or int)
	do_only_n_posts = 20  # Обраб. только N постов (None or int)
	forced_processing = False  # Обрабатывать и перезаписывать файл, если уже найден результирующий файл обработки поста

	# Непосредственно ВЫЗОВЫ функций в зависимости от настроек и опций
	if lj_load_posts_list:
		lj.getljcontent(ljname=ljname, minyear=blogstartyear, minmonth=blogstartmonth)
	if lj_load_raw_post_and_comments:
		lj.dwnldljposts(ljname=ljname, skip=skip_n_posts, maxcount=do_only_n_posts, loadwithoutnav=load_raw_without_nav)
	ljp.testdata(ljname)
	if ljp_parse_raw_and_load_images:
		ljp.processing(ljname=ljname, skip=skip_n_posts, maxcount=do_only_n_posts, forced=forced_processing)
	if ljm_make_html_pages or ljm_make_content_page:
		makehtml(ljname=ljname, skip=skip_n_posts, maxcount=do_only_n_posts, mkposts=ljm_make_html_pages, mkindex=ljm_make_content_page)


#  МОДУЛЬ 3     ljm    СВОДНЫЙ


if __name__ == '__main__':
	main()
