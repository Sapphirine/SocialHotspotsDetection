#!/usr/bin/env python

from categoryClassification import TweetClassifier
import sys

if __name__ == "__main__":
    clf = TweetClassifier()
    if sys.argv[1] == 'train':
        clf.train_model()
    elif sys.argv[1] == 'test':
        clf.load_model()
        cat = clf.predict([sys.argv[2]], prob_threshold=None)
        print("Category:", cat)
        cat = clf.predict([sys.argv[2]], prob_threshold=0.50)
        print("Category with Probability Threshold 0.50:", cat)
