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

CACHE_LABEL_TMDB_DATA = "filelist.ro.api_cached_tmdb_"
CACHE_EXPIRATION_HOURS = 72
class MovieInfoProvider:
    
    def __init__(self, tmdbKey):
        self.tmdbKey = tmdbKey
        self.cache = simplecache.SimpleCache()

    def getMovieInfo(self, imdbID):
        if imdbID:
            cachedLabel = CACHE_LABEL_TMDB_DATA + imdbID
            cachedMovieInfo = self.cache.get(cachedLabel)
            if cachedMovieInfo:
                return cachedMovieInfo

            tmdb_url = 'https://api.themoviedb.org/3/find/%s?api_key=%s&language=en-US&external_source=imdb_id' % (imdbID, self.tmdbKey)
            tmdb_response = urllib.urlopen(tmdb_url)
            tmdb_data = json.loads(tmdb_response.read())
            xbmc.log(str(tmdb_data))
            if not tmdb_data is None:
                if len(tmdb_data['movie_results']) > 0:
                    first_movie = tmdb_data['movie_results'][0]
                    xbmc.log(str(first_movie))
                    self.cache.set(cachedLabel,first_movie, expiration=datetime.timedelta(hours=CACHE_EXPIRATION_HOURS))
                    return first_movie

    def getPosterFullPath(self, posterRelativePath):
        return 'http://image.tmdb.org/t/p/w500/%s' % posterRelativePath

    def getBackdropFullPath(self, backdropRelativePath):
        return 'http://image.tmdb.org/t/p/original/%s' % backdropRelativePath


