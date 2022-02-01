import re
import urllib
import sublime
import sublime_plugin


CACHE = "CsoundDocs.sublime-settings"


class CsoundDocs(sublime_plugin.ViewEventListener):

	SYNTAX_FILE = "Csound.sublime-syntax"
	SELECTOR = "support.function.csound"
	BASE_URL = "http://www.csounds.com/manual/html/"

	@classmethod
	def is_applicable(cls, settings):
		return settings.get('syntax') == cls.SYNTAX_FILE

	def on_selection_modified_async(self):

		#only trigger on 2 column view
		if not self.view.window().num_groups() == 2:
			return


		#get selected function
		point = self.view.sel()[0].begin() #get the cursor position

		if not self.view.match_selector(point, self.SELECTOR): #ensure the selection is a function
			return

		func = self.view.substr(self.view.word(point)) #get the function to look up


		#display the page
		focusedGroup = self.view.window().active_group() #save the selected group

		#check the cache
		cache = sublime.load_settings(CACHE)
		page = cache.get(func, None)

		#download the page
		if page == None:

			#grab the page
			link = "{}{}.html".format(self.BASE_URL, func)
			try:
				req = urllib.request.Request(link, headers={'User-Agent' : "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:70.0) Gecko/20100101 Firefox/70.0"})
				con = urllib.request.urlopen(req)
				page = con.read().decode()
			except urllib.error.HTTPError:
				return #epic fail

			#wrangle the page
			page = re.sub(r"<\?xml.*?>", "", page) #remove <xml> tag
			page = re.sub(r"<!DOCTYPE.*?>", "", page) #remove <!DOCTYPE> tag
			page = re.sub(r"<head>.*</head>", "", page, flags=re.DOTALL) #remove <head> tag
			page = re.sub(r"<div[^>]*?navheader.*?</div>", "", page, flags=re.DOTALL) #remove the top nav links
			page = re.sub(r"<div[^>]*?navfooter.*?</div>", "", page, flags=re.DOTALL) #and bottom nav links
			page = page.replace("</pre>", "</pre><br>") #add a <br> after each <pre> (cause minihtml doesn't support pre)
			page = re.sub(r"<pre.*?</pre>", lambda match: match.group(0).replace("\n", "<br>\n"), page, flags=re.DOTALL) #add a <br> after each newline in a <pre>
			page = re.sub(r"<table.*?</table>", "<i>*** Table Removed (Sublime doesn't support html tables) ***</i>", page, flags=re.DOTALL)

			#add links
			page = re.sub(r"<a([^>]*?)href=\"(.*?)\"([^>].*?)>", "<a\\1href=\"{}\\2\"\\3>".format(self.BASE_URL), page) #make in-page links work
			page = re.sub(r"(<span class=\"refentrytitle\">.*?</span>)", "<a href=\"{}\">\\1</a>".format(link), page) #add a link to the title

			#update cache
			cache.set(func, page)
			sublime.save_settings(CACHE)


		#inject css
		page = page.replace("<body>", "<body>\n<style>\n{}\n</style>".format(sublime.load_resource(sublime.find_resources("csound.css")[0])))

		#display the page
		self.view.window().new_html_sheet(func, page, sublime.TRANSIENT, 1)
		self.view.window().focus_group(focusedGroup)



class ClearCsoundCacheCommand(sublime_plugin.ApplicationCommand):

	def run(self):

		cache = sublime.load_settings(CACHE)

		for key in cache.to_dict():
			cache.set(key, None) #don't use cache.erase because that just comments the lines out (which takes up storage space) so set each one to None

		sublime.save_settings(CACHE)


def plugin_loaded():

	CsoundDocs.SYNTAX_FILE = sublime.find_resources(CsoundDocs.SYNTAX_FILE)[0] #Can't call sublime.find_resources at import time
