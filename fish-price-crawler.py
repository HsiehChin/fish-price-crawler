import time
import json
import click
import requests
import datetime
from bs4 import BeautifulSoup

from config.config import Config

# db config
CONFIG = Config()
DB = CONFIG.db
FISH_PRICE = DB["marketDB"]["fishPrice"]

with open("./market.json", "r+", encoding="utf-8") as file:
    MARKET_ID = json.load(file)

# crawler config
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36\
        (KHTML, like Gecko) Chrome/72.0.3626.121 Safari/537.36"
}
URL = "https://efish.fa.gov.tw/efish/statistics/daysinglemarketmultifish.htm"


def common_era_to_republic_era(date):
    """Convert common era to republic era.

    Args:
        date: Current date.

    Returns:
        A date string which is republic era.
        For example:
        "1999.08.10"
    """
    republic_era = date.replace(year=date.year - 1911)
    return republic_era.strftime("%Y.%m.%d")


def today():
    now = datetime.datetime.today()
    return common_era_to_republic_era(now)


def yesterday():
    yesterday = datetime.datetime.today() - datetime.timedelta(days=1)
    return common_era_to_republic_era(yesterday)


def get_data(date):
    """Collects fish price info on query date.

    Args:
        date: Query date.

    Retruns:
        None
    """
    cnt = 0
    for id in MARKET_ID:
        # get html doc from url
        date_list = date.split(".")
        query = {
            "dateStr": date,
            "calendarType": "tw",
            "year": date_list[0],
            "month": date_list[1],
            "day": date_list[2],
            "mid": id,
            "numbers": "999",
            "orderby": "w",
        }
        res = requests.post(URL, data=query, headers=HEADERS)
        soup = BeautifulSoup(res.text, "html.parser")
        # start parse
        tr = soup.find(id="ltable").find_all("tr")
        for tr_data in tr:
            td_list = tr_data.find_all("td")
            if len(td_list) == 0 or td_list[0].text == "合計":
                continue
            else:
                # clean the td_list
                for i in range(len(td_list)):
                    td_list[i] = td_list[i].text.replace(",", "").strip(" ")
                    if td_list[i] == "\n":
                        td_list[i] = "0"
                query = {
                    "code": int(td_list[0]),
                    "market": MARKET_ID[id],
                    "date": datetime.datetime(
                        int(date_list[0]) + 1911,
                        int(date_list[1]),
                        int(date_list[2]),
                        1,
                        0,
                        0,
                    ),
                }
                result = {
                    "code": int(td_list[0]),
                    "name": td_list[1],
                    "market": MARKET_ID[id],
                    "volume": float(td_list[5]),
                    "date": datetime.datetime(
                        int(date_list[0]) + 1911,
                        int(date_list[1]),
                        int(date_list[2]),
                        1,
                        0,
                        0,
                    ),
                    "price": {
                        "high": float(td_list[2]),
                        "mid": float(td_list[3]),
                        "low": float(td_list[4]),
                        "average": float(td_list[7]),
                    },
                    "fluctuationLimit": {
                        "volume": float(td_list[6]),
                        "price": float(td_list[8]),
                    },
                }
                FISH_PRICE.update_one(query, {"$set": result}, upsert=True)
                cnt += 1
    print(date)
    print("Update document: " + str(cnt))


# get oneday data
@click.group()
def cli1():
    pass


@cli1.command()
@click.option(
    "-d",
    "--date",
    default=datetime.datetime.today().strftime("%Y.%m.%d"),
    help="Query date",
)
def oneday(date):
    """ crawler for oneday data"""
    date = datetime.datetime.strptime(date, "%Y.%m.%d")
    if date.date() == datetime.datetime.today().date():
        get_data(today())
        get_data(yesterday())
    else:
        get_data(common_era_to_republic_era(date))


# get period data
@click.group()
def cli2():
    pass


@cli2.command()
@click.option(
    "-s",
    "--start_date",
    prompt="Start date(Please use A.D. ex: 2019.10.11)",
    help="Start date",
)
@click.option(
    "-e",
    "--end_date",
    prompt="End date(Please use A.D. ex: 2019.10.11)",
    help="End date",
)
def period(start_date, end_date):
    """ crawler for period data"""
    start_date = datetime.datetime.strptime(start_date, "%Y.%m.%d")
    end_date = datetime.datetime.strptime(end_date, "%Y.%m.%d")
    while start_date.date() <= end_date.date():
        get_data(common_era_to_republic_era(start_date))
        start_date += datetime.timedelta(days=1)
        time.sleep(10)


if __name__ == "__main__":
    cli = click.CommandCollection(sources=[cli1, cli2])
    cli()
