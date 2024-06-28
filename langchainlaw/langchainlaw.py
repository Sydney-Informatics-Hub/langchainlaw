import argparse
import json
from pathlib import Path
from openpyxl import Workbook

from langchainlaw.classifier import Classifier


def cli():
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
        "--case",
        default="",
        type=str,
        help="Select a single case by its filename",
    )
    ap.add_argument(
        "--prompt",
        default="",
        type=str,
        help="Generate results from only one prompt",
    )

    args = ap.parse_args()

    with open(args.config, "r") as cfh:
        config = json.load(cfh)

    workbook = Workbook()
    worksheet = workbook.active

    classifier = Classifier(config)

    if args.prompt:
        if not classifier.prompts.prompt(args.prompt):
            print(f"No prompt defined with name '{args.prompt}'")
            return

    if args.prompt:
        headers = ["file", "mnc", args.prompt]
    else:
        headers = classifier.headers
    worksheet.append(headers)

    if args.case:
        case = Path(config["input"]) / Path(args.case)
        if not case.is_file():
            print(f"Case file {args.case} not found")
            return
        cases = [case]
    else:
        cases = Path(config["input"]).glob("*.json")

    for casefile in cases:
        results = classifier.classify(casefile, test=args.test, one_prompt=args.prompt)
        cols = classifier.as_columns(results)
        worksheet.append(cols)

    spreadsheet = config["output"]
    if args.test:
        print(f"Writing sample prompts to {spreadsheet}")
    else:
        print(f"Writing results to {spreadsheet}")
    workbook.save(spreadsheet)


if __name__ == "__main__":
    cli()
