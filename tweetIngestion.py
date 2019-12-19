#!/usr/bin/env python
# Columbia EECS E6893 Big Data Analytics
"""
This module creates a socket connection and listens for incoming tweets sent by the Twitter HTTP Client.
Then, it uses a spark streaming process to ingest the tweet, filter and batch write to BigQuery.
"""

from datetime import datetime
from google.cloud import bigquery
import json
import math
from pyspark import SparkConf, SparkContext
from pyspark.streaming import StreamingContext
from pyspark.sql import Row, SQLContext
import time


# output table and columns name
PROJECT_ID = 'intrepid-broker-253108'
OUTPUT_DATASET = 'bigdata_project'
OUTPUT_TABLE = 'tweets'

# parameter
IP = 'localhost'                # ip port
PORT = 9001                     # port
BATCH_INTERVAL = 60             # streaming batch interval in seconds
BOUNDING_BOX_THRESHOLD = 0.005  # magnitude of bounding box diagonal to consider as a place


def format_tweets(data_stream):
    """
    Process incoming Tweets and write to BQ Tweets table.
    """
    return data_stream\
        .flatMap(lambda line: list(filter(lambda x: x != '', line.split('::'))))\
        .map(lambda jsonstr: json.loads(jsonstr))\
        .filter(lambda jsonobj: get_coordinates(jsonobj) is not None)\
        .map(lambda jsonobj: {
            'id': jsonobj['id'],
            'created_at': parse_created_at(jsonobj['created_at']),
            'db_insert_time': datetime.utcnow(),
            'raw_text': get_text(jsonobj),
            'coord_lat': get_coordinates(jsonobj)['lat'],
            'coord_long': get_coordinates(jsonobj)['long']
        })


def parse_created_at(dateStr):
    """
    Parse Tweet str date format into python datetime
    """
    return datetime.strptime(dateStr, '%a %b %d %H:%M:%S +0000 %Y')


def get_text(twitterObj):
    """
    Get Tweet text from the data. Will resolve extended text (280 char limit) if available, or else it will
    default to using the legacy text (140 char limit).
    """
    if "extended_tweet" in twitterObj and twitterObj["extended_tweet"] is not None and\
            twitterObj["extended_tweet"]["full_text"] is not None and\
            len(twitterObj["extended_tweet"]["full_text"]) > 0:
        return twitterObj["extended_tweet"]["full_text"]
    return twitterObj["text"]


def get_coordinates(twitterObj):
    """
    Resolve (lat,lng) from the data if location metadata is available.
    Use exact coordinates if present.
    If the place field exists and a bounding box is present, use the midpoint of
    the bounding box if the diagonal length is <= BOUNDING_BOX_THRESHOLD
    """
    if twitterObj is None:
        return None

    if 'coordinates' in twitterObj and twitterObj['coordinates'] is not None and ['coordinates'] is not None and \
            twitterObj['coordinates']['type'] == 'Point':
        coord = twitterObj['coordinates']['coordinates']
        return {'lat': coord[1], 'long': coord[0]}

    if 'geo' in twitterObj and twitterObj['geo'] is not None and twitterObj['geo']['coordinates'] is not None and \
            twitterObj['geo']['type'] == 'Point':
        coord = twitterObj['geo']['coordinates']
        return {'lat': coord[0], 'long': coord[1]}

    if 'place' in twitterObj and twitterObj['place'] is not None and 'bounding_box' in twitterObj['place'] and \
            twitterObj['place']['bounding_box'] is not None:
        bbox = twitterObj['place']['bounding_box']
        if 'coordinates' in bbox:
            coords = bbox['coordinates'][0]
            if len(coords) == 4:
                long_diff = coords[1][0] - coords[2][0]
                lat_diff = coords[0][1] - coords[1][1]
                mag = math.sqrt(lat_diff ** 2 + long_diff ** 2)
                tl = coords[0]
                if mag <= BOUNDING_BOX_THRESHOLD:
                    coord = {'lat': tl[1] + lat_diff * 0.5, 'long': tl[0] + long_diff * 0.5}
                    return coord

    return None


def save_to_bigquery(rdd, cnt):
    """
    Saves tweets in rdd from stream to BQ
    """
    bq_client = bigquery.Client()
    table_ref = bq_client.dataset(OUTPUT_DATASET).table(OUTPUT_TABLE)
    table = bq_client.get_table(table_ref)
    rows = [x for x in rdd.collect()]
    num_rows = len(rows)
    cnt['cnt'] += num_rows
    if num_rows > 0:
        result = bq_client.insert_rows(table, rows)
        if not result:
            print('insert {0} rows to BQ successful: {1}, total insertions: {2}'.format(num_rows, rows, cnt['cnt']))
        else:
            print('insert {0} rows to BQ error: {1}'.format(num_rows, result))


if __name__ == '__main__':
    # Spark settings
    conf = SparkConf()
    conf.setMaster('local[2]')
    conf.setAppName("SocialHotspots")

    # create spark context with the above configuration
    sc = SparkContext(conf=conf)
    sc.setLogLevel("ERROR")

    # create sql context, used for saving rdd
    sql_context = SQLContext(sc)

    # create the Streaming Context from the above spark context with batch interval size BATCH_INTERVAL seconds
    ssc = StreamingContext(sc, BATCH_INTERVAL)
    # setting a checkpoint to allow RDD recovery
    ssc.checkpoint("~/checkpoint_SocialHotspots")

    # read data from port 9001
    data_stream = ssc.socketTextStream(IP, PORT)
    # data_stream.pprint()

    # write to Tweets table
    tweets = format_tweets(data_stream)
    cnt = {'cnt': 0}
    tweets.foreachRDD(lambda rdd: save_to_bigquery(rdd, cnt))

    ssc.start()

    while True:
        time.sleep(0.1)
