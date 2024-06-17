from langchainlaw.langchainlaw import Classifier
import json


def test_classifier():
    """Smoke test for classifier class"""
    with open("tests/config.json", "r") as fh:
        cf = json.load(fh)
        classifier = Classifier(cf)
        assert classifier.headers
