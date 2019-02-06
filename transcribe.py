import tempfile
import os
import urllib
import ffmpeg

class Location:
    '''Class to represent the location of origin for records to be transcribed'''
    def __init__(country:str,region:str,location:str):
        '''Create a new Location instance representing the county/municipality location in state/region region in country country'''
        self.country=country
        self.region=region
        self.location=location

class Record:
    '''Class to represent individual records to be transcribed'''
    def __init__(title:str,id:str,organization:str,location:Location,audio:tempFile.TemporaryFile):
        '''Create a new Record instance representing a record with title title produced by group/organization organization in location location.
        The passed-in id should uniquely identify the Record amongst other records produced by the same organization, and should not change if the resource is re-fetched
        The record audio should be passed in as a TemporaryFile'''
        self.title=title
        self.id=id
        self.org=organization
        self.audio=audio

def getAudioFromURL(url)->tempfile.NamedTemporaryFile:
    remoteVid=urllib.request.urlopen(url)
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
