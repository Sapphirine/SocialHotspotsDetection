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

- `./start` Run the start script to start the system. This will connect to the Twitter API, ingest and persist relevant tweets,
and generate social hotspots.

- `./stop` Run the stop script to stop the system.

- `python manage.py runwebserver` to start the web server in order to serve the visualization web application

- `http://localhost:8000` on a web browser to connect to the web server and begin visualizing the tweet heatmap,
hotspot map markers via the Google Maps API.

- Sensitive code such as api keys in the `auth` folder have not been uploaded to the repository.
