#!/usr/bin/env python3
from steam_scanner.steam_scanner import scan_profiles, get_scan_details
from flask import Flask, jsonify, request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from os import environ
import logging
import redis

# redis credentials
redis_host = environ.get("REDIS_HOST")
redis_port = environ.get("REDIS_PORT")
redis_pass = environ.get("REDIS_PASS")

red = redis.StrictRedis(host=redis_host, port=redis_port,
                        password=redis_pass, charset="utf-8", decode_responses=True)
app = Flask(__name__)
limiter = Limiter(app, key_func=get_remote_address, storage_uri="redis://:%s@%s:%s" %
                                                    (redis_pass, redis_host, redis_port))
log = logging.getLogger(__name__)
json_ct = {'Content-Type': 'application/json'}

def error_handler():
    return app.config.get("DEFAULT_ERROR_MESSAGE")

# scan profile batch
@app.route("/api/scan/batch")
def api_scan_batch():
    # internal gae header
    if request.headers.get('X-Appengine-Cron'):
        try:
            # batch of 100 random profiles
            scan = scan_profiles(100)
            print(get_scan_details(scan))
            return scan, json_ct
        except Exception as e:
            log.exception(e)
            return jsonify({"error": "unable to complete scan"})
    else:
        return jsonify({"error": "unauthorized"})


# scan one steam64id
@app.route("/api/scan/<steamid>")
# limit to 10/minute per ip
@limiter.limit("10/minute", error_message=error_handler)
def api_scan_steamid(steamid):
    try:
        # check format & sanitize input
        if len(steamid) == 17:
            steamid = str(int(steamid))
            # check cache, otherwise scan
            if red.exists(steamid):
                scan = red.get(steamid)
                print("Served from cache: %s" % get_scan_details(scan))
                return scan, json_ct
            else:
                scan = scan_profiles(steamid)
                print(get_scan_details(scan))
                # update cache
                red.set(steamid, scan)
                return scan, json_ct
        # status
        elif steamid == "status":
            return jsonify({"status": True})    
    except Exception as e:
        log.exception(e)
        return jsonify({"error": "unable to complete scan"})
    return jsonify({"error": "incorrect format"})


if __name__ == '__main__':
    # local dev server
    app.run(host='0.0.0.0', port=8080, debug=True)