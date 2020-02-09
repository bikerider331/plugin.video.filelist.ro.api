# -*- coding: utf-8 -*-
# Module: default
# Author: Dark1
# Created on: 12.01.2020
# License: GPL v.3 https://www.gnu.org/copyleft/gpl.html

import sys
from urllib import urlencode
from urlparse import parse_qsl
import xbmcgui
import xbmcplugin
import xbmcaddon
import xbmc
import json
import urllib
import os
import xbmcvfs
import time
import flprovider 
import categories
import base64
import simplecache
import datetime

ACTION_WATCH_WITH_ELEMENTUM = "0"
ACTION_SAVE_TO_PATH = "1"

CACHE_LABEL_TORRENTS_BY_ID = "filelist.ro.api_cached_torrents_by_id"
CACHE_LABEL_TORRENTS = "filelist.ro.api_cached_torrents"
CACHE_EXPIRATION_HOURS = 1

class Indexer:
    def __init__(self):
        xbmc.log("__init__")
        # Get the plugin url in plugin:// notation.
        self._url = sys.argv[0]
        # Get the plugin handle as an integer number.
        self._handle = int(sys.argv[1])
        self.cache = simplecache.SimpleCache()

        self.addon = xbmcaddon.Addon()
        self.addonRootPath = self.addon.getAddonInfo('path').decode('utf-8')
        self.dataPath = xbmc.translatePath(xbmcaddon.Addon().getAddonInfo(('profile'))).decode('utf-8')
        
        #settings
        self.username=self.addon.getSetting('filelist.user')
        self.passkey=self.addon.getSetting('filelist.passphrase')
        self.watchDir=self.addon.getSetting('saveTorrentFolder')
        self.torrentAction=self.addon.getSetting('torrentAction')
        self.tmdb_api_key=self.addon.getSetting('tmdb_api_key')
        self.metaDataAvailable = False
        self.pageSize = 10
        if self.tmdb_api_key:
            print("tmdb_api_key: "+self.tmdb_api_key)
            from movieinfo import MovieInfoProvider
            self.movieInfoProvider = MovieInfoProvider(self.tmdb_api_key)
            self.metaDataAvailable = True
        self.FLTorrentProvider = flprovider.FLTorrentProvider(self.username, self.passkey)
        self.categories = categories.Categories(self.addonRootPath)

    def get_url(self, **kwargs):
        """
        Create a URL for calling the plugin recursively from the given set of keyword arguments.

        :param kwargs: "argument=value" pairs
        :type kwargs: dict
        :return: plugin call URL
        :rtype: str
        """
        return '{0}?{1}'.format(self._url, urlencode(kwargs))

    def list_categories(self):
        """
        Create the list of video categories in the Kodi interface.
        """
        if (self.username == '' or self.passkey == ''):
                return xbmc.executebuiltin('Addon.OpenSettings(%s)' % xbmcaddon.Addon().getAddonInfo('id'))
        # Set plugin category. It is displayed in some skins as the name
        # of the current section.
        xbmcplugin.setPluginCategory(self._handle, 'FilList.ro')
        xbmcplugin.setContent(self._handle, 'videos')

        list_item = xbmcgui.ListItem(label="Search")
        # Create a URL for a plugin recursive call.
        # Example: plugin://plugin.video.example/?action=listing&category=Animals
        url = self.get_url(action='search')
        # is_folder = True means that this item opens a sub-list of lower level items.
        is_folder = True
        # Add our item to the Kodi virtual folder listing.
        xbmcplugin.addDirectoryItem(self._handle, url, list_item, is_folder)

        allCategories = self.categories.getCategories()
        # Iterate through categories
        for category in allCategories:
            if (self.showCategory(category)):
                self.addCategoryItem(category, category['name'], 'listing')
        # Finish creating a virtual folder.
        xbmcplugin.endOfDirectory(self._handle)

    def addCategoryItem(self, category, labelValue, actionValue):
        # Create a list item with a text label and a thumbnail image.
        list_item = xbmcgui.ListItem(label=labelValue)
        # Set graphics (thumbnail, fanart, banner, poster, landscape etc.) for the list item.
        # Here we use the same image for all items for simplicity's sake.
        # In a real-life plugin you need to set each image accordingly.
        categoryThumb = self.addonRootPath+"/resources/media/"+str(category['id'])+"-image.png"
        categoryFanart = self.addonRootPath+"/resources/media/"+str(category['id'])+"-fanart.png"
        
        list_item.setArt({'thumb': categoryThumb,
                        'icon': categoryThumb})
        # Set additional info for the list item.
        # Here we use a category name for both properties for for simplicity's sake.
        # setInfo allows to set various information for an item.
        # For available properties see the following link:
        # https://codedocs.xyz/xbmc/xbmc/group__python__xbmcgui__listitem.html#ga0b71166869bda87ad744942888fb5f14
        # 'mediatype' is needed for a skin to display info for this ListItem correctly.
        list_item.setInfo('video', {'title': category['name'],
                                    'genre': category['name'],
                                    'mediatype': 'video'})
        # Create a URL for a plugin recursive call.
        # Example: plugin://plugin.video.example/?action=listing&category=Animals
        url = self.get_url(action=actionValue, categoryId=category['id'])
        # is_folder = True means that this item opens a sub-list of lower level items.
        is_folder = True
        # Add our item to the Kodi virtual folder listing.
        xbmcplugin.addDirectoryItem(self._handle, url, list_item, is_folder)    


    def showCategory(self, category):
        switcher = {
           "video": xbmcaddon.Addon().getSettingBool('show_video'),
           "audio": xbmcaddon.Addon().getSettingBool('show_audio'),
           "software": xbmcaddon.Addon().getSettingBool('show_software'),
           "docs": xbmcaddon.Addon().getSettingBool('show_docs'),
           "misc": xbmcaddon.Addon().getSettingBool('show_misc'),
           "xxx": xbmcaddon.Addon().getSettingBool('show_xxx'),
        }
        categoryType = category['type']
        result = switcher.get(categoryType, lambda: False)
        return result
     

    def list_torrents(self, categoryId, startIndex):
        category = self.categories.getCategoryById(int(categoryId))

        xbmcplugin.setPluginCategory(self._handle, category['name'])
        xbmcplugin.setContent(self._handle, 'videos')
        
        torrents = []
        if not startIndex:
            startIndex = 0
            self.addCategoryItem(category, "Search "+category['name'], 'search')
            torrents = self.FLTorrentProvider.getLatestTorrentsByCategoryID(category['id'])
        else:
            torrents = self.cache.get(CACHE_LABEL_TORRENTS)

        self.cacheTorrents(torrents)

        self.show_torrents(categoryId, torrents, startIndex)
        
    def cacheTorrents(self, torrents):
        torrentsById = {}
        for torrent in torrents:
            id = torrent['id']
            torrentsById[id] = torrent
        self.cache.set(CACHE_LABEL_TORRENTS_BY_ID,torrentsById, expiration=datetime.timedelta(hours=CACHE_EXPIRATION_HOURS))
        self.cache.set(CACHE_LABEL_TORRENTS,torrents, expiration=datetime.timedelta(hours=CACHE_EXPIRATION_HOURS))

    def show_torrents(self, categoryId, torrents, startIndex): 
        startIndex = int(startIndex)
        addNextPageItem = True
        endIndex = startIndex + self.pageSize
        
        if len(torrents) < endIndex:
            endIndex = len(torrents)
            addNextPageItem = False

        totalItems = 1 + endIndex - startIndex
        for index in range(startIndex, endIndex):
            torrent = torrents[index]
            
            # Create a list item with a text label and a thumbnail image.
            list_item = xbmcgui.ListItem(label=torrent['name'])
            # Set additional info for the list item.
            # 'mediatype' is needed for skin to display info for this ListItem correctly.
            list_item.setInfo('video', {'title': torrent['name'],
                                        'genre': torrent['small_description'],
                                        'imdbnumber': torrent['imdb'], 
                                        'mediatype': 'video'})
            # Set graphics (thumbnail, fanart, banner, poster, landscape etc.) for the list item.
            # Here we use the same image for all items for simplicity's sake.
            # In a real-life plugin you need to set each image accordingly.
            category = self.categories.getCategoryByName(torrent['category'])
            categoryThumb = self.addonRootPath+"/resources/media/"+str(category['id'])+"-image.png"
            categoryFanart =  self.addonRootPath+"/resources/media/"+str(category['id'])+"-fanart.png"

            artData = {}
            artData['icon'] = categoryThumb
            if self.metaDataAvailable:
                if 'imdb' in torrent:
                    xbmc.log("IMDB ID available: "+str(torrent['imdb']))
                    metadata = self.movieInfoProvider.getMovieInfo(imdbID=torrent['imdb'])
                    if metadata:
                        if 'poster_path' in metadata:
                            posterFullPath = self.movieInfoProvider.getPosterFullPath(metadata['poster_path'])
                            if posterFullPath:
                                xbmc.log("Found poster: "+str(posterFullPath))
                                artData['poster'] = posterFullPath
                        if 'backdrop_path' in metadata:
                            fanartFullPath = self.movieInfoProvider.getBackdropFullPath(metadata['backdrop_path'])
                            if fanartFullPath:
                                xbmc.log("Found fanart: "+str(fanartFullPath))
                                artData['fanart'] = fanartFullPath
            list_item.setArt(artData)
            
            #list_item.setArt({'thumb': video['thumb'], 'icon': video['thumb'], 'fanart': video['thumb']})
            # Set 'IsPlayable' property to 'true'.
            # This is mandatory for playable items!
            list_item.setProperty('IsPlayable', 'true')
            url = self.get_url(action='play', torrent=torrent['id'])
            # Add the list item to a virtual Kodi folder.
            # is_folder = False means that this item won't open any sub-list.
            is_folder = False
            # Add our item to the Kodi virtual folder listing.
            xbmcplugin.addDirectoryItem(self._handle, url, list_item, is_folder, totalItems = totalItems)
        
        if addNextPageItem:
            #item for the next page
            list_item = xbmcgui.ListItem(label='Next..')
            url = self.get_url(action='listing', startIndex=endIndex, categoryId=categoryId)
            is_folder = True
            xbmcplugin.addDirectoryItem(self._handle, url, list_item, is_folder)
        # Finish creating a virtual folder.
        xbmcplugin.endOfDirectory(self._handle)

        

    def play_video(self, torrentId):
        torrentsById = self.cache.get(CACHE_LABEL_TORRENTS_BY_ID)
        print("TorrentsById: "+str(torrentsById))
        torrent = torrentsById[int(torrentId)]

        saveDir = self.dataPath
        if self.torrentAction == ACTION_SAVE_TO_PATH and self.watchDir:
            saveDir = self.watchDir

        torrentPath = self.FLTorrentProvider.downloadTorrent(torrent, saveDir)

        torrentPathUrl = urllib.quote_plus(torrentPath)
        
        if self.torrentAction == ACTION_SAVE_TO_PATH:
            dialog = xbmcgui.Dialog()
            ok = dialog.ok('FileList.ro', 'Torrent saved.')

        if self.torrentAction == ACTION_WATCH_WITH_ELEMENTUM:

            link = 'plugin://plugin.video.elementum/play?uri=%s' % torrentPathUrl
            
            # Create a playable item with a path to play.
            play_item = xbmcgui.ListItem(path=link)
            # Pass the item to the Kodi player.
            xbmcplugin.setResolvedUrl(self._handle, True, listitem=play_item)
        
    def startSearch(self, categoryId = None):
        kb = xbmc.Keyboard('default', 'Name', True)
        kb.setDefault("")
        kb.setHiddenInput(False)
        kb.doModal()
        if (kb.isConfirmed()):
            text  = kb.getText()
            filtered_text = urllib.quote_plus(text)
            torrents = self.FLTorrentProvider.searchTorrents("name", filtered_text, categoryId)
            if len(torrents) > 0:
                if type(torrents) is dict:
                    if 'error' in torrents.keys():
                        dialog = xbmcgui.Dialog()
                        ok = dialog.ok('Error', torrents['error'])
                else:
                    # Set plugin category. It is displayed in some skins as the name
                    # of the current section.
                    xbmcplugin.setPluginCategory(self._handle, "Search results")
                    # Set plugin content. It allows Kodi to select appropriate views
                    # for this type of content.
                    xbmcplugin.setContent(self._handle, 'videos')
                    # Get the list of videos in the category.
                    self.show_torrents(torrents)
            else:
                dialog = xbmcgui.Dialog()
                ok = dialog.ok('Error', 'There was an error.')


    def router(self, paramstring):
        """
        Router function that calls other functions
        depending on the provided paramstring

        :param paramstring: URL encoded plugin paramstring
        :type paramstring: str
        """
        # Parse a URL-encoded paramstring to the dictionary of
        # {<parameter>: <value>} elements
        params = dict(parse_qsl(paramstring))
        # Check the parameters passed to the plugin
        if params:
            if params['action'] == 'listing':
                if 'startIndex' in params:
                    print("Start index: "+params['startIndex'])
                    self.list_torrents(params['categoryId'], params['startIndex'])
                else:
                    self.list_torrents(params['categoryId'], None)
            elif params['action'] == 'search':
                if 'categoryId' in params:
                    self.startSearch(params['categoryId'])
                else:
                    self.startSearch()
            elif params['action'] == 'play':
                # Play a video from a provided URL.
                self.play_video(params['torrent'])
            else:
                # If the provided paramstring does not contain a supported action
                # we raise an exception. This helps to catch coding errors,
                # e.g. typos in action names.
                raise ValueError('Invalid paramstring: {0}!'.format(paramstring))
        else:
            # If the plugin is called from Kodi UI without any parameters,
            # display the list of video categories
            self.list_categories()


if __name__ == '__main__':
    # Call the router function and pass the plugin call parameters to it.
    # We use string slicing to trim the leading '?' from the plugin call paramstring
    indexer = Indexer()
    indexer.router(sys.argv[2][1:])
