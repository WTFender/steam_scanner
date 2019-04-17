#!/usr/bin/env python3
from steam.steamid import SteamID
from xml.etree import ElementTree
from bs4 import BeautifulSoup
from datetime import datetime
from random import randint
from steam import WebAPI
from os import environ
import sqlalchemy
import requests
import json
import re


class Profile:
    def __init__(self, steamid, communityvisibilitystate, profilestate,
                    personaname, profileurl, avatar, timecreated):
        self.steamid = steamid
        self.steamid_found = 1
        self.communityvisibilitystate = communityvisibilitystate
        self.profilestate = profilestate
        self.personaname = personaname
        self.profileurl = profileurl
        self.avatar = avatar
        self.timecreated = timecreated
        self.summary = None
        self.vacBanned = 0
        self.tradeBanState = None
        self.links = []


class Link:
    def __init__(self, url):
        self.url = url
        self.is_threat = 0
        self.threatType = None


# connect to database
def connect_db():
    # get database settings
    db_user = environ["MYSQL_USER"]
    db_pass = environ["MYSQL_PASS"]
    db_name = environ["MYSQL_NAME"]
    # db_host = "127.0.0.1" # for TCP connection, uncomment db_host, comment out db_proxy
    db_proxy = environ["MYSQL_PROXY"]
    db = sqlalchemy.create_engine(sqlalchemy.engine.url.URL(
            drivername='mysql+mysqlconnector',
            username=db_user,
            password=db_pass,
            database=db_name,
            # host=db_host), # for TCP connection, uncomment db_host, comment out query
            query={'unix_socket': '/cloudsql/{}'.format(db_proxy)}),
            poolclass=sqlalchemy.pool.NullPool)
    # return cursor
    return db.connect()


# get community profile info
def get_community_profile(steamid):
    links = []
    summary = None
    vacBanned = 0
    tradeBanState = None
    r = requests.get("https://steamcommunity.com/profiles/%s/?xml=1" % steamid)
    try:
        xml = ElementTree.fromstring(r.content)
    # gracefully handle empty/crazy profiles
    except Exception as e:
        # return empty
        return summary, vacBanned, tradeBanState, links 
    # find attributes in XML profile
    for child in xml:
        try:
            if child.tag == "summary":
                summary = child.text
            elif child.tag == "vacBanned":
                vacBanned = int(child.text)
            elif child.tag == "tradeBanState":
                if child.text != "None":
                    tradeBanState = child.text
        except Exception as e:
            print(e)
    if summary:
        for l in find_links(summary, steamid):
            links.append(Link(l))
    return summary, vacBanned, tradeBanState, links


# find links in summary
def find_links(summary, steamid):
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
            print(e)
            print(link)
            continue
        # connect to database
        db = connect_db()
        # commit link to db
        db.execute("INSERT INTO links (url, display) "
                    "VALUES (%s, %s) "
                    "ON DUPLICATE KEY UPDATE display=%s",
                    (url, link.text, link.text))
        # commit profile_link to db
        db.execute("INSERT IGNORE INTO profile_links (url, steamid) "
                    "VALUES (%s, %s)",
                    (url, steamid))
        db.close()
    return urls


def get_profiles(steamid):
    ids = ""
    # if arg is string, expect single steam64id
    if type(steamid) == str:
        ids = steamid
    # if arg is int, generate n random steam64ids
    elif type(steamid) == int:
        # [NEEDS IMPROVED]
        # this isn't random, nor conclusive method of generating steamids
        for i in range(0,steamid):
            ids = ids + ",%s" % SteamID(id=randint(1, 1000000000), 
                                        type="Individual", 
                                        universe="Public", 
                                        instance=1).as_64
    # get player info via steam WebAPI (100 max)
    s_api_key = environ['STEAM_API_KEY']
    steam_api = WebAPI(key=s_api_key)
    players = steam_api.call('ISteamUser.GetPlayerSummaries', steamids=ids)['response']['players'] 
    # return empty profile only for single steamid scan
    if not players and len(steamid) == 17:
        # empty profile
        p = Profile(steamid, 0, 0, 0, 0, 0, 0)
        p.steamid_found = False
        return [p]
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
            profiles.append(Profile(p["steamid"], p["communityvisibilitystate"], state,
                                    p["personaname"], p["profileurl"], p["avatar"], tc))
        except Exception as e:
            # if no steam64id, discard
            if str(e) == "'steamid'":
                continue
    # if profile is configured and public
    for p in profiles:
        if p.profilestate == 1 and p.communityvisibilitystate == 3:
            # get attributes from community profile 
            p.summary, p.vacBanned, p.tradeBanState, p.links = get_community_profile(p.steamid)
    # commit profiles to db
    for p in profiles:
        db = connect_db()
        db.execute("INSERT INTO profiles (steamid, communityvisibilitystate, profilestate, personaname, profileurl, avatar, timecreated, summary, vacBanned, tradeBanState) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) "
                    "ON DUPLICATE KEY UPDATE updated_at=NOW()",
                    (p.steamid, p.communityvisibilitystate, p.profilestate, p.personaname, p.profileurl, p.avatar, p.timecreated, p.summary, p.vacBanned, p.tradeBanState))
        db.close()
    return profiles


def check_profile_urls(profiles):
    urls = []
    for p in profiles:
        for l in p.links:
            urls.append(l.url)
    url_threats = check_urls(urls)
    # update profile links with threats
    for t in url_threats:
        for p in profiles:
            for l in p.links:
                if t['url'] == l.url:
                    l.is_threat = 1
                    l.threatType = t['threatType']
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
def check_urls(urls):
    threats = []
    # convert urls list to dict
    entries = []
    for url in urls:
        entries.append({"url": url})
    try:
        # submit urls to be scanned, returns threat matches
        for match in scan_urls(entries)['matches']:
            # connect to database
            db = connect_db()
            threats.append({"url": match['threat']['url'], "threatType": match['threatType']})
            # commit updated link threat info to db
            db.execute("UPDATE links SET is_threat = 1, threatType = %s, threatEntryType = %s WHERE url = %s",
                        (match['threatType'], match['threatEntryType'], match['threat']['url']))
            db.close()
    except KeyError as e:
        # no matches, handle gracefully
        if str(e) == "'matches'":
            pass
    return threats


# convert profiles to json string
def profiles_to_json_string(profiles):
    # convert objects to dicts
    dict_profiles = []
    for p in profiles:
        links = []
        for l in p.links:
            links.append(l.__dict__)
        p.links = links
        dict_profiles.append(p.__dict__)
    # convert dicts to json string
    return json.dumps(dict_profiles)


def scan_profiles(ids):
    # get profiles from steam
    profiles = get_profiles(ids)
    # updates profile links with threats
    profiles = check_profile_urls(profiles)
    # return profile with associated links
    return profiles_to_json_string(profiles)


def get_scan_details(scan):
    p_count = 0
    l_count = 0
    t_count = 0
    for profile in json.loads(scan):
        p_count += 1
        for l in profile['links']:
            l_count += 1
            if l['is_threat'] == 1:
                t_count += 1
    # return scan details string
    return (("%s: Scanned %s profiles with %s links containing %s threats.") %
                (datetime.now(), p_count, l_count, t_count))


def main():
    scan = scan_profiles(100)         # scan batch of random profiles (max 100)
    # scan = scan_profiles(steamid64) # or scan specific steamid64
    print(get_scan_details(scan))     # print scan details
    # print(scan)                     # print raw json


if __name__ == "__main__":
    main()
