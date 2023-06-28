import argparse
import json
from pathlib import Path
from langchain.llms import OpenAI
from openpyxl import Workbook


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
    ap.add_argument(
        "--test",
        action="store_true",
        default=False,
        help="Run without making calls to OpenAI, for testing prompts",
    )
    ap.add_argument(
        "--output",
        default="./results.xlsx",
        type=Path,
        help="Output spreadsheet",
    )
    args = ap.parse_args()
    cf = load_config(args.config)
    prompts = load_prompts(cf["PROMPTS"])
    llm = OpenAI(
        openai_api_key=cf["OPENAI_API_KEY"],
        openai_organization=cf["OPENAI_ORGANIZATION"],
        temperature=cf["TEMPERATURE"],
    )

    workbook = Workbook()
    worksheet = workbook.active

    worksheet.append(["file", "mnc"] + [p.name for p in prompts])

    for jsonfile in Path(cf["JUDGMENTS"]).glob("*.json"):
        metadata, judgment = load_case(jsonfile)
        print("Case: " + metadata["mnc"])
        results = [str(jsonfile), metadata["mnc"]]
        for prompt in prompts:
            prompt_str = prompt.make_prompt(metadata, judgment[:10])
            if args.test:
                results.append(prompt_str)
            else:
                result = llm(prompt_str)
                results.append(result)
        worksheet.append(results)

    workbook.save(args.output)


if __name__ == "__main__":
    classify()
