import urllib
import xbmc
import json
import xbmcvfs
import os

class FLTorrentProvider:
    
    def __init__(self, username, passkey):
        self.username = username
        self.passkey = passkey


    def getLatestTorrentsByCategoryID(self, categoryId):
        action="latest-torrents"
        url = self.makeUrl(action)

        url = url +"&category="+str(categoryId)

        data = self.getData(url) 

        return data

    def searchTorrents(self,searchType, query, categoryId):
        action="search-torrents"
        
        url = self.makeUrl(action)
        url = url + "&type="+searchType
        url = url + "&query="+query
        if categoryId:
            url = url + "&category="+categoryId

        data = self.getData(url)

        return data    

    def makeUrl(self, action):
        url = "https://filelist.io/api.php?username="+self.username+"&passkey="+self.passkey+"&action="+action
        return url

    def getData(self, url):
        response = urllib.urlopen(url)
        data = json.loads(response.read())
        return data

    def downloadTorrent(self, torrent, saveDir):
        torrentPath = os.path.join(saveDir, torrent['name']+".torrent")
        xbmc.log("Torrent path: "+torrentPath)
        xbmcvfs.delete(torrentPath)

        url = torrent['download_link']

        xbmc.log("Download link: "+url)

        response = urllib.urlopen(url)
        data = response.read()
        response.close()

        f = xbmcvfs.File(torrentPath, 'wb')
        f.write(data)
        f.close()
        
        return torrentPath