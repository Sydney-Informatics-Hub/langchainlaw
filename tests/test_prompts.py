from langchainlaw.prompts import parse_llm_json
from langchainlaw.classifier import Classifier
import json


def test_quoted_json(llm_json):
    for case in llm_json:
        parsed = parse_llm_json(case["string"])
        assert parsed == case["json"]


def test_accidental_lists(files, executor):
    """Make sure that a prompt which expects a single object can cope when
    the LLM gives it a list containing an object"""
    with open(files["config"], "r") as fh:
        cf = json.load(fh)
    classifier = Classifier(cf)
    prompt = classifier.prompts.prompt("executor")
    for name, case in executor.items():
        parsed = prompt.parse_response(case["response"])
        print(parsed)
        assert parsed == case["expect"]
