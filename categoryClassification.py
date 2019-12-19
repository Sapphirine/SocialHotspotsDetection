#!/usr/bin/env python

import re
import nltk
nltk.download('stopwords')
nltk.download('wordnet')
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.feature_extraction.text import TfidfTransformer
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score
from sklearn.naive_bayes import MultinomialNB
from joblib import dump, load
from nltk.stem import PorterStemmer
import string
from wordsegment import load as wordSegmentLoad
from wordsegment import segment
import csv
from sklearn.pipeline import Pipeline
from sklearn.base import BaseEstimator, TransformerMixin
import numpy as np
import operator

wordSegmentLoad()

porter = PorterStemmer()
stemmer = WordNetLemmatizer()
stop_words = set(stopwords.words('english'))

TRAINING_INPUT_FILENAME = 'data/uci-news-aggregator.csv'
DEFAULT_PERSIST_FILENAME = 'categoryClassifier.joblib'
DEFAULT_CATEGORY_MAPPING = ["Business", "Entertainment", "Medicine", "Technology"]


class TweetClassifier:
    def __init__(self):
        self.training_input_filename = TRAINING_INPUT_FILENAME
        self.persist_filename = DEFAULT_PERSIST_FILENAME
        self.category_mapping = DEFAULT_CATEGORY_MAPPING
        self.trained_model = None

    def get_input_data(self):
        X = []
        Y = []
        with open(self.training_input_filename, newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                X.append(row['TITLE'])
                Y.append(row['CATEGORY'])
        return X, Y

    def train_model(self):
        print("Loading input file...")
        X, y = self.get_input_data()

        clf_pipeline = Pipeline([
            ('preprocess', PreprocessText()),
            ('vect', CountVectorizer(ngram_range=(1, 3))),
            ('tfidf', TfidfTransformer()),
            ('clf', MultinomialNB())
        ])

        print("Split training and test sets...")
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=0)

        print("Classifying...")
        clf_pipeline.fit(X_train, y_train)

        print("Predicting test set...")
        y_pred = clf_pipeline.predict(X_test)

        print(confusion_matrix(y_test,y_pred))
        print(classification_report(y_test,y_pred))
        print(accuracy_score(y_test, y_pred))

        print("Persisting classifier pipeline...")
        self.persist_model(clf_pipeline)

    def persist_model(self, model):
        self.trained_model = model
        dump(model, self.persist_filename)

    def load_model(self):
        try:
            self.trained_model = load(self.persist_filename)
        except Exception as e:
            print("Cannot load classifier model!", e)

    def predict(self, X, prob_threshold=None):
        y_pred_prob = self.trained_model.predict_proba(X)[0]
        index, value = max(enumerate(y_pred_prob), key=operator.itemgetter(1))
        if prob_threshold is None or value >= prob_threshold:
            return self.category_mapping[index]
        return None


class PreprocessText(BaseEstimator, TransformerMixin):
    """
    Transformer that preprocesses input text
    """
    def fit(self, X, y=None):
        return self

    def transform(self, X):
        output_documents = []
        for document in X:
            document = document.replace('\n',' ') # Remove line breaks
            document = document.replace('\r',' ')
            document = re.sub(r'http\S+', '', document) # Remove links
            document = re.sub(r'#\w+', PreprocessText.hashtag_replace, document)  # expand hashtags
            document = re.sub(r'[^a-zA-Z]', ' ', document)  # Remove everything other than letters
            document = re.sub(r'\s+[a-zA-Z]\s+', ' ', document) # rm single char
            document.translate(str.maketrans('', '', string.punctuation)) # Remove punctuation
            words = document.lower().split()  # Convert to lower case, split into individual words
            words = [w for w in words if not w in stop_words]  # Removing stopwords
            words = [porter.stem(w) for w in words] # Stemming
            document = " ".join(words)
            output_documents.append(document)

        return np.array(output_documents)

    def hashtag_replace(match):
        hashtag = match.group()[1:]
        hashtag = re.sub(r'[^a-zA-Z]', '', hashtag)
        return " ".join(segment(hashtag))
