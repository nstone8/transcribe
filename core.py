import tempfile
import os
import urllib
import ffmpeg
import re
import sys
import inspect

class Location:
    '''Class to represent the location of origin for records to be transcribed'''
    def __init__(self,country:str,region:str,location:str):
        '''Create a new Location instance representing the county/municipality location in state/region region in country country'''
        self.country=country
        self.region=region
        self.location=location

class Record:
    '''Class to represent individual records to be transcribed'''
    def __init__(self,title:str,id:str,organization:str,location:Location,audio:tempfile.TemporaryFile):
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
    audioHandle,audioPath=tempfile.mkstemp(suffix='.wav') #make file for audio to go to
    os.close(audioHandle) #ffmpeg will write to this, so we'll close it on our end first
    #strip audio from video and save to audioPath
    ffmpeg.input(tempPath).output(audioPath,ac=1,ar=16000,f='wav',c='pcm_s16le').overwrite_output().run()
    #remove temp video, we're done with it
    os.remove(tempPath)
    oldAudio=open(audioPath,'rb')
    newAudio=tempfile.NamedTemporaryFile(mode='w+b',suffix='.wav') #new temporary file which will auto-delete on garbage collection
    #copy the audio into the new self destructing file
    part=oldAudio.read(1000)
    while part:
        newAudio.write(part)
        part=oldAudio.read(1000)
    #clean up non self-destructing temp files we made
    oldAudio.close()
    os.remove(audioPath)
    newAudio.seek(0)
    return newAudio

def chunkAudio(audio:tempfile.NamedTemporaryFile,duration:int,offset:int)->str:
    '''take an audio file and split it into chunks duration long starting at offset. Returns dict with a handle to a (temporary) directory holding the result files as well as a list containing the file names in chronological order'''
    i=0
    directory=tempfile.mkdtemp()
    suffix=re.compile(r'.*\.(.*)').search(audio.name).group(1)
    durRe=re.compile(r'Duration: ([0-9]{2}):([0-9]{2}):([0-9]{2})\.([0-9]{2})')
    ffprobe=os.popen('ffprobe '+audio.name+' 2>&1').read()
    durMatch=durRe.search(ffprobe)
    length=24*60*int(durMatch.group(1))+60*int(durMatch.group(2))+int(durMatch.group(3))+0.01*int(durMatch.group(4))
    files=[]
    while ((i*duration)+offset)<length:
        #make a chunk with the same format/codec
        filePath=os.path.join(directory,'chunk'+str(i)+'.'+suffix)
        files.append(filePath)
        ffmpeg.input(audio.name,ss=(i*duration)+offset).output(filename=filePath,c='copy',t=duration).overwrite_output().run()
        i+=1
    return {'directory':directory,'files':files}

def shotgun(audio:tempfile.NamedTemporaryFile,snipSize:int,depth:int)->list:
    '''Take a audio file and sample it into overlapping segments. Each segment will be snipSize long and any single moment will be sampled by depth overlapping segments'''
    offset=snipSize/depth
    allChunks=[]
    for i in range(depth):
        allChunks.append(chunkAudio(audio,snipSize,offset*i)['files'])
        i+=1
    #interleve chunks so we have an array of overlapping reads in chronological order
    j=0
    reads=[]
    go=True
    while go:
        for chunkArray in allChunks:
            try:
                reads.append(chunkArray[j])
            except IndexError:
                #We're out of reads
                go=False
                break
        j+=1
    return reads

def audioToText(audio:tempfile.NamedTemporaryFile)->str:
    #get series of overlapping reads
    reads=shotgun(audio,6,6)
    #convert all reads to text
    projectDir=os.sep.join(inspect.getfile(sys.modules[__name__]).split(os.sep)[:-1]) #find deepsearch in transcribe directory
    dsCommand='deepspeech --model '+os.path.join(projectDir,'deepspeech','models/output_graph.pbmm')+' --alphabet '+os.path.join(projectDir,'deepspeech','models/alphabet.txt')+' --lm '+os.path.join(projectDir,'deepspeech','models/lm.binary')+' --trie '+os.path.join(projectDir,'deepspeech','models/trie')+' --audio '
    readText=[]
    k=1
    for a in reads:
        print('converting read',k,'of',len(reads))
        #do speech recognition
        thisText=os.popen(dsCommand+a).read()
        print('***',thisText,'***')
        readText.append(thisText)
        k+=1
    return readText

