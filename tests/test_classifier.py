from langchainlaw.langchainlaw import Classifier, parse_llm_json
import json


def test_classifier():
    """Smoke test for Classifier class"""
    with open("tests/config.json", "r") as fh:
        cf = json.load(fh)
        classifier = Classifier(cf)
        assert classifier.headers


def test_quoted_json(variants_of_json):
    for case in variants_of_json:
        parsed = parse_llm_json(case["string"])
        assert parsed == case["json"]
