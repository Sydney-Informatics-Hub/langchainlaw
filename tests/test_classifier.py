from langchainlaw.langchainlaw import Classifier
import json
from pathlib import Path


def test_classifier(files, headers):
    """Smoke test for Classifier class"""
    with open(files["config"], "r") as fh:
        cf = json.load(fh)
    classifier = Classifier(cf)
    assert classifier.headers == headers


def test_parse_results(files, headers, results, flat_results):
    with open(files["config"], "r") as fh:
        cf = json.load(fh)
    classifier = Classifier(cf)
    case = Path(files["case"])
    # note that there are results in the cache as fixtures so this doesn't
    # call the LLM
    got_results = classifier.classify(case, test=True)
    assert got_results == results
    got_flat = classifier.flatten(results)
    assert got_flat == flat_results
