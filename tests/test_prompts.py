import json
import pytest
import random
#from langchain.schema import HumanMessage #No longer work as of 20251210, see Tariq-Imran at https://github.com/langchain-ai/langchain/issues/8527
from langchain_core.messages import HumanMessage #Added non 20251210

from langchainlaw.prompts import parse_llm_json, PromptException
from langchainlaw.classifier import Classifier


def test_quoted_json(variants_of_json):
    for case in variants_of_json:
        parsed = parse_llm_json(case["string"])
        assert parsed == case["json"]


def test_make_prompt(files):
    random.seed(1)  # fixed page numbers
    with open(files["config"], "r") as fh:
        cf = json.load(fh)
    classifier = Classifier(cf)
    classifier.load_prompts(files["prompts"])

    # can't make a message until you've loaded a judgment
    with pytest.raises(PromptException):
        prompt = classifier.prompt("dates")
        classifier.make_message(prompt)

    with open(files["case"], "r") as file:
        classifier.judgment = json.load(file)

    prompt = classifier.prompt("dates")
    message = classifier.make_message(prompt)
    assert type(message) is HumanMessage

    with open(files["expect_dates_prompt"], "r") as fh:
        expect_dates_prompt = fh.read()
    got_prompt = message.content

    assert got_prompt.strip() == expect_dates_prompt.strip()
