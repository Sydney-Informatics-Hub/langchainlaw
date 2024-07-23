from langchainlaw.prompts import parse_llm_json
from langchainlaw.generate_prompts import process_prompts

import json


def test_quoted_json(variants_of_json):
    for case in variants_of_json:
        parsed = parse_llm_json(case["string"])
        assert parsed == case["json"]


def test_load_spreadsheet(files):
    prompts = process_prompts(files["prompt_spreadsheet"])
    with open(files["prompt_json"], "r") as fh:
        expect_prompts = json.load(fh)
    assert prompts is not None
    assert prompts == expect_prompts
