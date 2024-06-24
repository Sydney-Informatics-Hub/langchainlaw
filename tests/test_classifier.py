from langchainlaw.langchainlaw import Classifier
import json


def test_classifier(headers):
    """Smoke test for Classifier class"""
    with open("tests/config.json", "r") as fh:
        cf = json.load(fh)
        classifier = Classifier(cf)
        assert classifier.headers == headers
