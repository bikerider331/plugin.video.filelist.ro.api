import urllib
from urllib.request import FancyURLopener
import xbmc
import json
import xbmcvfs
import os

class FireFoxAgent(FancyURLopener):
    version = 'Mozilla/5.0 (Windows; U; Windows NT 5.1; it; rv:1.8.1.11) Gecko/20071127 Firefox/2.0.0.11'

class FLTorrentProvider:
    
    def __init__(self, username, passkey):
        self.username = username
        self.passkey = passkey

    def getLatestTorrentsByCategoryID(self, categoryId):
        action="latest-torrents"

        url = self.makeUrl(action)
        url = url +"&category=" + str(categoryId)

        data = self.getData(url) 

        return data

    def searchTorrents(self,searchType, query, categoryId):
        action="search-torrents"
        
        url = self.makeUrl(action)
        url = url + "&type=" + searchType
        url = url + "&query=" + query

        if categoryId:
            url = url + "&category=" + categoryId

        data = self.getData(url)

        return data    

    def makeUrl(self, action):
        return "https://filelist.io/api.php?username=" + self.username + \
            "&passkey=" + self.passkey + "&action=" + action

    def getData(self, url):
        xbmc.log("getData using url: "+url)
        data = []
        try:
            agent = FireFoxAgent() 
            response = agent.open(url)
            receivedData = response.read()
            data = json.loads(receivedData)
        except Exception as e:
            xbmc.log("Error decoding json response from FL. Exception: " + str(e))

        return data

    def downloadTorrent(self, torrent, saveDir):
        torrentPath = os.path.join(saveDir, torrent['name'] + ".torrent")
        xbmc.log("Torrent path: " + torrentPath)
        xbmcvfs.delete(torrentPath)

        url = torrent['download_link']

        xbmc.log("Download link: " + url)

        agent = FireFoxAgent() 

        response = agent.open(url)
        data = response.read()
        response.close()

        f = xbmcvfs.File(torrentPath, 'wb')
        f.write(data)
        f.close()
        
        return torrentPath
