# steam_scanner
python2/3 compatible

## demo
[wtfender.com/steam-scanner](https://wtfender.com/steam-scanner)

## setup

register for api keys
- [steam](https://steamcommunity.com/dev/apikey)
- [google](https://developers.google.com/safe-browsing)
```bash
# set environment variables
export MYSQL_USER="user"
export MYSQL_PASS="password"
export MYSQL_HOST="host"
export MYSQL_DB="database"
export MYSQL_CERT="SSL_CERT"
export MYSQL_KEY="SSL_KEY"
export MYSQL_CA="SSL_CA"
export STEAM_API_KEY="api_key"
export GOOGLE_API_KEY="api_key"

# clone project
git clone https://github.com/WTFender/steam_scanner.git && cd steam_scanner

# install requirements
pip install -r requirements.txt

# setup database
python database_setup.py
> Database tables created.
```


## scan

```bash
# run one scan
python steam_scanner.py
> 2019-04-06 14:31:42.309805: Scanned 1 profiles with 2 links containing 2 threats.

{
    "...snip...": 1,
    "links": [
        {
            "is_threat": 1,
            "threatType": "MALWARE",
            "url": "https://testsafebrowsing.appspot.com/s/malware.html"
        },
        {
            "is_threat": 1,
            "threatType": "SOCIAL_ENGINEERING",
            "url": "https://testsafebrowsing.appspot.com/s/phishing.html"
        }
    ],
    "personaname": "Mr. Cringer Pants",
    "...snip...": 1
}

# run more scans
while true; do python steam_scanner.py && sleep 120s; done
> 2019-04-06 15:12:54.184112: Scanned 51 profiles with 5 links containing 0 threats.
> 2019-04-06 15:13:19.837920: Scanned 58 profiles with 1 links containing 0 threats.
> 2019-04-06 15:13:41.044895: Scanned 65 profiles with 3 links containing 0 threats.

# be mindful of steam's api limitations
# 1 scan = 1 api call  
# 1 api call = 100 profile scans max
# 100,000 api call limit per day
```

## investigate

 ```sql
SELECT count(url) AS bad_links, threatType 
FROM links
WHERE is_threat=1
GROUP BY threatType;

+----------+--------------------+
| bad_links | threatType         |
+----------+--------------------+
|        1 | MALWARE            |
|        1 | SOCIAL_ENGINEERING |
|        2 | UNWANTED_SOFTWARE  |
+----------+--------------------+

SELECT p.personaname AS name, p.profileurl, count(pl.url) as bad_links
FROM links l
LEFT JOIN profile_links pl ON l.url=pl.url
LEFT JOIN profiles p ON pl.steamid=p.steamid
WHERE l.is_threat=1
GROUP BY pl.steamid;

+--------------------+------------+-----------+---------------+-----------+
| name               | profileurl | vacBanned | tradeBanState | bad_links |
+--------------------+------------+-----------+---------------+-----------+
| Mr. Cringer Pants  | ...snip... |         0 | None          |         2 |
| imgur.com@!)%)     | ...snip... |         0 | None          |         2 |
+--------------------+------------+-----------+---------------+-----------+
```

## visualize
graph mysql via [grafana](https://grafana.com/)

![](https://i.imgur.com/qcW4o5e.png "wtfender's scan activity")

## scale
deploy on [google app engine](https://cloud.google.com/appengine/)

```bash
# clone from source
git clone https://github.com/WTFender/steam_scanner.git && cd steam_scanner/gae/steam_scanner

# update secrets
nano secrets.yaml

# deploy on gae
gcloud projects create "project_name"
gcloud app deploy --project="project_name"

# enable scan job (100 profiles per minute)
gcloud app deploy cron.yaml --project="project_name"

# scan specific steamID
curl https://wtfender.com/api/scan/76561198130753269 | python -m json.tool

[
    {
        "personaname": "Mr. Cringer Pants",
        "profilestate": 1,
        "profileurl": "https://steamcommunity.com/id/cringerpants/",
        "...snip...": 1
    }
]
```
