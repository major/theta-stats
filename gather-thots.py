#!/usr/bin/env python
"""Retrieve data from thetagang.com about trades."""
import json
import time

from tinydb import TinyDB, where
import urllib3


HTTP_HEADERS = {
    "User-Agent": "mhayden's scripts",
    "Content-Type": "application/json"
}


def get_thots(symbol=None):
    """Get the current list of thots from the site."""
    http = urllib3.PoolManager()

    # Add a query string if we are looking up thots for a specific ticker.
    fields = {}
    if symbol:
        fields = {"ticker": symbol}

    # Make the request for JSON.
    r = http.request(
        'GET',
        'https://api.thetagang.com/thots',
        fields=fields,
        headers=HTTP_HEADERS
    )

    # Load just the thots data.
    raw_thots = json.loads(r.data.decode('utf-8'))
    return raw_thots["data"]["thots"]


def update_thots(db, symbol=None):
    """Update the database with the latest thots."""
    thots = get_thots(symbol)
    user_db = db.table("users")
    trade_db = db.table("trades")

    # Update the latest thots.
    update_users(user_db, [x["User"] for x in thots])
    update_trades(trade_db, [x["Trade"] for x in thots])


def update_trades(db, trade_thots):
    """Update the trade database with the latest data."""
    # Skip any thots that are comments and not an actual trade.
    for trade_thot in trade_thots:
        if trade_thot:
            trade_db.upsert(trade_thot, where("guid") == trade_thot["guid"])


def update_users(db, user_thots):
    """Update the user database with the latest data."""
    for user_thot in user_thots:
        user_db.upsert(user_thot, where("guid") == user_thot["guid"])


if __name__ == "__main__":
    # Set up the database and its tables.
    db = TinyDB('database/db.json')
    user_db = db.table("users")
    trade_db = db.table("trades")

    # Update the latest thots.
    update_thots(db)

    # Get a list of unique tickers from the database.
    tickers = {x["symbol"] for x in trade_db.all()}
    for ticker in sorted(tickers):
        time.sleep(15)
        print(f"> {ticker.ljust(4)}: Getting latest thots")
        # update_thots(db, ticker)