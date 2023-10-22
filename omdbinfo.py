# Test API: https://www.omdbapi.com/?i=tt3896198&apikey=<API_KEY>
# {
#     "Title": "Guardians of the Galaxy Vol. 2",
#     "Year": "2017",
#     "Rated": "PG-13",
#     "Released": "05 May 2017",
#     "Runtime": "136 min",
#     "Genre": "Action, Adventure, Comedy",
#     "Director": "James Gunn",
#     "Writer": "James Gunn, Dan Abnett, Andy Lanning",
#     "Actors": "Chris Pratt, Zoe Saldana, Dave Bautista",
#     "Plot": "The Guardians struggle to keep together as a team while dealing with their personal family issues, notably Star-Lord's encounter with his father, the ambitious celestial being Ego.",
#     "Language": "English",
#     "Country": "United States",
#     "Awards": "Nominated for 1 Oscar. 15 wins & 60 nominations total",
#     "Poster": "https://m.media-amazon.com/images/M/MV5BNjM0NTc0NzItM2FlYS00YzEwLWE0YmUtNTA2ZWIzODc2OTgxXkEyXkFqcGdeQXVyNTgwNzIyNzg@._V1_SX300.jpg",
#     "Ratings": [
#         {
#             "Source": "Internet Movie Database",
#             "Value": "7.6/10"
#         },
#         {
#             "Source": "Rotten Tomatoes",
#             "Value": "85%"
#         },
#         {
#             "Source": "Metacritic",
#             "Value": "67/100"
#         }
#     ],
#     "Metascore": "67",
#     "imdbRating": "7.6",
#     "imdbVotes": "719,971",
#     "imdbID": "tt3896198",
#     "Type": "movie",
#     "DVD": "22 Aug 2017",
#     "BoxOffice": "$389,813,101",
#     "Production": "N/A",
#     "Website": "N/A",
#     "Response": "True"
# }

import re
import json
import simplecache
from datetime import timedelta as td
from urllib.parse import urlencode, parse_qsl
from urllib.request import urlopen

CACHE_LABEL_OMDB_DATA = "filelist.ro.api_cached_omdb_"
CACHE_EXPIRATION_HOURS = 24 * 7
NOT_FOUND = "NOT_FOUND"


class OMDBInfoProvider:

    def __init__(self, token):
        self.omdbKey = token
        self.cache = simplecache.SimpleCache()

    def get_movie_info(self, imdb_id):
        if not imdb_id:
            return

        cache_key = CACHE_LABEL_OMDB_DATA + imdb_id
        metadata = self.cache.get(cache_key)

        if metadata == NOT_FOUND:
            return None

        if metadata:
            return metadata

        url = 'https://www.omdbapi.com/?i=%s&apikey=%s' % (imdb_id, self.omdbKey)

        try:
            response = urlopen(url)
            metadata = json.loads(response.read())

            if metadata['Response'] == 'False':
                raise Exception(NOT_FOUND)

        except:
            self.cache.set(cache_key, NOT_FOUND, expiration=td(hours=CACHE_EXPIRATION_HOURS))

        metadata = self.process_metadata(metadata)
        self.cache.set(cache_key, metadata, expiration=td(hours=CACHE_EXPIRATION_HOURS))

        return metadata

    def process_metadata(self, metadata):
        m = {}

        # get release year (eg: 2017 in 05 May 2017). if not available an [''] is returned by findall
        # then we get the first element: ''
        try:
            m['year'] = re.findall(r'\d{4}|$', metadata.get('Released', ''))[0]
        except:
            m['year'] = ''

        try:
            m['rating'] = float(metadata.get('imdbRating', '0').replace('N/A', '0'))
        except:
            m['rating'] = 0.0
        
        try:
            m['votes'] = int(metadata.get('imdbVotes', '0').replace('N/A', '0').replace(',', ''))
        except:
            m['votes'] = 0

        try:
            m['duration'] = int(re.findall(r'\d+|$', metadata.get('Runtime', '0').replace('N/A', '0'))[0]) * 60
        except:
            m['duration'] = 0

        m['poster'] = metadata.get('Poster', '')
        m['genre'] = metadata.get('Genre', '').split(', ')
        m['mpaa'] = metadata.get('Rated', '')
        m['plot'] = metadata.get('Plot', '')
        m['director'] = metadata.get('Director', '')
        m['title'] = metadata.get('Title', '')
        m['cast'] = metadata.get('Actors', '').split(', ')
        m['imdbnumber'] = metadata.get('imdbID') 
        m['tagline'] = metadata.get('Awards') 

        return m
