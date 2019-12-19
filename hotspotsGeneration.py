#!/usr/bin/env python
# Columbia EECS E6893 Big Data Analytics
"""
Queries recent Tweets from BigQuery, runs DBSCAN, classification and
sentiment analysis to generate hotspots and write them to BigQuery.
"""

from categoryClassification import TweetClassifier
from collections import defaultdict
from datetime import datetime
from google.cloud import bigquery
import math
import re
from textblob import TextBlob
import uuid

# params
EPSILON = 0.002  # roughly equivalent to 200m
DENSITY_MIN_POINTS = 5
NOISE_LABEL = -1
TWEET_CREATION_TIME_AGO_THRESHOLD = 60 # tweet must have been created <= this threshold min ago to be considered
SENTIMENT_POLARITY_THRESHOLD = 0.0

# output table and columns name
PROJECT_ID = 'intrepid-broker-253108'
OUTPUT_DATASET = 'bigdata_project'
OUTPUT_TABLE = 'clusters'

TWEET_CLASSIFIER = TweetClassifier()
TWEET_CLASSIFIER.load_model()
CATEGORY_SELECTION_MIN_PROBABILITY = 0.50


class TwitterData:
    """
    Class to hold Tweet data queried from BigQuery.
    """
    def __init__(self, id, created_at, raw_text, coord_lat, coord_long):
        self.id = id
        self.created_at = created_at
        self.raw_text = raw_text
        self.coord = {'lat': float(coord_lat), 'long': float(coord_long)}

    def to_string(self):
        return "[TwitterData (id=" + str(self.id) + ")]"

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other):
        return other is not None and self.id == other.id

    def __str__(self):
        return self.to_string()

    def __repr__(self):
        return self.to_string()


class Hotspot:
    """
    Class to represent a Social Hotspot.
    """
    def __init__(self, id, tweets):
        self.id = id
        self.uuid = uuid.uuid4()
        self.tweets = tweets
        self.center = self.get_center()
        self.corpus = self.get_corpus()
        self.sentiment = get_sentiment(self.corpus)
        self.category = get_category(self.corpus)

    def get_center(self):
        lat_sum = 0
        long_sum = 0
        num_tweets = len(self.tweets)
        for tweet in self.tweets:
            lat_sum += tweet.coord['lat']
            long_sum += tweet.coord['long']
        return {'lat': lat_sum / num_tweets, 'long': long_sum / num_tweets}

    def get_corpus(self):
        return "\n".join([tweet.raw_text for tweet in self.tweets])

    def get_serialized_tweet_ids(self):
        return ",".join([tweet.id for tweet in self.tweets])

    def get_bigquery_row(self, insert_time):
        return {'id': str(self.uuid),
                'coord_lat': self.center['lat'],
                'coord_long': self.center['long'],
                'num_tweets': len(self.tweets),
                'tweets': self.get_serialized_tweet_ids(),
                'corpus': self.corpus,
                'sentiment': self.sentiment,
                'category': self.category,
                'db_insert_time': insert_time}

    def to_string(self):
        return "[Hotspot (id=" + \
               str(self.id) + \
               " center:" + str(self.get_center()) + \
               " num_tweets:" + str(len(self.tweets)) + \
               " sentiment:" + str(self.sentiment) + \
               " category:" + str(self.category) + ")]"

    def __str__(self):
        return self.to_string()

    def __repr__(self):
        return self.to_string()


def run_dbscan(tweet_data):
    """
    Runs the DBSCAN algorithm on tweet_data input and generates a list of Hotspot instances.
    """
    c = 0
    labels = defaultdict(lambda: None)
    for p in tweet_data:
        if labels[p] is not None:
            continue
        neighbors = get_neighbors(tweet_data, p)
        if len(neighbors) < DENSITY_MIN_POINTS:
            labels[p] = NOISE_LABEL
            continue
        c = c + 1
        labels[p] = c
        seed_set = neighbors - {p}
        for q in seed_set:
            if labels[q] == NOISE_LABEL:
                labels[q] = c
            if labels[q] is not None:
                continue
            labels[q] = c
            neighbors = get_neighbors(tweet_data, q)
            if len(neighbors) >= DENSITY_MIN_POINTS:
                seed_set.add(q)

    cluster_to_tweets = defaultdict(lambda: [])
    for tweet_data, cluster_id in labels.items():
        if cluster_id != NOISE_LABEL:
            cluster_to_tweets[cluster_id].append(tweet_data)

    hotspots = []
    for cluster_id, tweets in cluster_to_tweets.items():
        hotspots.append(Hotspot(cluster_id, tweets))

    return hotspots


def print_hotspots_with_text(hotspots):
    for hotspot in hotspots:
        print("hotspot: " + str(hotspot.id))
        for tweet in hotspot.tweets:
            print("tweet: " + tweet.raw_text + " coord: " + str(tweet.coord))
        print("")


def get_neighbors(tweet_data, p):
    """
    find neighbor tweets of p (according to coord distance)
    """
    neighbors = set()
    for q in tweet_data:
        if get_distance(p, q) <= EPSILON:
            neighbors.add(q)
    return neighbors


def get_distance(p, q):
    """
    distance between two tweet data (i.e. geographical distance between coordinates)
    """
    return math.sqrt((p.coord['lat'] - q.coord['lat']) ** 2 +
                     (p.coord['long'] - q.coord['long']) ** 2)


def get_sentiment(text):
    """
    Utility function to classify sentiment of passed tweet
    using textblob's sentiment method
    """
    analysis = TextBlob(clean_sentiment_text(text))
    if analysis.sentiment.polarity > SENTIMENT_POLARITY_THRESHOLD:
        return 'Positive'
    elif analysis.sentiment.polarity < -SENTIMENT_POLARITY_THRESHOLD:
        return 'Negative'
    else:
        return 'Neutral'


def clean_sentiment_text(text):
    """
    Utility function to clean tweet text by removing links, special characters
    using simple regex statements.
    """
    return ' '.join(re.sub("(@[A-Za-z0-9]+)|([^0-9A-Za-z \t]) | (\w+:\ / \ / \S+)", " ", text).split())


def get_category(text):
    """
    Function to resolve tweet category {business, entertainment, medicine, technology} or None
    Probability of winning category must be >= CATEGORY_SELECTION_MIN_PROBABILITY to be considered
    """
    X = [text]
    return TWEET_CLASSIFIER.predict(X, prob_threshold=CATEGORY_SELECTION_MIN_PROBABILITY)


def fetch_tweets_from_bigquery():
    bq_client = bigquery.Client()
    query_job = bq_client.query("""
        SELECT 
          id, created_at, raw_text, coord_lat, coord_long
        FROM `intrepid-broker-253108.bigdata_project.tweets`
        WHERE TIMESTAMP(created_at) >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(),INTERVAL {} MINUTE)
        ORDER BY created_at DESC
        LIMIT 100000
    """.format(TWEET_CREATION_TIME_AGO_THRESHOLD))
    result = query_job.result()
    data = [TwitterData(
        id=row['id'],
        created_at=row['created_at'],
        raw_text=row['raw_text'],
        coord_lat=row['coord_lat'],
        coord_long=row['coord_long']) for row in result]
    return data


def persist_hotspots(hotspots):
    """
    Saves hotspots to BigQuery
    """
    if len(hotspots) <= 0:
        print("No hotspots generated")
        return
    bq_client = bigquery.Client()
    table_ref = bq_client.dataset(OUTPUT_DATASET).table(OUTPUT_TABLE)
    table = bq_client.get_table(table_ref)

    print_hotspots_with_text(hotspots)

    insert_time = datetime.utcnow()
    rows = [hotspot.get_bigquery_row(insert_time) for hotspot in hotspots]
    result = bq_client.insert_rows(table, rows)
    if not result:
        print('insert rows to BQ successful: {}'.format(rows))
    else:
        print('insert rows to BQ error: {}'.format(result))


if __name__ == '__main__':
    print("{} Generating hotspots...".format(datetime.now()))
    tweets = fetch_tweets_from_bigquery()
    hotspots = run_dbscan(tweets)
    persist_hotspots(hotspots)
