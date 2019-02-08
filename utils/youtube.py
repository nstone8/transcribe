import urllib
import json
import vlc
import time
import transcribe as tr

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

        #get video duration and caption status
        for video in toReturn:
            videoJSON=json.loads(urllib.request.urlopen('https://www.googleapis.com/youtube/v3/videos?'+urllib.parse.urlencode({'part':'contentDetails','id':video['videoID'],'key':self.apiKey})).read())
            video['duration']=videoJSON['items'][0]['contentDetails']['duration']
            video['captioned']=videoJSON['items'][0]['contentDetails']['caption']=='true' #make this True if the response is 'true' false otherwise
        return toReturn

    def getPlaylistGenerator(self,playlist:str,location:tr.core.Location,organization:str)->'function':
        '''Return a function that implements the genenerates a record for each playlist entry'''
        play=self.getPlaylistEntries(playlist)
        def gen():
            #generate records
            for v in play:
                url=getRawURL(p['videoURL'])
                audio=tr.core.getAudioFromURL(url)
                rec=tr.core.Record(v['title'],v['videoID'],organization,location,audio)
                yield rec
        return gen
                
    
def getRawURL(url:str)->str:
    '''get raw video url for youtube video at url'''
    #Use VLC to determine raw video url
    inst=vlc.Instance()
    video=inst.media_new(url)
    player=video.player_new_from_media() 
    if player.play(): #need to play video to generate raw url
        raise Exception('video failed to play')
    while not vlc.libvlc_media_subitems(video).count(): #wait for raw url to be generated
        time.sleep(1)
    realURL=vlc.libvlc_media_subitems(video).item_at_index(0).get_mrl() #get raw url
    player.stop()
    return realURL
