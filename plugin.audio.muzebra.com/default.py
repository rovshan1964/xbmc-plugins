#!/usr/bin/python
# Writer (c) 2012, MrStealth
# Rev. 2.2.1
# -*- coding: utf-8 -*-

import os, sys, urllib, urllib2, cookielib
import xbmc, xbmcplugin,xbmcgui,xbmcaddon
import json, HTMLParser, XbmcHelpers
import Translit as translit

import time
from datetime import datetime

translit = translit.Translit()
common = XbmcHelpers

class Muzebra():
  def __init__(self):
    self.id = 'plugin.audio.muzebra.com'
    self.addon = xbmcaddon.Addon(self.id)
    self.icon = self.addon.getAddonInfo('icon')
    self.path = self.addon.getAddonInfo('path')
    self.profile = self.addon.getAddonInfo('profile')

    self.language = self.addon.getLocalizedString
    self.handle = int(sys.argv[1])
    self.url = 'http://muzebra.com'

    self.playlists_url = 'http://muzebra.com/user/playlist'

    self.username = self.addon.getSetting('username') if self.addon.getSetting('username') else None
    self.password = self.addon.getSetting('password') if self.addon.getSetting('password') else None

    # TODO: set expiry date and remove file if cookie expired
    self.cookie_file = os.path.join(xbmc.translatePath(self.profile), 'cookie.txt')
    self.cookie = cookielib.LWPCookieJar()

    self.authenticated = False
    self.api_keys = self.getAPIkey()


  def main(self):
    params = common.getParameters(sys.argv[2])
    mode = url = playlist = None
    #title = artist = playlist = language = None

    mode = params['mode'] if params.has_key('mode') else None
    url = urllib.unquote_plus(params['url']) if params.has_key('url') else None
    #url = params['url'] if params.has_key('url') else None

    playlist = params['playlist'] if params.has_key('playlist') else 'Unknown'
    artists = params['artists'] if params.has_key('artists') else 'Unknown'
    lang = params['lang'] if params.has_key('lang') else None
    page = params['page'] if params.has_key('page') else 1

    dataid = params['dataid'] if params.has_key('dataid') else None
    datalink = params['datalink'] if params.has_key('datalink') else None

    if mode == 'play':
      self.play(dataid, datalink)
    if mode == 'search':
      self.search()
    if mode == 'songs':
      self.getSongs(url)
    if mode == 'add':
      self.addToPlaylist(url)
    if mode == 'playlists':
      self.showPlaylists()
    if mode == 'artists':
      self.listArtists(url)
    if mode == 'radio':
      self.listStations(url)
    if mode == 'alphabet':
        self.alphabet(url, lang)
    elif mode == None:
      self.menu()


  def menu(self):
    if self.addon.getSetting('authentication') == 'true': self.login()

    uri = sys.argv[0] + '?mode=%s'%('search')
    item = xbmcgui.ListItem('[COLOR=FF00FF00][%s][/COLOR]'%self.language(1000), iconImage=self.icon)
    xbmcplugin.addDirectoryItem(self.handle, uri, item, True)

    print "*** Authenticated user? %s"%self.authenticated

    if self.authenticated:
      uri = sys.argv[0] + '?mode=%s'%('playlists')
      item = xbmcgui.ListItem("[COLOR=FF00FFF0]%s (muzebra.com)[/COLOR]"%self.language(2000), iconImage=self.icon)
      xbmcplugin.addDirectoryItem(self.handle, uri, item, True)

    uri = sys.argv[0] + '?mode=%s&url=%s&playlist=%s'%('songs', 'http://muzebra.com/charts/russian', self.language(4001))
    item = xbmcgui.ListItem(self.language(4001), iconImage=self.icon)
    xbmcplugin.addDirectoryItem(self.handle, uri, item, True)

    uri = sys.argv[0] + '?mode=%s&url=%s&playlist=%s'%('songs', 'http://muzebra.com/charts/worldwide', self.language(4002))
    item = xbmcgui.ListItem(self.language(4002), iconImage=self.icon)
    xbmcplugin.addDirectoryItem(self.handle, uri, item, True)

    uri = sys.argv[0] + '?mode=%s&url=%s'%('radio', 'http://muzebra.com/radio/')
    item = xbmcgui.ListItem(self.language(3001), iconImage=self.icon)
    xbmcplugin.addDirectoryItem(self.handle, uri, item, True)

    uri = sys.argv[0] + '?mode=%s&url=%s'%('radio', 'http://muzebra.com/radio/spb/')
    item = xbmcgui.ListItem(self.language(3002), iconImage=self.icon)
    xbmcplugin.addDirectoryItem(self.handle, uri, item, True)

    uri = sys.argv[0] + '?mode=%s&url=%s&lang=%s'%('alphabet', 'http://muzebra.com/artists/', 'ru')
    item = xbmcgui.ListItem(self.language(5001), iconImage=self.icon)
    xbmcplugin.addDirectoryItem(self.handle, uri, item, True)

    uri = sys.argv[0] + '?mode=%s&url=%s&lang=%s'%('alphabet', 'http://muzebra.com/artists/', 'en')
    item = xbmcgui.ListItem(self.language(5002), iconImage=self.icon)
    xbmcplugin.addDirectoryItem(self.handle, uri, item, True)

    xbmcplugin.endOfDirectory(self.handle, True)


  def showPlaylists(self):
    print "*** Show playlists"
    playlists = self.getPlaylists()

    for name, pid in playlists.items():
      uri = sys.argv[0] + '?mode=%s&url=%s&playlist=%s'%('songs', urllib.quote_plus("http://muzebra.com/playlist/%s/"%pid), name)
      item = xbmcgui.ListItem(name, iconImage=self.icon)
      xbmcplugin.addDirectoryItem(self.handle, uri, item, True)

    xbmcplugin.endOfDirectory(self.handle, True)


  def getPlaylists(self):
    print "*** GET PLAYLISTS"
    self.login()

    page = common.fetchPage({"link": self.playlists_url})
    content = common.parseDOM(page["content"], "div", attrs = { "id":"content" })
    hashes = common.parseDOM(content, "a", attrs = { "class":"hash" })[:-1]
    pids = common.parseDOM(content, "li", ret = "data-id")[:-1]

    playlists = {}

    for i, name in enumerate(hashes):
      playlists[name] = pids[i]

    return playlists


  def addToPlaylist(self, song):
    print "*** add to playlist"
    playlists = self.getPlaylists()

    names = []
    pids = []

    for name,pid in playlists.items():
      names.append(name)
      pids.append(pid)

    selected = xbmcgui.Dialog().select('Choose a playlist', names)

    url = "http://muzebra.com/user/song/addSongs"

    data = urllib.urlencode({
        "isExistName" : "true",
        "pl_name" : pids[selected],
        "songs[]" : song
    })

    headers = {
        "Accept" : "application/json, text/javascript, */*; q=0.01",
        "Accept-Encoding": "gzip,deflate",
        "Accept-Language" : "de-de,de;q=0.8,en-us;q=0.5,en;q=0.3",
        "Cache-Control" : "no-cache",
        "Connection" : "keep-alive",
        "Content-Type" : "application/x-www-form-urlencoded",
        "Host" : "muzebra.com",
        "Referer" : 'http://muzebra.com/charts/',
        "User-Agent" : "Mozilla/5.0 (X11; Linux x86_64; rv:17.0) Gecko/17.0 Firefox/17.0",
        "X-Requested-With" : "XMLHttpRequest"
    }

    req = urllib2.Request(url, data, headers)
    handle = urllib2.urlopen(req)

    if handle.code == 200:
      self.showSuccessMessage('Song was successfully added to %s playlist'%names[selected])
    else:
      self.showErrorMessage('Adding song to playlist %s failed'%names[selected])

  def getSongs(self, url):
    print "*** GET SONGS FOR PLAYLIST %s" % url

    page = common.fetchPage({"link": url})
    content = common.parseDOM(page["content"], "div", attrs={"id": "content"})

    playlists = common.parseDOM(content, "ul", attrs={"class": "white playlist"})

    if not playlists:
      playlists = common.parseDOM(content, "ul", attrs={"class": "playlist"})

      if not playlists:
        playlists = common.parseDOM(content, "ul")

    artists = common.parseDOM(playlists, "li", attrs={"class": "track"}, ret="data-artist")
    titles = common.parseDOM(playlists, "li", attrs={"class": "track"}, ret="data-title")

    dataids = common.parseDOM(playlists, "li", attrs={"class": "track"}, ret="data-aid")
    datalinks = common.parseDOM(playlists, "li", attrs = {"class": "track"}, ret="data-link")

    durations = common.parseDOM(playlists, "li", attrs = {"class": "track"}, ret="data-duration")

    image = self.getArtistPhoto(page["content"])

    for i, title in enumerate(titles):
      title = self.stripHtmlEntitites(common.stripTags(title))

      try:
        artist = self.stripHtmlEntitites(common.stripTags(artists[i]))
      except IndexError:
        artist = "unknown"

      song = "%s - %s" % (title, artist)

      uri = sys.argv[0] + '?mode=%s&dataid=%s&datalink=%s'%('play', dataids[i], datalinks[i])
      item = xbmcgui.ListItem(self.stripHtmlEntitites(song), iconImage=self.icon, thumbnailImage=image)

      item.setInfo(type='music',
        infoLabels = {
          'title': title,
          'artist': artist,
          'album': 'N/A',
          'genre': 'muzebra.com',
          'duration': durations[i],
          'rating' : '0'
        }
      )

      script = os.path.join(xbmc.translatePath(self.path), 'downloader.py')
      params = "%s|%s"%(datalinks[i], song)

      runner1 = "XBMC.RunScript(" + str(script)+ ", " + params + ")"
      runner2 = "XBMC.RunPlugin(plugin://plugin.audio.muzebra.com/" + "?mode=add&url=" + datalinks[i] + ")"

      item.addContextMenuItems([(self.language(8001), runner1), (self.language(2001), runner2)])

      item.setProperty('IsPlayable', 'true')
      xbmcplugin.addDirectoryItem(self.handle, uri, item, False)

    self.showMore(url, content)
    xbmcplugin.endOfDirectory(self.handle, True)


  def getSongByID(self, dataid, datalink):
    print "DataID: %s DataLink: %s " % (dataid, datalink)
    api = "https://api.vk.com/method/audio.getById.json?access_token=%s&audios=%s"%(self.api_keys['token'], dataid)

    try:
      print "*** try to get the song from api.vk.com"
      response = json.loads(common.fetchPage({"link": api})["content"])['response'][0]
      return {'url' : response['url'], 'title' : response['title'], 'artist' : response['artist']}
    except (KeyError, IndexError) as e:
      print "*** try to get the song from savestreaming.com"
      return {'url' : 'http://savestreaming.com/t/%s_%s'%(datalink, self.api_keys['hash'])}


  def getArtistPhoto(self, content):
    photo = common.parseDOM(content, "img", attrs = { "class":"artist_image" }, ret="src")
    return photo[0] if photo else self.icon


  def listArtists(self, url):
    print "*** list artists %s"%url

    #url = urllib.quote(url)

    page = common.fetchPage({"link": url})

    if page["status"] == 200:
        artists = common.parseDOM(page["content"], "ul", attrs = { "class":"artists span6" })
        links = common.parseDOM(artists, "a", attrs = { "class":"hash" }, ret="href")
        titles = common.parseDOM(artists, "a")

        for i, link in enumerate(links):
          title = titles[i].upper().replace('%26', 'and').encode('utf-8')

          print title
          print link
          uri = sys.argv[0] + '?mode=%s&url=%s&playlist=%s'%('songs', urllib.quote_plus(self.url+link), title)

          item = xbmcgui.ListItem(title, iconImage = self.icon, thumbnailImage = self.icon)
          xbmcplugin.addDirectoryItem(self.handle, uri, item, isFolder=True)

    # xbmcplugin.addSortMethod(self.handle, xbmcplugin.SORT_METHOD_TITLE)
    # xbmcplugin.addSortMethod( handle=self.handle, sortMethod=xbmcplugin.SORT_METHOD_TITLE )
    xbmcplugin.endOfDirectory(self.handle, True)


  def listStations(self, url):
    print "*** list stations %s"%url
    page = common.fetchPage({"link": url})

    if page["status"] == 200:
        stations = common.parseDOM(page["content"], "ul", attrs = { "class":"stations" })
        thumbs = common.parseDOM(stations, "div", attrs = { "class":"thumb" })

        images = common.parseDOM(thumbs, "img", ret="src")
        links = common.parseDOM(thumbs, "a", attrs = { "class":"hash" }, ret="href")
        titles = common.parseDOM(thumbs, "img", ret="alt")

        for i, link in enumerate(links):
          title = titles[i].upper()
          uri = sys.argv[0] + '?mode=%s&url=%s&playlist=%s'%('songs', urllib.quote_plus(self.url+link), title)

          item = xbmcgui.ListItem(title, iconImage = self.url+images[i])
          xbmcplugin.addDirectoryItem(self.handle, uri, item, isFolder=True)

    xbmcplugin.endOfDirectory(self.handle, True)


  def alphabet(self, url, lang):
    page = common.fetchPage({"link": url})

    print "*** get alphabet %s"%url

    if page["status"] == 200:
      if lang == 'ru':
        letters = common.parseDOM(page["content"], "ul", attrs = { "class":"ru clearfix" })
      else:
        letters = common.parseDOM(page["content"], "ul", attrs = { "class":"en clearfix" })

      links = common.parseDOM(letters, "a", attrs = { "class":"hash" }, ret="href")
      titles = common.parseDOM(letters, "a")

      if lang == 'ru':
        links.insert(1, '/artists/%D0%B0/')
        titles.insert(1, 'A')

      for i, link in enumerate(links):
        link = link.encode('utf-8')
        url = urllib.quote_plus(self.url + link)

        uri = sys.argv[0] + '?mode=artists'
        uri += '&url='  + url
        title = titles[i]

        item = xbmcgui.ListItem(title.upper(), iconImage = self.icon, thumbnailImage = self.icon)
        xbmcplugin.addDirectoryItem(self.handle, uri, item, isFolder=True)

    xbmcplugin.endOfDirectory(self.handle, True)


  def showMore(self, url, content):
    pagination = common.parseDOM(content, "div", attrs = { "class":"pagination" })

    if pagination:
      title = common.parseDOM(content, "a", attrs = {"class": "stat"})[0]
      link = common.parseDOM(content, "a", ret="href", attrs = {"class": "stat"})[0]

      if url.find('page') == -1:
        url = url.replace(' ', '+') + '&page=2'
      else:
        page = int(url.split('=')[-1])
        url = url[:-1]+str(page+1)

      uri = sys.argv[0] + '?mode=%s&url=%s'%('songs', urllib.quote_plus(url))
      item = xbmcgui.ListItem('[COLOR=FF00FFF0]%s[/COLOR]'%title, iconImage = self.icon, thumbnailImage = self.icon)
      xbmcplugin.addDirectoryItem(self.handle, uri, item, isFolder=True)


  def play(self, dataid, datalink):
    song = self.getSongByID(dataid, datalink)
    item = xbmcgui.ListItem(path = song['url'], iconImage=self.icon)

    #item.setInfo(type='music', infoLabels = {'title': song['title'], 'artist' : song['artist'] })
    item.setProperty('mimetype', 'audio/mpeg')
    xbmcplugin.setResolvedUrl(self.handle, True, item)


  def duration(self, time):
    duration = time.split(':')
    return int(duration[0]) * 60 + int(duration[1])


  #  get API key for savestreaming.com
  def getAPIkey(self):
    url = 'http://muzebra.com/service/playerparams/'

    headers = {
     "Accept" : "application/json, text/javascript, */*; q=0.01",
     "Accept-Language" : "de-de,de;q=0.8,en-us;q=0.5,en;q=0.3",
     "Accept-Charset" : "ISO-8859-1,utf-8;q=0.7,*;q=0.3",
     "DNT" : "1",
     "Host" : "muzebra.com",
     "Origin" : "http://muzebra.com",
     "Referer" : "http://muzebra.com/",
     "User-Agent" : "Mozilla/5.0 (X11; Linux x86_64; rv:15.0) Gecko/20100101 Firefox/15.0",
     "X-Requested-With" : "XMLHttpRequest"
    }

    try:
      request = urllib2.Request(url, urllib.urlencode({}), headers)
      response = json.loads(urllib2.urlopen(request).read())
      return {'token' : response['token'], 'hash' : response['hash']}

    except  urllib2.URLError, e:
      if hasattr(e, 'reason'):
        self.showErrorMessage('We failed to reach a muzebra.com server %s'%e.reason)
      elif hasattr(e, 'code'):
        print 'The server couldn\'t fulfill the request.'
        self.showErrorMessage('The server couldn\'t fulfill the request. %s'%e.code)


  def search(self):
    query = common.getUserInput(self.language(1000), "")

    if query:
      if self.addon.getSetting('translit') == 'true':
        print "Module translit enabled"

        try:
            keyword = translit.rus(query).encode('utf-8','ignore')
        except Exception, e:
            keyword = translit.rus(query)
      else:
        keyword = query

      url =self.url + '/search/?q=' +  urllib.quote_plus(keyword.replace(' ', '+'))
      self.getSongs(url)

    else:
      print "Empty query"


  # login to muzebra.com
  def login(self):
    print "*** Login to muzebra.com"

    if self.username is None or self.password is None or self.username is '' or self.password is '':
        self.authenticated = False
        print "Username and password missing, continue"
        return False
    else:
      if self.checkCookieFile(self.cookie_file):
        try:
            cj = cookielib.MozillaCookieJar()
            cj.load(self.cookie_file)
            opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
            urllib2.install_opener(opener)
            self.authenticated = True
            return True
        except cookielib.LoadError:
            print "*** remove existing cookie file and try again"
            os.remove(self.cookie_file)


      else:
        print "*** Cookie file not found, get cookies from server\n"

        cj = cookielib.MozillaCookieJar()
        opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
        urllib2.install_opener(opener)

        url = "http://muzebra.com/user/login"

        values = {
            "UserLogin[password]" : self.password,
            "UserLogin[rememberMe]" : "1",
            "UserLogin[username]" : self.username,
            "yt0":"%D0%92%D1%85%D0%BE%D0%B4"
        }

        request = urllib2.Request(url, urllib.urlencode(values))
        request.add_header('Accept', 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8')
        request.add_header('Accept-Encoding', 'gzip,deflate')
        request.add_header('Accept-Language', 'de-de,de;q=0.8,en-us;q=0.5,en;q=0.3')
        request.add_header('Connection', 'keep-alive')
        request.add_header('Content-Type', 'application/x-www-form-urlencoded')
        request.add_header('Host', 'muzebra.com')
        request.add_header('Referer', 'http://muzebra.com/user/playlist')
        request.add_header('User-Agent', 'Mozilla/5.0 (X11; Linux x86_64; rv:17.0) Gecko/17.0 Firefox/17.0')

        try:
            response =  urllib2.urlopen(request)
        except  urllib2.URLError, e:
            if hasattr(e, 'reason'):
                print 'We failed to reach a server.'
                print 'Reason: ', e.reason
            elif hasattr(e, 'code'):
                print 'The server couldn\'t fulfill the request.'
                print 'Error code: ', e.code

        response = urllib2.urlopen(request)

        if response.geturl() == "http://muzebra.com/user/profile":
          self.authenticated = True
          print "save cookies"
          cj.save(self.cookie_file)
          return True
        else:
          print "*** Authentication failed"
          print response.geturl()
          return False


  def checkCookieFile(self, cookie):
    if os.path.isfile(cookie):
      print "Cookie file found"

      if (time.mktime(datetime.now().timetuple()) - os.path.getmtime(cookie)) > 86400:
        print "Remove cookie file and get new one from server"
        os.remove(cookie)
        return False
      else:
        print "Cookie file is up-to-date"
        return True
    else:
      return False

    #print "Cookie file created at: %s" % datetime.fromtimestamp(os.path.getmtime(cookie))


  def showErrorMessage(self, msg):
    print msg
    xbmc.executebuiltin("XBMC.Notification(%s,%s, %s)"%("ERROR",msg, str(10*1000)))

  def showSuccessMessage(self, msg):
    print msg
    xbmc.executebuiltin("XBMC.Notification(%s,%s, %s)"%("SUCCESS",msg, str(5*1000)))

  def encode(self, string):
    return string.decode('cp1251').encode('utf-8')

  def stripHtmlEntitites(self, string):
    return HTMLParser.HTMLParser().unescape(string)

muzebra = Muzebra()
muzebra.main()
