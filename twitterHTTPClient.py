#!/usr/bin/env python
# Columbia EECS E6893 Big Data Analytics
"""
This module is used to pull data from twitter API and send data to
the Tweet ingestion process using a socket connection. It acts as a
client of the Twitter API and a server of spark streaming conducted
in the Tweet ingestion. It open a listening TCP server socket and listens
to any connection from TCP client. After a connection established, it send
Tweet json streaming data to it.
"""

from tweepy import OAuthHandler
from tweepy import Stream
from tweepy.streaming import StreamListener
import socket

# credentials
ACCESS_TOKEN = '114718581-BKgrfcxaTWxbxBzK6ECcoHjnCuTaMfUOJXDT9Y3X'     # your access token
ACCESS_SECRET = 'lcmjmZpdNTRMDwRr4lh2XmTMFzAuTiHk26uhfprQcWzBe'         # your access token secret
CONSUMER_KEY = 'qApUFBNnJEEHunllrBambhvKM'                              # your API key
CONSUMER_SECRET = 'ncgp243EMzcsSdjouJiN95hSz0qGq5i4rZjk4VzmuD2AAVKyYM'  # your API secret key

# location bounding boxes to track
LOCATION_NYC = [-74, 40, -73, 41]
LOCATION_SEATTLE = [-122.423917, 47.803539, -121.899584, 47.465533]
LOCATION_WEST_COAST = [-124.401491, 32.499675, -114.082156, 42.004921]
LOCATION_LA = [-118.899385, 33.602971, -117.082033, 34.271299]
LOCATION_US = [-124.782852, 24.431378,  -66.833928, 49.480390]
LOCATIONS = LOCATION_US

DELIMITER = '::'


class TweetsListener(StreamListener):
    """
    tweets listener object
    """
    def __init__(self, csocket):
        self.client_socket = csocket
        self.transmit_cnt = 0

    def on_data(self, data):
        try:
            data_to_send = data.replace(DELIMITER, '') + DELIMITER
            self.client_socket.send(data_to_send.encode('utf-8'))
            self.transmit_cnt += 1
            print(data_to_send.encode('utf-8'))
            print("Total Transmit Count: {}".format(self.transmit_cnt))
            return True
        except BaseException as e:
            print("Error on_data: %s" % str(e))
            return False

    def on_error(self, status):
        print("Error: status=" + str(status))
        return False


class TwitterClient:
    def __init__(self, tcp_ip, tcp_port, locations):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind((tcp_ip, tcp_port))
        self.locations = locations

    def run(self):
        try:
          self.socket.listen(1)
          while True:
            print("Waiting for TCP connection...")
            conn, addr = self.socket.accept()
            print("Connected. Starting to receive tweets...")
            self.send_data(conn)
            conn.close()
        except KeyboardInterrupt:
          exit

    def send_data(self, socket_connection):
        """
        send data to socket
        """
        auth = OAuthHandler(CONSUMER_KEY, CONSUMER_SECRET)
        auth.set_access_token(ACCESS_TOKEN, ACCESS_SECRET)
        twitter_stream = Stream(auth, TweetsListener(socket_connection))
        twitter_stream.filter(locations=self.locations, languages=['en'])


if __name__ == '__main__':
    client = TwitterClient("localhost", 9001, LOCATIONS)
    client.run()
