import sys
from urllib.parse import urlencode, parse_qsl
from urllib.request import urlopen
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

CACHE_LABEL_TMDB_DATA = "filelist.ro.api_cached_tmdb_"
CACHE_EXPIRATION_HOURS = 72


class TMDBInfoProvider:

    def __init__(self, token):
        self.tmdbKey = token
        self.cache = simplecache.SimpleCache()

    def get_movie_info(self, imdb_id):
        if not imdb_id:
            return
        
        cachedLabel = CACHE_LABEL_TMDB_DATA + imdb_id
        cachedMovieInfo = self.cache.get(cachedLabel)

        if cachedMovieInfo:
            return cachedMovieInfo

        tmdb_url = 'https://api.themoviedb.org/3/find/%s?api_key=%s&language=en-US&external_source=imdb_id' % \
            (imdb_id, self.tmdbKey)

        tmdb_response = urlopen(tmdb_url)
        tmdb_data = json.loads(tmdb_response.read())

        if tmdb_data and len(tmdb_data['movie_results']) > 0:
            metadata = tmdb_data['movie_results'][0]

            m = self.process_metadata(metadata)

            self.cache.set(cachedLabel, m, expiration=datetime.timedelta(hours=CACHE_EXPIRATION_HOURS))
            return m

    def process_metadata(metadata):
        m = {}

        if 'poster_path' in metadata:
            m['poster'] = 'http://image.tmdb.org/t/p/w500/%s' % metadata['poster_path']

        return m