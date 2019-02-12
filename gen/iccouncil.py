import transcribe as tr
import transcribe.utils.youtube as youtube
def genRecords():
    yt=youtube.Youtube('AIzaSyDx9fq4MAamDGiY6mCDg0w-etXq1gcZqnU')#key goes here
    here=tr.core.Location(country='USA',region='Iowa',location='Iowa City')
    gen=yt.getPlaylistGenerator('PLeu1kpwYwId5b4DKSu0s9ZxVbaJTBX3H7',here,'Iowa City City Council')
    for g in gen():
        yield g
