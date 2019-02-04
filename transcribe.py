import urllib
import json

class Youtube:
    def __init__(self,apiKey:str):
        '''Create new Youtube object which will execute queries using apiKey'''
        self.apiKey=apiKey
    def getChannelsFromUsername(self,username:str)->list:
        '''Get a list of all of the channels associated with username'''
        channels=json.loads(urllib.request.urlopen('https://www.googleapis.com/youtube/v3/channels?'+urllib.parse.urlencode({'part':'id,snippet','forUsername':username,'key':self.apiKey})).read())
        return channels

    def getPlaylistsFromChannel(self,channelId:str)->list:
        '''Get a list of all the playlists associated with the channel with id channelId'''
        playlists=[]
        thisPage=json.loads(urllib.request.urlopen('https://www.googleapis.com/youtube/v3/playlists?'+urllib.parse.urlencode({'part':'snippet','channelId':channelId,'key':self.apiKey})).read())
        playlists.extend(thisPage['items'])
        while 'nextPageToken' in thisPage:
            thisPage=json.loads(urllib.request.urlopen('https://www.googleapis.com/youtube/v3/playlists?'+urllib.parse.urlencode({'part':'snippet','channelId':channelId,'pageToken':thisPage['nextPageToken'],'key':self.apiKey})).read())
            playlists.extend(thisPage['items'])
        return playlists

    def getPlaylistEntries(self,playlistId:str)->list:
        '''Get a list of all of the videos in the playlist with id playlistId'''
        entries=[]
        thisPage=json.loads(urllib.request.urlopen('https://www.googleapis.com/youtube/v3/playlistItems?'+urllib.parse.urlencode({'part':'snippet','playlistId':playlistId,'key':self.apiKey})).read())
        entries.extend(thisPage['items'])
        while 'nextPageToken' in thisPage:
            thisPage=json.loads(urllib.request.urlopen('https://www.googleapis.com/youtube/v3/playlistItems?'+urllib.parse.urlencode({'part':'snippet','playlistId':playlistId,'pageToken':thisPage['nextPageToken'],'key':self.apiKey})).read())
            entries.extend(thisPage['items'])
        toReturn=[]
        for entry in entries:
            videoId=entry['snippet']['resourceId']['videoId']
            toReturn.append({'title':entry['snippet']['title'],'videoID':videoId,'videoURL':'https://www.youtube.com/watch?'+urllib.parse.urlencode({'v':videoId})})
        return toReturn
