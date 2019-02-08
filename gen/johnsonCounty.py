import transcribe as tr
import urllib
import re
def genRecords():
    vidList=str(urllib.request.urlopen('http://johnsoncountyia.iqm2.com/Citizens/Media.aspx').read())
    here=tr.core.Location(country='USA',region='Iowa',location='Johnson County')
    date=re.compile(r'[0-9]{2}/[0-9]{2}/[0-9]{4} [0-9]{2}:[0-9]{2} .{2}')
    title=re.compile(r"\\'MediaLink\\'.*?>(.*?)<")
    url=re.compile(r"\\'MediaDownloadLink\\'.*?href=\\'(.*?)\\'")
    org=re.compile(r"\\'MediaEventType\\'>(.*?)<")
    thisOrg=org.search(vidList)
    vidList=vidList[thisOrg.end(0):]
    vidInfo=[]
    while thisOrg:
        orgName='Johnson County '+thisOrg.group(1)
        thisOrg=org.search(vidList)
        if thisOrg:
            thisSection=vidList[:thisOrg.start(0)] #this org's worth of videos. if there is not another org, we'll just go to EOF
            vidList=vidList[thisOrg.end(0):]#Remove this org from vidList
        else:
            thisSection=vidList[:]
        thisDate=date.search(thisSection)
        while thisDate:
            thisSection=thisSection[thisDate.end(0):]
            thistitle=title.search(thisSection).group(1)
            thisURL=url.search(thisSection).group(1)

            vidInfo.append({'title':thistitle,'date':thisDate.group(0),'url':thisURL,'org':orgName})
        
            thisDate=date.search(thisSection)
    for v in vidInfo:
        audio=tr.core.getAudioFromURL(v['url'])
        rec=tr.core.Record(v['date']+'_'+v['title'],v['url'],v['org'],here,audio)
        yield rec
        
