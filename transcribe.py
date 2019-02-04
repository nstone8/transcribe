import urllib
import json
def getChannelsFromUsername(username:str)->list:
    '''Get a list of all of the channels associated with username'''
    channels=json.loads(urllib.request.urlopen('https://www.googleapis.com/youtube/v3/channels?'+urllib.parse.urlencode({'part':'id,snippet','forUsername':username,'key':'AIzaSyBtV9xEealtUjYQmM-WKdTGMdAGSnYdNDE'})).read())
    return channels

def getPlaylistsFromChannel(channelId:str)->list:
    '''Get a list of all the playlists associated with the channel with id channelId'''
    playlists=[]
    thisPage=json.loads(urllib.request.urlopen('https://www.googleapis.com/youtube/v3/playlists?'+urllib.parse.urlencode({'part':'snippet','channelId':channelId,'key':'AIzaSyBtV9xEealtUjYQmM-WKdTGMdAGSnYdNDE'})).read())
    playlists.extend(thisPage['items'])
    while 'nextPageToken' in thisPage:
        thisPage=json.loads(urllib.request.urlopen('https://www.googleapis.com/youtube/v3/playlists?'+urllib.parse.urlencode({'part':'snippet','channelId':channelId,'pageToken':thisPage['nextPageToken'],'key':'AIzaSyBtV9xEealtUjYQmM-WKdTGMdAGSnYdNDE'})).read())
        playlists.extend(thisPage['items'])
    return playlists

def getPlaylistEntries(playlistId:str)->list:
    '''Get a list of all of the videos in the playlist with id playlistId'''
    entries=[]
    thisPage=json.loads(urllib.request.urlopen('https://www.googleapis.com/youtube/v3/playlistItems?'+urllib.parse.urlencode({'part':'snippet','playlistId':playlistId,'key':'AIzaSyBtV9xEealtUjYQmM-WKdTGMdAGSnYdNDE'})).read())
    entries.extend(thisPage['items'])
    while 'nextPageToken' in thisPage:
        thisPage=json.loads(urllib.request.urlopen('https://www.googleapis.com/youtube/v3/playlistItems?'+urllib.parse.urlencode({'part':'snippet','playlistId':playlistId,'pageToken':thisPage['nextPageToken'],'key':'AIzaSyBtV9xEealtUjYQmM-WKdTGMdAGSnYdNDE'})).read())
        entries.extend(thisPage['items'])
    toReturn=[]
    for entry in entries:
        videoId=entry['snippet']['resourceId']['videoId']
        toReturn.append({'title':entry['snippet']['title'],'videoID':videoId,'videoURL':'https://www.youtube.com/watch?'+urllib.parse.urlencode({'v':videoId})})
    return toReturn
