import argparse
import json
from pathlib import Path
from langchain.llms import OpenAI

from langchainlaw.prompts import load_prompts


def load_config(cf_file):
    with open(cf_file, "r") as fh:
        cf = json.load(fh)
        return cf


def load_case(jsonfile):
    with open(jsonfile, "r") as file:
        data = json.load(file)
    judgment = data.pop("judgment")
    return data, judgment


def classify():
    ap = argparse.ArgumentParser("langchain-law")
    ap.add_argument(
        "--config",
        default="./config.json",
        type=Path,
        help="Config file",
    )
    args = ap.parse_args()
    cf = load_config(args.config)
    prompts = load_prompts(cf["PROMPTS"])
    llm = OpenAI(
        openai_api_key=cf["OPENAI_API_KEY"],
        openai_organization=cf["OPENAI_ORGANIZATION"],
        temperature=cf["TEMPERATURE"],
    )

    rows = []

    for jsonfile in Path(cf["JUDGMENTS"]).glob("*.json"):
        metadata, judgment = load_case(jsonfile)
        print("Case: " + metadata["mnc"])
        results = {}
        for prompt in prompts:
            prompt_str = prompt.make_prompt(metadata, judgment[:10])
            print(f"--\n{prompt.name}:\n{prompt_str}\n")
            results[prompt.name] = llm(prompt_str)
        rows.append(results)
    print(rows)


if __name__ == "__main__":
    classify()
