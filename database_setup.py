#!/usr/bin/env python
from os import environ
import mysql.connector

# set your database credentials
db_user = environ["MYSQL_USER"]
db_pass = environ["MYSQL_PASS"]
db_host = environ["MYSQL_HOST"]
db_db = environ["MYSQL_DB"]
db_cert = environ["MYSQL_CERT"]
db_key = environ["MYSQL_KEY"]
db_ca = environ["MYSQL_CA"] 

cnx = mysql.connector.connect(user=db_user, password=db_pass, host=db_host, database=db_db,
                                ssl_cert=db_cert, ssl_key=db_key, ssl_ca=db_ca)
c = cnx.cursor()

c.execute("CREATE TABLE IF NOT EXISTS profiles ("
                "steamid VARCHAR(17) PRIMARY KEY,"
                "communityvisibilitystate INT,"
                "profilestate INT,"
                "personaname TINYTEXT,"
                "profileurl TINYTEXT,"
                "avatar TINYTEXT,"
                "timecreated INT(10),"
                "summary TEXT,"
                "vacBanned INT,"
                "tradeBanState TINYTEXT,"
                "updated_at TIMESTAMP NOT NULL DEFAULT NOW() ON UPDATE NOW(),"
                "created_at TIMESTAMP NOT NULL DEFAULT NOW())")
cnx.commit()

c.execute("CREATE TABLE IF NOT EXISTS links ("
                "url VARCHAR(255) PRIMARY KEY,"
                "display TINYTEXT,"
                "tld TINYTEXT,"
                "domain TINYTEXT,"
                "subdomain TINYTEXT,"
                "threatEntryType TINYTEXT,"
                "threatType TINYTEXT,"
                "is_threat BOOL,"
                "updated_at TIMESTAMP NOT NULL DEFAULT NOW() ON UPDATE NOW(),"
                "created_at TIMESTAMP NOT NULL DEFAULT NOW())")
cnx.commit()

c.execute("CREATE TABLE IF NOT EXISTS profile_links ("
                "url VARCHAR(255),"
                "steamid VARCHAR(17),"
                "updated_at TIMESTAMP NOT NULL DEFAULT NOW() ON UPDATE NOW(),"
                "created_at TIMESTAMP NOT NULL DEFAULT NOW(),"
                "PRIMARY KEY (url, steamid),"
                "KEY url (url),"
                "KEY steamid (steamid),"
                "FOREIGN KEY (url) REFERENCES links (url) ON DELETE CASCADE,"
                "FOREIGN KEY (steamid) REFERENCES profiles (steamid) ON DELETE CASCADE)")
cnx.commit()
print("Database tables created.")
