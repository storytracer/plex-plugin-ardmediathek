# +++++ ARD Mediathek Plugin for Plex v0.1.1 alpha +++++
#
# (C) 2010 by Sebastian Majstorovic
# 
# Licensed under the GPL, Version 3.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#  
#    http://www.gnu.org/licenses/gpl-3.0-standalone.html
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# PMS plugin framework
from PMS import *
from PMS.Objects import *
from PMS.Shortcuts import *
import re

####################################################################################################

VIDEO_PREFIX = "/video/ardmediathek"

NAME = L('Title')

# make sure to replace artwork with what you want
# these filenames reference the example files in
# the Contents/Resources/ folder in the bundle
ART           = 'art.png'
ICON          = 'icon.png'

SHORT_CACHE_INTERVAL        = 300 #five minutes
CACHE_INTERVAL              = 1800 #half hour
LONG_CACHE_INTERVAL         = 604800 #one week
DEBUG                       = False

BASE_URL = "http://www.ardmediathek.de"

####################################################################################################

def Start():
  Plugin.AddPrefixHandler(VIDEO_PREFIX, VideoMainMenu, L('VideoTitle'), ICON, ART)

  Plugin.AddViewGroup("InfoList", viewMode="InfoList", mediaType="items")
  Plugin.AddViewGroup("List", viewMode="List", mediaType="items")
  
  MediaContainer.art = R(ART)
  MediaContainer.title1 = NAME
  #DirectoryItem.thumb = R(ICON)
    
def VideoMainMenu():
  dir = MediaContainer(viewGroup="List")
  
  dir.Append(Function(DirectoryItem(MenuTopByDate, title = "Nach Datum (Letzte 7 Tage)")))
  dir.Append(Function(DirectoryItem(MenuTopMostViewedToday, title = "Beliebteste Sendungen (Heute)")))
  
  return dir
    
def FullURL(path):
  return BASE_URL + path
    
def MenuTopMostViewedToday(sender):
  dir = MediaContainer(viewGroup="InfoList")
  site = XML.ElementFromURL(BASE_URL, True)
  
  contentBoxes = site.xpath("//div[@class='mt-box']")
  mostViewedBox = contentBoxes[1]
  mostViewedElement = mostViewedBox.xpath(".//div[@class='mt-box_header']/ul/li/a")[1]
  listPath = str(mostViewedElement.xpath('@href')[0])
  
  documentID = GetDocumentID(listPath)
  listURL = FullURL("/ard/servlet/ajax-cache/" + documentID + "/view=list/show=recent/index.html")

  menuItems = ParseMenuTopMostViewedToday(listURL)
  for i in range(0, len(menuItems)):
    dir.Append(menuItems[i])
  
  return dir
    
def MenuTopByDate(sender):
  dir = MediaContainer(viewGroup="List")
  site = XML.ElementFromURL(BASE_URL, True)
  
  listPath = str(site.xpath("//ul[@class='mt_navi']/li[@class='special']/a/@href")[0])
  listURL = FullURL(listPath)

  menuItems = ParseMenuTopByDate(listURL)
  for i in range(0, len(menuItems)):
    dir.Append(menuItems[i])

  return dir
  
def ParseMenuTopByDate(url):
  shows = []
  site = XML.ElementFromURL(url, True)
  
  dateElements = site.xpath("//div[@id='mt-broadcast_date']/ol/li/a")
  for i in range(0, len(dateElements)):
    dateElement = dateElements[i]
    datePath = str(dateElement.xpath("@href")[0])
    dateWeekday = dateElement.xpath("./span")[0].text
    dateDate = dateElement.xpath("./strong")[0].text
    
    shows.append(Function(
      DirectoryItem(
        MenuByDate, 
        title = dateWeekday + " - " + dateDate
      ), url = FullURL(datePath)
    ))
  
  return shows
  
def MenuByDate(sender, url):
  dir = MediaContainer(viewGroup="InfoList")
  site = XML.ElementFromURL(url, True)
  
  listPath = str(site.xpath("//a[@class='mt-box_pillbutton']/@href")[0])
  listURL = FullURL(listPath)
  
  site = XML.ElementFromURL(listURL, True)
  showElements = site.xpath("//div[@class='mt-box-overflow']/ol/li/ol/li/div[@class='mt-media_item']")
  for i in range(0, len(showElements)):
    showElement = showElements[i]
    showData = ParseShowData(showElement)
    if (showData is not None):
      dir.Append(GetVideoItem(showData))
  
  return dir
  
def ParseShowName(element):
  nameElement = element.xpath(".//p[" + containing("mt-source") + "]")[0]
  reShowName = re.search("aus:(.*)", nameElement.text)
  showName = Utf8Decode(reShowName.group(1))
  
  return showName

def ParseMenuTopMostViewedToday(url):
  shows = []
  site = XML.ElementFromURL(url, True)
  showElements = site.xpath("//div[@class='mt-media_item']")
  for i in range(0, len(showElements)):
    showElement = showElements[i]
    showData = ParseShowData(showElement)
    if (showData is not None):
      shows.append(GetVideoItem(showData))
  return shows
  
def GetVideoItem(showData):
  showDetails = showData['showDetails']
  return Function(VideoItem(
          GetStreamURL,
          title = showData['showName'] + " | " + showData['showTitle'],
          subtitle = showDetails['showDuration'],
          thumb = FullURL(showDetails['showThumbPath']),
          summary = showDetails['showDescription'],
        ), url = FullURL(showData['showPath']))
  
def ParseShowData(element):
  titleElements = element.xpath("./h3[@class='mt-title']/a")
  videoTypeElements = element.xpath(".//span[" + containing("mt-icon_video") + "]")
  if ((len(titleElements) > 0) and (len(videoTypeElements) > 0)):
    showPath = str(titleElements[0].xpath("@href")[0])
    documentID = GetDocumentID(showPath)
    
    showTitle = Utf8Decode(titleElements[0].text)
    showDetails = ParseShowDetails(documentID)
    showName = ParseShowName(element)
      
    itemDict = {
      'showPath': showPath,
      'documentID': documentID,
      'showTitle': showTitle,
      'showName': showName,
      'showDetails': showDetails
    }
    
    return itemDict
  
  return None
  
def ParseShowDetails(documentID):
  detailPage = XML.ElementFromURL(FullURL("/ard/servlet/ajax-cache/" + documentID + "/view=ajax/index.html"), True)
  
  titleElements = detailPage.xpath("./h3[@class='mt-title']/a")
  showTitle = Utf8Decode(titleElements[0].text)
  showPath = str(titleElements[0].xpath("@href")[0])
  
  showThumbPath = str(detailPage.xpath("//img/@src")[0])
  durationElement = detailPage.xpath(".//span[@class='mt-airtime']")[0]
  reShowDuration = re.search(".*min", durationElement.text)
  showDuration = Utf8Decode(reShowDuration.group(0))
  
  nameElement = detailPage.xpath(".//p[" + containing("mt-source") + "]")[0]
  reShowName = re.search("aus:(.*)", nameElement.text)
  showName = Utf8Decode(reShowName.group(1))
  
  descriptionElement = detailPage.xpath(".//p[@class='mt-description']")[0]
  showDescription = Utf8Decode(descriptionElement.text)
  
  detailPageDict = {
    'showTitle': showTitle,
    'showPath': showPath,
    'showThumbPath': showThumbPath,
    'showDuration': showDuration,
    'showName': showName,
    'showDescription': showDescription
  }
  
  return detailPageDict
  
def GetDocumentID(path):
  reDocumentID = re.search("ajax-cache\/(\d+)\/view", path)
  if (reDocumentID is None):
    reDocumentID = re.search("documentId=(\d+)", path)
  if (reDocumentID is None):
    reDocumentID = re.search("content\/(\d+)\?datum", path)
  documentID = reDocumentID.group(1)
  
  return documentID
  
def GetLargeThumb(documentID):
  site = XML.ElementFromURL("http://www.ardmediathek.de/ard/servlet/ajax-cache/" + documentID + "/view=ajax/index.html", True)
  imagePath = str(site.xpath("//img/@src")[0])
  
  return HTTP.Request(FullURL(imagePath))
  
def GetStreamURL(sender, url):
  site = XML.ElementFromURL(url, True)
  
  scriptContainer = site.xpath("//div[@class='mt-player_container']/script")[0]
  scriptText = scriptContainer.text
  
  reStream = re.findall("addMediaStream.*\"(.*)\".*\"(.*)\"", scriptText)
  
  streamsCount = len(reStream) - 1
  if (streamsCount < 0):
    streamsCount = 0
    
  streamParts = reStream[streamsCount]
  streamBase = streamParts[0]
  streamClip = streamParts[1]
  
  for i in range(0, streamsCount + 1):
    clip = reStream[i][1]
    if (clip.find("hi.flv") > -1):
      streamBase = ""
      streamClip = clip
  
  playerURL = 'http://www.plexapp.com/player/player.php?url=' + streamBase + '&clip=' + streamClip
  
  if (streamBase == ""):
    playerURL = 'http://www.plexapp.com/player/player.php?clip=' + streamClip
  
  return Redirect(WebVideoItem(playerURL))
  
def Utf8Decode(source):
  try:
      return source.encode("iso-8859-1").decode("utf-8")
  except:
      return ""
      
def containing(className):
  return "contains(concat(' ',normalize-space(@class),' '),' " + className + " ')";