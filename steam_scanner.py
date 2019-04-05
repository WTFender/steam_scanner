#!/usr/bin/env python
from steam.steamid import SteamID
from xml.etree import ElementTree
from bs4 import BeautifulSoup
from datetime import datetime
from random import randint
from steam import WebAPI
from os import environ
import mysql.connector
import requests
import json
import re


class Profile:
    def __init__(self, steamid, communityvisibilitystate, profilestate,
                    personaname, profileurl, avatar, timecreated):
        self.steamid = steamid
        self.communityvisibilitystate = communityvisibilitystate
        self.profilestate = profilestate
        self.personaname = personaname
        self.profileurl = profileurl
        self.avatar = avatar
        self.timecreated = timecreated
        self.summary = None
        self.vacBanned = 0
        self.tradeBanState = 0

# connect to database
def connect_db():
    # get database settings
    db_user = environ["MYSQL_USER"]
    db_pass = environ["MYSQL_PASS"]
    db_host = environ["MYSQL_HOST"]
    db_db = environ["MYSQL_DB"]
    # connect to db
    cnx = mysql.connector.connect(user=db_user, password=db_pass,
                                    host=db_host, database=db_db)
    # return cursor
    return cnx, cnx.cursor()

# get community profile info
def get_community_profile(steamid):
    r = requests.get("https://steamcommunity.com/profiles/%s/?xml=1" % steamid)
    try:
        xml = ElementTree.fromstring(r.content)
    # gracefully handle empty profiles
    except Exception as e:
        print e
        print r.content
    summary = None
    vacBanned = 0
    tradeBanState = 0
    # find attributes in XML profile
    for child in xml:
        try:
            if child.tag == "summary":
                summary = child.text
            elif child.tag == "vacBanned":
                vacBanned = child.text
            elif child.tag == "tradeBanState":
                tradeBanState = child.text
        except Exception as e:
            print e
    return summary, vacBanned, tradeBanState

# find links in summary
def find_links(summary, steamid, cnx, c):
    urls = []
    try:
        soup = BeautifulSoup(summary, "html.parser")
    except:
        return urls
    # steam href tags anything that looks like a link
    # scrape href tags (urls) from summary html
    for link in soup.findAll('a', attrs={'href': re.compile("^https?://")}):
        try:
            url = link.get("href").replace("https://steamcommunity.com/linkfilter/?url=", "")
            urls.append(url)
        except Exception as e:
            print e
            print link
            continue
        # commit link to db
        c.execute("INSERT INTO links (url, display) "
                    "VALUES (%s, %s) "
                    "ON DUPLICATE KEY UPDATE display=%s",
                    (url, link.text, link.text))
        cnx.commit()
        # commit profile_link to db
        c.execute("INSERT IGNORE INTO profile_links (url, steamid) "
                    "VALUES (%s, %s)",
                    (url, steamid))
        cnx.commit()
    return urls

# get n profiles
def get_profiles(n):
    # generate 100 steam64IDs, this needs to be improved
    # as it is not exactly "random" nor a conclusive range of ids
    ids = ""
    for i in range(0,n):
        ids = ids + ",%s" % SteamID(id=randint(1, 1000000000), 
                                    type="Individual", 
                                    universe="Public", 
                                    instance=1).as_64
    # get player info via steam WebAPI (100 max)
    s_api_key = environ['STEAM_API_KEY']
    steam_api = WebAPI(key=s_api_key)
    players = steam_api.call('ISteamUser.GetPlayerSummaries', steamids=ids)['response']['players'] 
    # get 1 specific profile (mostly for testing )
    # players = steam_api.call('ISteamUser.GetPlayerSummaries', steamids="76561198130753269")['response']['players']
    # build profile objects
    profiles = []
    for p in players:
        try:
            # profile is configured
            state = p["profilestate"]
        except:
            # profile is not configured
            state = 0
        try:
            # this attribute is missing from some profiles, unsure why
            tc = p["timecreated"]
        except:
            # handle gracefully
            tc = 0
        try:
            # create profile object
            profiles.append(Profile(
                    p["steamid"], p["communityvisibilitystate"], state,
                    p["personaname"], p["profileurl"], p["avatar"], tc))
        except Exception as e:
            # if no steam64id, discard
            if str(e) == "'steamid'":
                continue
    return profiles

# scan urls with google safebrowsing api
def scan_urls(urls):
    g_api = "https://safebrowsing.googleapis.com/v4/threatMatches:find"
    g_api_key = environ['GOOGLE_API_KEY']
    payload = {'client':{'clientId': "wtfender_steam_link_check", 'clientVersion': "0.1"},'threatInfo': {
                        'threatTypes': ["SOCIAL_ENGINEERING", "MALWARE", "UNWANTED_SOFTWARE",
                                        "POTENTIALLY_HARMFUL_APPLICATION", "THREAT_TYPE_UNSPECIFIED"],
                        'platformTypes': ["ANY_PLATFORM"],
                        'threatEntryTypes': ["URL"],
                        'threatEntries': urls}}
    params = {'key': g_api_key}
    # return threat matches
    return requests.post(g_api, params=params, json=payload).json()

# update urls with threat info
def check_urls(urls, cnx, c):
    # convert urls list to dict
    entries = []
    for url in urls:
        entries.append({"url": url})
    try:
        # submit urls to be scanned, returns threat matches
        for match in scan_urls(entries)['matches']:
            # commit updated link threat info to db
            c.execute("UPDATE links SET is_threat = 1, threatType = %s, threatEntryType = %s WHERE url = %s",
                        (match['threatType'], match['threatEntryType'], match['threat']['url']))
            cnx.commit()
    except KeyError as e:
        # no matches, handle gracefully
        if str(e) == "'matches'":
            pass
    cnx.close()

# get links, return urls
def get_links(profiles, cnx, c):
    profile_links = []
    for p in profiles:
        # if profile is configured and public
        if p.profilestate == 1 and p.communityvisibilitystate == 3:
            # get attributes from community profile 
            p.summary, p.vacBanned, p.tradeBanState = get_community_profile(p.steamid)
            # remove special chars
            if p.summary:
                p.summary = p.summary.encode("ascii", errors="ignore")
            if p.personaname:
                p.personaname = p.personaname.encode("ascii", errors="ignore")
        # commit profile to db
        c.execute("INSERT INTO profiles (steamid, communityvisibilitystate, profilestate, personaname, profileurl, avatar, timecreated, summary, vacBanned, tradeBanState) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) "
                    "ON DUPLICATE KEY UPDATE updated_at=NOW()",
                    (p.steamid, p.communityvisibilitystate, p.profilestate, p.personaname, p.profileurl, p.avatar, p.timecreated, p.summary, p.vacBanned, p.tradeBanState))
        cnx.commit()
        # find links in summary
        if p.summary is not None:
            for l in find_links(p.summary, p.steamid, cnx, c):
                profile_links.append(l)
    return profile_links

def main():
    # connect to database (connection, cursor)
    cnx, c = connect_db()
    # get steam profiles (100 max at a time)
    profiles = get_profiles(100)
    # find links in profile summaries, write to db
    profile_links = get_links(profiles, cnx, c)
    # check if urls are malicious, write to db
    check_urls(profile_links, cnx, c)
    # print scan info
    print "%s: Scanned %s profiles and %s links." % (datetime.now(), len(profiles), len(profile_links))

if __name__ == "__main__":
    main()
