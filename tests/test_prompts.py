from langchainlaw.prompts import parse_llm_json, PromptException
from langchainlaw.classifier import Classifier
import json
import pytest


def test_quoted_json(variants_of_json):
    for case in variants_of_json:
        parsed = parse_llm_json(case["string"])
        assert parsed == case["json"]


def test_make_prompt(files):
    with open(files["config"], "r") as fh:
        cf = json.load(fh)
    classifier = Classifier(cf)
    classifier.load_prompts(files["prompts"])

    with pytest.raises(PromptException):
        prompt = classifier.prompts.prompt("dates")
        classifier.prompts.make_message(prompt)
