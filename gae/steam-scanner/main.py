#!/usr/bin/env python3
from steam_scanner.steam_scanner import scan_profiles
from flask import Flask, jsonify

app = Flask(__name__)
json_ct = {'Content-Type': 'application/json'}


# scan profiles
@app.route("/api/scan/<steamid>")
def api_scan_batch(steamid):
    # batch of 100 random profiles
    if steamid == "batch":
        return scan_profiles(100), json_ct
    # one steam64id
    try:
        # check format & sanitize input
        if len(steamid) == 17:
            steamid = str(int(steamid))
            return scan_profiles(steamid), json_ct
        else:
            raise Exception
    except:
        return jsonify({"error": "incorrect format"})


if __name__ == '__main__':
    # local dev server
    app.run(host='0.0.0.0', port=8080, debug=True)