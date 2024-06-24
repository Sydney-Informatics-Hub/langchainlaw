from langchainlaw.langchainlaw import Classifier
import json


def test_classifier(files, headers):
    """Smoke test for Classifier class"""
    with open(files["config"], "r") as fh:
        cf = json.load(fh)
        classifier = Classifier(cf)
        assert classifier.headers == headers
