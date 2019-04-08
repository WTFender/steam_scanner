#!/usr/bin/env python3
from steam_scanner.steam_scanner import scan_profiles, print_scan_details
from flask import Flask, jsonify
import logging

app = Flask(__name__)
log = logging.getLogger(__name__)
json_ct = {'Content-Type': 'application/json'}


# scan profiles
@app.route("/api/scan/<steamid>")
def api_scan_batch(steamid):
    try:
        # batch of 100 random profiles
        if steamid == "batch":
            scan = scan_profiles(100)
            log.info(print_scan_details(scan))
            return scan, json_ct
        # one steam64id
        elif len(steamid) == 17:
            # check format & sanitize input
            steamid = str(int(steamid))
            scan = scan_profiles(steamid)
            log.info(print_scan_details(scan))
            return scan, json_ct    
    except Exception as e:
        log.exception(e)
        return jsonify({"error": "unable to complete scan"})
    return jsonify({"error": "incorrect format"})


if __name__ == '__main__':
    # local dev server
    app.run(host='0.0.0.0', port=8080, debug=True)