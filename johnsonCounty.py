import urllib
import re
def generateVideo():
    vidList=str(urllib.request.urlopen('http://johnsoncountyia.iqm2.com/Citizens/Media.aspx').read())
    date=re.compile(r'[0-9]{2}/[0-9]{2}/[0-9]{4} [0-9]{2}:[0-9]{2} .{2}')
    title=re.compile(r"\\'MediaLink\\'.*?>(.*?)<")
    url=re.compile(r"\\'MediaDownloadLink\\'.*?href=\\'(.*?)\\'")
    thisDate=date.search(vidList)
    vidInfo=[]
    while thisDate:
        vidList=vidList[thisDate.end(0):]
        thistitle=title.search(vidList).group(1)
        thisURL=url.search(vidList).group(1)

        vidInfo.append({'title':thistitle,'date':thisDate.group(0),'url':thisURL})
        
        thisDate=date.search(vidList)
    return vidInfo
        
