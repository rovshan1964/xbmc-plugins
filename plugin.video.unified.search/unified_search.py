import sys
import json
import urllib
import re

import xbmc
import xbmcplugin
import xbmcgui
import xbmcaddon

import XbmcHelpers
common = XbmcHelpers

import Translit as translit
translit = translit.Translit()

counter = 0


# xbmc.sleep( 500 ) => http://xbmc-scripting.googlecode.com/svn/trunk/SVNScripts_argv/

class UnifiedSearch():
    def __init__(self):
        self.id = 'plugin.video.unified.search'
        self.addon = xbmcaddon.Addon(self.id)
        self.icon = self.addon.getAddonInfo('icon')
        self.path = self.addon.getAddonInfo('path')
        self.profile = self.addon.getAddonInfo('profile')

        self.xpath = sys.argv[0]
        self.handle = int(sys.argv[1])
        self.params = sys.argv[2]

        self.language = self.addon.getLocalizedString
        self.supported_addons = self.get_supported_addons()
        self.debug = True

        self.counter = self.addon.getSetting("counter")

    def main(self):
        # self.log("Addon: %s"  % self.id)
        # self.log("Handle: %d" % self.handle)
        # self.log("Params: %s" % self.params)

        params = common.getParameters(self.params)
        mode = params['mode'] if 'mode' in params else None
        keyword = params['keyword'] if 'keyword' in params else None

        url = params['url'] if 'url' in params else None
        plugin = params['plugin'] if 'plugin' in params else None

        if mode == 'search':
            self.search(keyword)
        if mode == 'results':
            self.results()
        if mode == 'reset':
            self.resetResults()
        if mode == 'activatewindow':
            self.activatewindow(plugin, url)
        elif mode is None:
            self.menu()

    def menu(self):
        self.log("Supported add-ons: %s" % self.supported_addons)

        uri = self.xpath + '?mode=%s' % "search"
        item = xbmcgui.ListItem("[COLOR=FF00FF00]%s[/COLOR]" % self.language(1000), thumbnailImage=self.icon)
        xbmcplugin.addDirectoryItem(self.handle, uri, item, True)

        item = xbmcgui.ListItem("[COLOR=FF00FFF0]%s[/COLOR]" % self.language(1001), thumbnailImage=self.icon)
        xbmcplugin.addDirectoryItem(self.handle, self.xpath + '?mode=reset', item, False)

        xbmcplugin.endOfDirectory(self.handle, True)


    def getUserInput(self):
        kbd = xbmc.Keyboard()
        kbd.setDefault('')
        kbd.setHeading(self.language(4000))
        kbd.doModal()
        keyword = None

        if kbd.isConfirmed():
            keyword = kbd.getText()

        return keyword

    def search(self, keyword):
        self.resetResults()

        keyword = self.getUserInput()
        #keyword = "Persi"

        if keyword:
            self.log("Call other add-ons and pass keyword: %s" % keyword)

            keyword = translit.eng(keyword) if self.isCyrillic(keyword) else keyword

            # Send keyword to supported add-ons
            for i, plugin in enumerate(self.supported_addons):
                script = "special://home/addons/%s/default.py" % plugin
                xbmc.executebuiltin("XBMC.RunScript(%s, %d, mode=search&keyword=%s&unified=True)" % (script, self.handle, keyword), True)


                # xbmc.executescript("%s?mode=search&keyword=%s&unified=True" % (script, keyword))
                #subprocess.Popen([script_player_starts,self.playing_type()])
                #XBMC.RunScript(script.rssclient,feed=FEED_URL,limit=15)


        # xbmc.executebuiltin('Container.SetViewMode(50)')
        # xbmcplugin.endOfDirectory(self.handle, True)

    def results(self):
        self.log("Show results on separate page")

        results = self.getSearchResults()

        if results:
            for i, item in enumerate(results):
                uri = '%s?mode=activatewindow&plugin=%s&url=%s' % (self.xpath, item['plugin'], item['url'])
                item = xbmcgui.ListItem("%s (%s)" % (item['title'], item['plugin'].replace('plugin.video.', '')), thumbnailImage=item['image'])
                xbmcplugin.addDirectoryItem(self.handle, uri, item, False)
        else:
            item = xbmcgui.ListItem("[COLOR=FFFF4000]%s[/COLOR]" % self.language(1002))
            item.setProperty('IsPlayable', 'false')
            xbmcplugin.addDirectoryItem(self.handle, '', item, False)

        xbmcplugin.endOfDirectory(self.handle, True)

    def activatewindow(self, plugin, url):
        self.log("%s => %s" % (plugin, url))

        window = "plugin://%s/?mode=show&url=%s" % (plugin, url)
        xbmc.executebuiltin('activatewindow(video, %s)' % window)

    def getSearchResults(self):
        self.log("Get search results from storage")

        try:
            results = json.loads(self.addon.getSetting("results"))
            return results
        except ValueError:
            return []

    def collect(self, results):
        self.log("*** Collect results and activate window")

        counter = int(self.addon.getSetting("counter"))
        counter +=1

        self.addon.setSetting("counter", str(counter))

        if results:
            print "Counter: %s" % self.addon.getSetting("counter")

            saved = json.loads(self.addon.getSetting("results")) #self.getSearchResults()
            print "*** Saved %d " % len(saved)

            for result in results:
                try:
                    if not result['url'] in map(lambda item: item['url'], saved):
                        saved.append(result)
                        self.addon.setSetting("results", json.dumps(saved))
                except Exception, e:
                    self.error(e)
        else:
            self.log("Not found")

        xbmc.sleep(1000)

        if len(self.supported_addons) == counter:
            print "All done"

            plugin = "plugin://%s/?mode=results" % (self.id)
            xbmc.executebuiltin('XBMC.ReplaceWindow(10025, %s, return)' % plugin)

        else:
            print "Supported len %d " % len(self.supported_addons)
            print "Counter %d" % counter
            print "Wait and do nothing"
            return True

    def resetResults(self):
        self.addon.setSetting("counter", '0')
        self.addon.setSetting("results", '[]')
        xbmc.executebuiltin("Container.refresh()")

    # === HELPERS
    def get_supported_addons(self):
        request = '{"jsonrpc": "2.0", "method": "Addons.GetAddons", "params": {"properties": ["summary"]}, "id": 1}'

        response = json.loads(xbmc.executeJSONRPC(request))["result"]["addons"]
        supported = []

        for i, addon in enumerate(response):
            try:
                if not 'pvr' in addon["addonid"] and xbmcaddon.Addon(addon["addonid"]).getSetting('unified_search') == 'true':
                    supported.append(addon["addonid"])
            except RuntimeError:
                pass

        return supported

    def log(self, message):
        if self.debug:
            print "000 %s: %s" % (self.id, message)

    def error(self, message):
        print "%s ERROR: %s" % (self.id, message)

    def isCyrillic(self, keyword):
        if not re.findall(u"[\u0400-\u0500]+", keyword):
            return False
        else:
            return True
