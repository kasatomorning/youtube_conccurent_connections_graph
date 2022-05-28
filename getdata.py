import json
import os
from googleapiclient.discovery import build
import yt_dlp
from os.path import join, dirname
from dotenv import load_dotenv
from prometheus_client import start_http_server, Gauge, Enum
import datetime

dotenv_path = join(dirname(__file__), '.env')
load_dotenv(dotenv_path)
# .envの値をDEVELOPER_KEYに代入
DEVELOPER_KEY = os.environ.get("DEVELOPER_KEY")

YOUTUBE_API_SERVICE_NAME = 'youtube'
YOUTUBE_API_VERSION = 'v3'
# YouTubeAPIを読み込む
youtube = build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION,
                developerKey=DEVELOPER_KEY)
subscriberCount_prom = Gauge(
    "subscriberCount", "the number of subscriber", ['channelid'])
concurrentViewers_prom = Gauge(
    "concurrentViewers", "the number of concurrent viewers", ['videoid'])
likeCount_prom = Gauge("likeCount", "the number of likes", ['videoid'])
channelURL = "https://www.youtube.com/channel/UCSFCh5NL4qXrAy9u-u2lX3g"
islive = Enum('islive', 'whether online or not',
              states=['online', 'offline', 'unknown'])
videoid = -1


def searchvalues(videoid):
    # https://www.youtube.com/c/CHANNELNAMEの場合、CHANNELIDが不明なので流す
    nowvideoid = videoid
    if("/c/" in channelURL):
        print("URL invalid")
        islive.state('unknown')
        return -1
    elif(is_live(channelURL)):
        islive.state('online')

        channelid = channelURL.split("/")[-1]

        if(nowvideoid == -1):
            print("called")
            videolist_res = videolist_search(channelid)
            nowvideoid = videolist_res["items"][0]["id"]["videoId"]
            with open('videolistresponse.json', mode='w') as f:
                json.dump(videolist_res, f)

        video_res = video_search(nowvideoid)
        channel_res = channel_search(channelid)
        subscriberCount = channel_res['items'][0]["statistics"]['subscriberCount']
        concurrentViewers = video_res['items'][0]["liveStreamingDetails"]["concurrentViewers"]
        likeCount = video_res['items'][0]["statistics"]["likeCount"]

        print(subscriberCount)
        print(concurrentViewers)
        print(likeCount)
        subscriberCount_prom.labels(channelid).set(subscriberCount)
        concurrentViewers_prom.labels(videoid).set(concurrentViewers)
        likeCount_prom.labels(videoid).set(likeCount)
        return nowvideoid
    else:
        print("Not Online")
        islive.state('offline')
        nowvideoid = -1
        subscriberCount_prom.labels(-1).set(0)
        concurrentViewers_prom.labels(-1).set(0)
        likeCount_prom.labels(-1).set(0)
        return nowvideoid


def channel_search(channelid):
    channel_response = youtube.channels().list(
        part="id,statistics",
        id=channelid
    ).execute()
    return channel_response


def video_search(videoid):
    video_response = youtube.videos().list(
        part="liveStreamingDetails,id,snippet,statistics",
        id=videoid
    ).execute()
    return video_response


def is_live(channelURL):
    channellive = channelURL + "/live"
    try:
        with yt_dlp.YoutubeDL() as ydl:
            info = ydl.extract_info(channellive, download=False)
        return True
    except:
        return False


def videolist_search(channelid):
    videolist_response = youtube.search().list(
        part="id,snippet",
        channelId=channelid,
        eventType="live",
        type="video"
    ).execute()
    return videolist_response


if __name__ == "__main__":
    start_http_server(8000)
    while True:
        dt_now = datetime.datetime.now()
        if(dt_now.second % 60 == 30):
            videoid = searchvalues(videoid)
