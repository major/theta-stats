#!/usr/bin/env python
"""Retrieve data from thetagang.com about trades."""
from datetime import datetime
import json
import logging
import random
import time
import sys

from tinydb import TinyDB, where
import urllib3


HTTP_HEADERS = {
    "User-Agent": "mhayden's scripts",
    "Content-Type": "application/json"
}
RATELIMIT_REACHED = False
SLEEP_TIMER = 1


def get_thots(symbol=None, username=None):
    """Get the current list of thots from the site."""
    http = urllib3.PoolManager()

    # Add a query string if we are looking up thots for a specific ticker.
    fields = {}
    url = 'https://api.thetagang.com/thots'
    if symbol:
        fields = {"ticker": symbol}
    if username:
        fields = {"username": username}
        url = 'https://api.thetagang.com/trades'

    # Make the request for JSON.
    r = http.request(
        'GET',
        url,
        fields=fields,
        headers=HTTP_HEADERS,
        timeout=5.0
    )

    # Get the remaining rate limit.
    remaining_requests = r.headers['X-Ratelimit-Remaining']
    if int(remaining_requests) < 5:
        RATELIMIT_REACHED = True

    # Get date when rate limit resets.
    ratelimit_reset = int(r.headers['X-Ratelimit-Reset'])
    ratelimit_reset_date = datetime.utcfromtimestamp(
        ratelimit_reset
    ).strftime('%Y-%m-%d %H:%M:%S %z')

    # Log the rate limit information.
    logging.info(
        f"Remaining requests: {remaining_requests} "
        f"until {ratelimit_reset_date}"
    )

    # Load just the thots data.
    raw = json.loads(r.data.decode('utf-8'))
    if username:
        return raw["data"]["trades"]

    return raw["data"]["thots"]


def update_thots(db, symbol=None, username=None):
    """Update the database with the latest thots."""
    thots = get_thots(symbol=symbol, username=username)
    user_db = db.table("users")
    trade_db = db.table("trades")

    # Update the latest thots.
    if username:
        update_trades(trade_db, thots)
        return

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
    # Configure logging.
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s"
    )

    # Set up the database and its tables.
    db = TinyDB(
        'database/db.json',
        sort_keys=True,
        indent=4,
        separators=(',', ': ')
    )
    user_db = db.table("users")
    trade_db = db.table("trades")

    # Update the latest thots.
    logging.info("🤔 Getting the most recent thots")
    update_thots(db)

    # Get a list of unique tickers from the database.
    tickers = {x["symbol"] for x in trade_db.all()}
    for ticker in sorted(tickers, key=lambda _: random.random()):
        logging.info(f"😴 Sleeping for {SLEEP_TIMER} seconds.")
        time.sleep(SLEEP_TIMER)
        logging.info(f"🚚 {ticker.ljust(4)}: Getting latest thots")
        if not RATELIMIT_REACHED:
            update_thots(db, symbol=ticker)
        else:
            print("Reached the rate limit. exiting now.")
            sys.exit()

    # Get a list of unique users from the database.
    # users = {x["username"] for x in user_db.all()}
    # for user in sorted(users, key=lambda _: random.random()):
    #     logging.info(f"😴 Sleeping for {SLEEP_TIMER} seconds.")
    #     time.sleep(SLEEP_TIMER)
    #     logging.info(f"🚚 Getting latest thots from {user.ljust(4)}")
    #     update_thots(db, username=user)
