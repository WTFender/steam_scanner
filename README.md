# steam_scanner

## setup
1. register for api keys
    - [steam](https://steamcommunity.com/dev/apikey)
    - [google](https://developers.google.com/safe-browsing/v4/get-started)

2. set environment variables
    ```bash
    export MYSQL_USER="user"`
    export MYSQL_PASS="password"
    export MYSQL_HOST="host"
    export MYSQL_DB="database"
    export STEAM_API_KEY="api_key"
    export GOOGLE_API_KEY="api_key"
    ```

3. setup database
    ```bash
    python database_setup.py
    > Database tables created.
    ```
    
4. install requirements  
    ```bash
    pip install -r requirements.txt
    ```

## scan
1. run scan

   ```c
   python steam_scanner.py
   > 2019-04-05 01:57:07.325673: Scanned 59 profiles and 1 links.
   ```
2. repeat

    ```c
    while true;do python steam_scanner.py && sleep 120s;done
    > 2019-04-05 04:27:07.640805: Scanned 61 profiles and 0 links.
    > 2019-04-05 04:29:21.871832: Scanned 62 profiles and 0 links.
    > 2019-04-05 04:31:34.832634: Scanned 65 profiles and 2 links.
    ```
3. be mindful of [steam's api limitations](https://steamcommunity.com/dev/apiterms)

    ```c
    1 scan = 1 api call  
    1 api call = 100 profile scans [attempted]
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
| imgur.com@#%@!     | ...snip... |         0 | None          |         2 |
+--------------------+------------+-----------+---------------+-----------+
```

## visualize
![](https://i.imgur.com/qcW4o5e.png "wtfender's scan activity")
    