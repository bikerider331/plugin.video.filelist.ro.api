# -*- coding: utf-8 -*-
# Module: default
# Author: Dark1
# Created on: 12.01.2020
# License: GPL v.3 https://www.gnu.org/copyleft/gpl.html

import sys
from urllib.parse import urlencode, parse_qsl, quote_plus
import xbmcgui
import xbmcplugin
import xbmcaddon
import xbmc
import json
import urllib
import os
import xbmcvfs
import time
import flclient 
import categories
import base64
import simplecache
import datetime

CACHE_LABEL_TORRENTS_BY_ID = "filelist.io.api_cached_torrents_by_id"
CACHE_LABEL_TORRENTS = "filelist.io.api_cached_torrents"
CACHE_EXPIRATION_HOURS = 1


class Indexer:
    def __init__(self, url: str, handle: int):
        # Get the plugin url in plugin:// notation.
        self._url = url

        # Get the plugin handle as an integer number.
        self._handle = handle

        self.cache = simplecache.SimpleCache()
        self.addon = xbmcaddon.Addon()
        self.addonRootPath = self.addon.getAddonInfo('path')
        self.dataPath = xbmcvfs.translatePath(xbmcaddon.Addon().getAddonInfo(('profile')))
        
        # settings
        self.username = self.addon.getSetting('filelist.user')
        self.passkey = self.addon.getSetting('filelist.passphrase')
        self.tmdb_api_key = self.addon.getSetting('tmdb_api_key')
        self.omdb_api_key = self.addon.getSetting('omdb_api_key')

        self.movie_info_providers = []
        self.page_size = 8

        if self.tmdb_api_key:
            from tmdbinfo import TMDBInfoProvider
            self.movie_info_providers.append(TMDBInfoProvider(self.tmdb_api_key))
        
        if self.omdb_api_key:
            from omdbinfo import OMDBInfoProvider
            self.movie_info_providers.append(OMDBInfoProvider(self.omdb_api_key))

        self.filelist_api = flclient.FilelistClient(self.username, self.passkey)
        self.categories = categories.Categories(self.addonRootPath)
        xbmc.log("Indexer init successfully")

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
        if self.username == '' or self.passkey == '':
            return xbmc.executebuiltin('Addon.OpenSettings(%s)' % xbmcaddon.Addon().getAddonInfo('id'))

        # Set plugin category. It is displayed in some skins as the name of the current section.
        xbmcplugin.setPluginCategory(self._handle, 'FileList.io')
        xbmcplugin.setContent(self._handle, 'videos')

        list_item = xbmcgui.ListItem(label="Search")
        
        # Create a URL for a plugin recursive call.
        # Example: plugin://plugin.video.example/?action=listing&category=Animals
        url = self.get_url(action='search')

        # Add our item to the Kodi virtual folder listing.
        xbmcplugin.addDirectoryItem(self._handle, url, list_item, isFolder=True)

        all_categories = self.categories.get_categories()

        # Iterate through categories
        for category in all_categories:
            if self.show_category(category):
                self.add_category_item(category, category['name'], 'listing')

        # Finish creating a virtual folder.
        xbmcplugin.endOfDirectory(self._handle)

    def add_category_item(self, category, label, action):
        # Create a list item with a text label and a thumbnail image.
        list_item = xbmcgui.ListItem(label=label)

        # Set graphics (thumbnail, fanart, banner, poster, landscape etc.) for the list item.
        # Here we use the same image for all items for simplicity's sake.
        # In a real-life plugin you need to set each image accordingly.
        categoryThumb = self.addonRootPath + "/resources/media/" + str(category['id']) + "-image.png"
        categoryFanart = self.addonRootPath + "/resources/media/" + str(category['id']) + "-fanart.png"
        
        list_item.setArt({'thumb': categoryThumb,
                          'fanart': categoryFanart,
                          'icon': categoryThumb})

        # Set additional info for the list item.
        # Here we use a category name for both properties for simplicity's sake.
        # setInfo allows to set various information for an item.
        # For available properties see the following link:
        # https://codedocs.xyz/xbmc/xbmc/group__python__xbmcgui__listitem.html#ga0b71166869bda87ad744942888fb5f14
        # 'mediatype' is needed for a skin to display info for this ListItem correctly.
        list_item.setInfo('video', {'title': category['name'],
                                    'genre': category['name'],
                                    'mediatype': 'video'})

        # Create a URL for a plugin recursive call.
        # Example: plugin://plugin.video.example/?action=listing&category=Animals
        url = self.get_url(action=action, category_id=category['id'])
        
        # Add our item to the Kodi virtual folder listing.
        xbmcplugin.addDirectoryItem(self._handle, url, list_item, isFolder=True)    


    def show_category(self, category):
        switcher = {
           "video": xbmcaddon.Addon().getSettingBool('show_video'),
           "audio": xbmcaddon.Addon().getSettingBool('show_audio'),
           "software": xbmcaddon.Addon().getSettingBool('show_software'),
           "docs": xbmcaddon.Addon().getSettingBool('show_docs'),
           "misc": xbmcaddon.Addon().getSettingBool('show_misc'),
           "xxx": xbmcaddon.Addon().getSettingBool('show_xxx'),
        }
        categoryType = category['type']
        result = switcher.get(categoryType, False)
        return result
     

    def list_torrents(self, category_id, start_index):
        category = self.categories.get_category_by_id(category_id)

        xbmcplugin.setPluginCategory(self._handle, category['name'])
        xbmcplugin.setContent(self._handle, 'videos')
        
        if not start_index:
            start_index = 0
            self.add_category_item(category, "Search " + category['name'], 'search')
            torrents = self.filelist_api.get_latest_torrents_by_category_id(category['id'])
        else:
            torrents = self.cache.get('%s.%s' % (CACHE_LABEL_TORRENTS, category_id))

        self.show_torrents(category_id, torrents, start_index)
        
    def cache_torrents(self, torrents, category_id):
        xbmc.log("Caching %d torrents of %s" % (len(torrents), category_id))

        if not torrents:
            return

        torrentsById = {}

        for torrent in torrents:
            id = torrent['id']
            torrentsById[id] = torrent

        self.cache.set('%s.%s' % (CACHE_LABEL_TORRENTS_BY_ID, category_id),
                        torrentsById,
                        expiration=datetime.timedelta(hours=CACHE_EXPIRATION_HOURS))

        self.cache.set('%s.%s' % (CACHE_LABEL_TORRENTS, category_id),
                        torrents,
                        expiration=datetime.timedelta(hours=CACHE_EXPIRATION_HOURS))

    def show_torrents(self, category_id, torrents, start_index, paged=True):
        self.cache_torrents(torrents, category_id)

        addNextPageItem = True
        end_index = start_index + self.page_size
        
        if len(torrents) < end_index:
            end_index = len(torrents)
            addNextPageItem = False

        if not paged:
            addNextPageItem = False
            end_index = len(torrents) 

        totalItems = 1 + end_index - start_index

        for index in range(start_index, end_index):
            torrent = torrents[index]

            xbmc.log("Adding torrent to view: " + str(torrent))
            
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
            category = self.categories.get_category_by_name(torrent['category'])
            categoryThumb = self.addonRootPath + "/resources/media/" + str(category['id']) + "-image.png"
            categoryFanart =  self.addonRootPath + "/resources/media/" + str(category['id']) + "-fanart.png"

            artData = {}
            artData['icon'] = categoryThumb

            if 'imdb' in torrent:
                xbmc.log("IMDB ID available: " + str(torrent['imdb']))

                for provider in self.movie_info_providers:
                    metadata = provider.get_movie_info(imdb_id=torrent['imdb'])
                    # Available fields:
                    # year            
                    # poster            
                    # rating
                    # votes
                    # genre
                    # mpaa            
                    # plot            
                    # director            
                    # title            
                    # cast
                    # duration
                    # imdbnumber            
                    # tagline            

                    if metadata:
                        artData['poster'] = metadata['poster']
                        artData['fanart'] = metadata['poster']

                        list_item.setLabel(torrent['name'])
                        list_item.setLabel2(metadata['title'])
                        
                        list_item.setInfo('video', {
                            'plotoutline': torrent['small_description'],
                            'imdbnumber': torrent['imdb'],
                            'title': torrent['name'],

                            'year': metadata['year'],
                            'rating': metadata['rating'],
                            'votes': metadata['votes'],
                            'genre': metadata['genre'],
                            'mpaa': metadata['mpaa'],
                            'plot': metadata['plot'],
                            'director': metadata['director'],
                            'originaltitle': metadata['title'],
                            'cast': metadata['cast'],
                            'duration': metadata['duration'],
                            'tagline': metadata['tagline'],

                            'mediatype': 'video'
                            })

                        break

            list_item.setArt(artData)
            
            # Set 'IsPlayable' property to 'true'.
            # This is mandatory for playable items!
            list_item.setProperty('IsPlayable', 'true')

            if category_id is not None:
                url = self.get_url(action='play', category_id=category_id, torrent=torrent['id'])
            else:
                url = self.get_url(action='play', category_id=self.categories.get_category_by_name(torrent["category"])['id'], torrent=torrent['id'])

            # Add our item to the Kodi virtual folder listing.
            xbmcplugin.addDirectoryItem(self._handle, url, list_item, isFolder=False, totalItems=totalItems)
        
        if addNextPageItem:
            # item for the next page
            list_item = xbmcgui.ListItem(label='Next...')
            url = self.get_url(action='listing', start_index=end_index, category_id=category_id)
            xbmcplugin.addDirectoryItem(self._handle, url, list_item, True)

        # Finish creating a virtual folder.
        xbmcplugin.endOfDirectory(self._handle)

    def play_video(self, category_id, torrent_id):
        torrentsById = self.cache.get('%s.%s' % (CACHE_LABEL_TORRENTS_BY_ID, category_id))

        try:
            torrent = torrentsById[torrent_id]
        except:
            torrentsById = self.cache.get('%s.%s' % (CACHE_LABEL_TORRENTS_BY_ID, None))
            torrent = torrentsById[torrent_id]

        torrent_path = self.filelist_api.download_torrent(torrent, self.dataPath)
        torrent_path_safe_str = quote_plus(torrent_path)

        link = 'plugin://plugin.video.elementum/play?uri=%s' % torrent_path_safe_str
        
        # Create a playable item with a path to play.
        play_item = xbmcgui.ListItem(path=link)

        # Pass the item to the Kodi player.
        xbmcplugin.setResolvedUrl(self._handle, True, listitem=play_item)

    def start_search(self, category_id):
        kb = xbmc.Keyboard('default', 'Name', True)
        kb.setDefault("")
        kb.setHiddenInput(False)
        kb.doModal()

        if not kb.isConfirmed():
            return
        
        text  = kb.getText()
        filtered_text = quote_plus(text)
        torrents = self.filelist_api.search_torrents("name", filtered_text, category_id)

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
                self.show_torrents(category_id, torrents, start_index=0, paged=False)
        else:
            dialog = xbmcgui.Dialog()
            ok = dialog.ok('Error', 'Not Found')


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

        xbmc.log("Router command: " + str(params))

        # Check the parameters passed to the plugin
        if params:

            if params['action'] == 'listing':
                if 'start_index' in params:
                    self.list_torrents(int(params['category_id']), int(params['start_index']))
                else:
                    self.list_torrents(int(params['category_id']), None)

            elif params['action'] == 'search':
                self.start_search(params.get('category_id'))

            elif params['action'] == 'play':
                # Play a video from a provided URL.
                self.play_video(params['category_id'], int(params['torrent']))

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
    indexer = Indexer(sys.argv[0], int(sys.argv[1]))
    indexer.router(sys.argv[2][1:])
