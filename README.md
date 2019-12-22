# Social Hotspots Detection

## Introduction

The widespread usage of social media platforms can provide much insight into activity occurring in real-time around the
world. Much of this user-generated content is tagged with geo-location data either with explicit gps coordinates or
implicitly from other location metadata. This can be leveraged to detect and classify clusters of emerging social activity,
or hotspots. Classifying the hotspots into discrete categories and sentiment further adds context to the nature of the
activity. There are numerous applications to this type of system including news, situational awareness, crime detection
and response, advertising and much more. This repository provides the necessary code required to generate such a system
and ultimately be able to visualize the results via a web application in the browser.

## Instructions

Setup

Sensitive code such as api keys in the `auth` folder and other miscellaneous files such as generated code
have not been uploaded to the repository. You will need to create an auth folder and add a globals.py
script with the code filled out:

```
#!/usr/bin/env python

def init():
    global TWITTER_ACCESS_TOKEN
    TWITTER_ACCESS_TOKEN = # your access token

    global TWITTER_ACCESS_SECRET
    TWITTER_ACCESS_SECRET = # your access token secret

    global TWITTER_CONSUMER_KEY
    TWITTER_CONSUMER_KEY = # your API key

    global TWITTER_CONSUMER_SECRET
    TWITTER_CONSUMER_SECRET = # your API secret key
```

Also, when setting up the hotspots_crontab, you will need to modify the paths to match your environment. e.g. for the
GOOGLE_APPLICATION_CREDENTIALS environment variable.

Lastly, you will need to have your GCP credentials whitelisted in order to be able to read/write to BigQuery.

Excecution

- `./categoryClassifierCommand train` - The classifier joblib file was too large to upload to GitHub so you must first
train the classifier before starting the system. data/uci-news-aggregator.csv file is used as the input file.

- `./start` - Run a bash script to start the system. This will connect to the Twitter API, ingest and persist relevant tweets,
and generate social hotspots. Note, you may have to manually open crontab and save if your system did not install it
correctly from the start script.

- `./stop` - Run a bash script script to stop the system.

- `./manage.py runserver` - Start the web server in order to serve the visualization web application.

- `http://localhost:8000/hotspots` - on a web browser to connect to the web server and begin visualizing the tweet heatmap,
hotspot map markers via the Google Maps API.
