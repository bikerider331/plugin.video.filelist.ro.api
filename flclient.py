"""
https://filelist.io/api.php?username=tavy14t&passkey=<PASS_KEY>&action=latest-torrents
returns a list with items like this:
{
    "id": 838752,
    "name": "El.caballo.blanco.1962.1080p.WEB-DL.DDP2.0.H-264",
    "imdb": "tt0055818",
    "freeleech": 0,
    "doubleup": 0,
    "upload_date": "2023-06-27 20:59:36",
    "download_link": "https:\/\/filelist.io\/download.php?id=bla&passkey=blabla",
    "size": 6532622737,
    "internal": 0,
    "moderated": 1,
    "category": "Filme HD",
    "seeders": 15,
    "leechers": 2,
    "times_completed": 21,
    "comments": 0,
    "files": 1,
    "small_description": "Comedy, Drama, Musical"
}
"""

import urllib
from urllib.request import FancyURLopener
import xbmc
import json
import xbmcvfs
import os

class FireFoxAgent(FancyURLopener):
    version = 'Mozilla/5.0 (Windows; U; Windows NT 5.1; it; rv:1.8.1.11) Gecko/20071127 Firefox/2.0.0.11'

class FilelistClient:
    
    def __init__(self, username, passkey):
        self.username = username
        self.passkey = passkey

    def get_latest_torrents_by_category_id(self, categoryId):
        action="latest-torrents"

        url = self.make_url(action)
        url = url + "&category=" + str(categoryId)

        data = self.get_data(url) 

        return data

    def search_torrents(self,searchType, query, categoryId):
        action="search-torrents"
        
        url = self.make_url(action)
        url = url + "&type=" + searchType
        url = url + "&query=" + query

        if categoryId:
            url = url + "&category=" + categoryId

        data = self.get_data(url)

        return data    

    def make_url(self, action):
        return "https://filelist.io/api.php?username=" + self.username + \
            "&passkey=" + self.passkey + "&action=" + action

    def get_data(self, url):
        data = []
        try:
            agent = FireFoxAgent() 
            response = agent.open(url)
            receivedData = response.read()
            data = json.loads(receivedData)
        except Exception as e:
            xbmc.log("Error decoding json response from FL. Exception: " + str(e))

        return data

    def download_torrent(self, torrent, saveDir):
        torrentPath = os.path.join(saveDir, torrent['name'] + ".torrent")
        xbmc.log("Torrent path: " + torrentPath)
        
        xbmcvfs.delete(torrentPath)

        url = torrent['download_link']
        agent = FireFoxAgent() 

        response = agent.open(url)
        data = response.read()
        response.close()

        f = xbmcvfs.File(torrentPath, 'wb')
        f.write(data)
        f.close()
        
        return torrentPath
