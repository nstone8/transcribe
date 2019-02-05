import urllib
import json
import vlc
import time
import tempfile
import os
import ffmpeg

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

def getAudioFromURL(url)->tempfile.NamedTemporaryFile:
    '''get raw video file for youtube video at url url, get audio and return a NamedTemporaryFile'''
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
    #write video to a temporary file
    remoteVid=urllib.request.urlopen(realURL)
    tempHandle,tempPath=tempfile.mkstemp()
    part=remoteVid.read(1000)
    while part: #read one MB of the video at a time
        os.write(tempHandle,part) #write to temp file
        part=remoteVid.read(1000)
    remoteVid.close()
    os.close(tempHandle) #close remote file and temp file
    audioHandle,audioPath=tempfile.mkstemp(suffix='.mp3') #make file for audio to go to
    os.close(audioHandle) #ffmpeg will write to this, so we'll close it on our end first
    #strip audio from video and save to audioPath
    ffmpeg.input(tempPath).output(audioPath,q=0).overwrite_output().run()
    oldAudio=open(audioPath,'rb')
    newAudio=tempfile.NamedTemporaryFile(mode='w+b') #new temporary file which will auto-delete on garbage collection
    #copy the audio into the new self destructing file
    part=oldAudio.read(1000)
    while part:
        newAudio.write(part)
        part=oldAudio.read(1000)
    #clean up non self-destructing temp files we made
    oldAudio.close()
    os.remove(tempPath)
    os.remove(audioPath)
    newAudio.seek(0)
    return newAudio
