import tempfile
import os
import urllib
import ffmpeg
import re
import sys
import inspect
import time

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

def alignReadsExhaustive(free:list,fixed:list=None)->(str,int):
    startTime=time.perf_counter()
    '''Try all alignment permutations of the reads given in 'free' (which should be a list of lists containing every word for each read and return the read with the longest overlapping sequence and its corresponding score'''
    free=free[:]
    bestSeq='' #this will be our highest scoring (longest) aligned sequence
    bestScore=0
    if not fixed:
        #fix one read if we haven't already
        fixed=[free[0][:]] #this should still be a list of lists
        free=free[1:][:]
    thisRead=free[0][:] #this recursion level will change the position of this read, do copy so the recursion doesn't walk all over itself
    free=free[1:][:]
    fixed=[f for f in fixed if f] #delete any empty reads
    for i in range(len(fixed)):
        fixed[i]=([None]*len(thisRead))+fixed[i] #pad all fixed reads with None so we barely don't overlap
            
    while True: #while we haven't run out of things to compare to, test first thing below
        noneLen=len([x for x in thisRead if not x]) #index of the first non-None word in thisRead
        fixedLengths=[len(f) for f in fixed]
        if len(fixed)==1:
            #Top level of recursion
            print('noneLen:',noneLen)
            print('max(fixedLengths)',max(fixedLengths))
            print('elapsed time (s):',time.perf_counter()-startTime)
            print('\n')
        if noneLen>max(fixedLengths): #We are no longer overlapping
            break
        elif free: #we are not at the bottom of the recursion
            newSeq,newScore=alignReads(free,fixed+[thisRead])
            if newScore>bestScore: #new winner
                bestSeq=newSeq
                bestScore=newScore
                #print(bestScore)
        else: #we are at the bottom of the recursion, time to count some shit
            allSeq=fixed+[thisRead]
            maxLen=max([len(j) for j in allSeq]) #find the maximum length of all of our reads
            totalScore=0
            thisSequence=''
            for i in range(maxLen):
                #see if we have any overlapping homology
                thisPosWords=[seq[i] for seq in allSeq if i<len(seq) if seq[i]]#ignore sequences we've exhausted and None padding
                #find the word that occurs the most, we will only score repeats of that word
                wordCounts={word:thisPosWords.count(word) for word in set(thisPosWords)} #strip none
                mostCommonWord=''
                highestCount=0            
                for word in wordCounts:
                    if wordCounts[word]>highestCount:
                        mostCommonWord=word
                        highestCount=wordCounts[word]
                #increment score for this iteration
                totalScore+=(highestCount-1)**2 #The purpose of this (n-1)**2 scoring is to incentivize large amounts of overlap at one locus over smaller amounts of overlap at multiple locations
                thisSequence=thisSequence+' '+mostCommonWord #our consensus sequence for this arrangement will be the most common word at each location
            if totalScore>bestScore: #new winner
                bestScore=totalScore
                bestSeq=thisSequence
        #after counting or starting the next round of recursion, add a None to the front of thisread or remove a None from the front of all fixed to scrooch its relative position up one
        firstFixed=[f[0] for f in fixed] #all the first entries in fixed
        if not any(firstFixed): #if all of fixed start with None
            fixed=[f[1:] for f in fixed] #trim one none off all fixed
        else:
            thisRead[0:0]=[None] #add a none to thisread
    return bestSeq,bestScore

def audioToText(audio:tempfile.NamedTemporaryFile)->str:
    #get series of overlapping reads
    reads=shotgun(audio,5,5) #Always want depth to be odd
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

def alignReads(*reads:str)->str:
    overlaps=[]
    readsToDo=list(range(len(reads)))
    readsToDo.reverse()
    while readsToDo:
        i=readsToDo.pop()
        thisRead=reads[i]
        thisReadOverlaps=[]
        #otherReads=[reads[j] for j in range(len(reads)) if j!=i]
        #Scan through this read, searching for subsets at least 2 words long present in the other reads
        for k in readsToDo: #for the index of all other reads which haven't been compared to this one
            curPos=0
            while True:
                if curPos > (len(thisRead)-1):#don't look at the last word, it has to be part of a longer match to count (2 word min)
                    break
                if thisRead[curPos] in reads[k]: #one word overlap
                    matchStart=reads[k].index(thisRead[curPos]) #index of the start of the overlap in the 'other' read
                    if thisRead[curPos+1]==reads[k][matchStart+1]: #got at least a two word match, see how long it is and record
                        matchLen=2
                        while thisRead[curPos+matchLen]==reads[k][matchStart+matchLen]: #the match is at least matchLen+1 long
                            matchLen+=1
                            if (len(thisRead)<=curPos+matchLen) or (len(reads[k])<=matchStart+matchLen): #check that we aren't going to run off the end of either of our lists, break if we are
                                break
                        #we now know the match length, record it's length and start position on both reads
                        overlaps.append({'reads':(i,k),'start':(curPos,matchStart),'length':matchLen})
                        curPos=curPos+matchLen #don't need to check parts of these strings for another match
                curPos+=1
    #reconstruct consensus sequence from overlaps
    #Which read is involved in the most overlaps?
    overlapReads=[]
    for o in overlaps:
        overlapReads.extend(o['reads'])
    matchedReads=set(overlapReads) #throw away reads which don't have any overlaps
    orderedReads=[]
    while matchedReads: #make list of reads in decreasing order of total matches
        maxCount=0
        maxRead=None
        for r in matchedReads:
            thisCount=overlapReads.count(r)
            if thisCount>maxCount:
                maxCount=thisCount
                maxRead=r
        orderedReads.append(maxRead)
        matchedReads=matchedReads-{maxRead} #remove this read from consideration in order to find the next most prolific matcher
    #fix most matched read, then align others to that (and subsequent fixed reads) so that the longest overlap for that read matches
    orderedReads.reverse() #go in decending order when popped
    fixedReads=[orderedReads.pop()]
    readShifts={fixedReads[0]:0} #how far must each read be shifted to get it in alignment
    fixedOverlaps=[o for o in overlaps if fixedReads[0] in o['reads']]
    while orderedReads:
        #calculate the shift required to bring the read in line and record it. If no matches are available for the read in fixedOverlaps, push it back on orderedReads
        thisRead=orderedReads.pop()
        matchingOverlaps=[f for f in fixedOverlaps if thisRead in f['reads']]
        if matchingOverlaps:
            #we align with a fixed read, calculate shift
            #find longest match between this read and fixed reads
            maxOverlapLength=0
            maxOverlap=None
            for o in matchingOverlaps:
                if o['length']>maxOverlapLength:
                    maxOverlapLength=o['length']
                    maxOverlap=o
            thisReadIndex=maxOverlap['reads'].index(thisRead)
            fixedReadIndex=0 if thisReadIndex else 1 #if thisReadIndex is 1, fixedReadIndex is 0 or vice versa
            thisShift=maxOverlap['start'][fixedReadIndex]-maxOverlap['start'][thisReadIndex]
            readShifts[thisRead]=thisShift
            #Add new fixed overlaps (overlaps that include this read but not any already fixed reads)
            newFixedOverlaps=[o for o in overlaps if (thisRead in o['reads'] and (not(set(o['reads']) & set(fixedReads))))]
            fixedOverlaps.extend(newFixedOverlaps)
            fixedReads.append(thisRead)
        else:
            #no matches with fixed read, push back on orderedReads
            orderedReads[0:0]=[thisRead]
    return (reads,overlaps,readShifts)

