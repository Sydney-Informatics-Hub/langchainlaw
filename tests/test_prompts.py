from langchainlaw.prompts import parse_llm_json


def test_quoted_json(variants_of_json):
    for case in variants_of_json:
        parsed = parse_llm_json(case["string"])
        assert parsed == case["json"]
