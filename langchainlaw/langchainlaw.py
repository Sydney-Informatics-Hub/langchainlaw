import argparse
import json
import sys
import time
from pathlib import Path
from langchain.chat_models import ChatOpenAI
from openpyxl import Workbook


from langchainlaw.prompts import CaseChat


def load_config(cf_file):
    with open(cf_file, "r") as fh:
        cf = json.load(fh)
        return cf


def load_case(casefile):
    with open(casefile, "r") as file:
        return json.load(file)


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
    cf = load_config(args.config)
    prompts = CaseChat(cf["PROMPTS"])
    if args.prompt:
        if not prompts.prompt(args.prompt):
            print(f"No prompt defined with name '{args.prompt}'")
            sys.exit()
    chat = None
    if not args.test:
        chat = ChatOpenAI(
            model_name=cf["OPENAI_CHAT_MODEL"],
            openai_api_key=cf["OPENAI_API_KEY"],
            openai_organization=cf["OPENAI_ORGANIZATION"],
            temperature=cf["TEMPERATURE"],
        )

    rate_limit = cf.get(cf["RATE_LIMIT"], 5)
    spreadsheet = cf["OUTPUT"]

    workbook = Workbook()
    worksheet = workbook.active

    if not args.prompt:
        worksheet.append(["file", "mnc"])  # fixme headers

    if args.case:
        case = Path(cf["INPUT"]) / Path(args.case)
        if not case.is_file():
            print(f"Case file {args.case} not found")
            sys.exit()
        cases = [case]
    else:
        cases = Path(cf["INPUT"]).glob("*.json")

    for casefile in cases:
        judgment = load_case(casefile)
        print("Case: " + judgment["mnc"])
        row = [str(casefile), judgment["mnc"]]

        system_prompt = prompts.start_chat()

        if not args.test:
            response = chat([system_prompt])

        for prompt in prompts.next_prompt(judgment):
            print(f"Prompt {prompt.name}")
            message = prompt.message(judgment)
            try:
                if args.test:
                    response = prompt.mock_response()
                else:
                    response = chat([message])
                results = prompt.parse_response(response.content)
            except Exception as e:
                results = prompt.wrap_error(str(e))
            if args.prompt:
                print(results)
            else:
                row += results
            print(f"Sleeping {rate_limit}")
            time.sleep(rate_limit)
        if not args.prompt:
            worksheet.append(row)

    if not args.prompt:
        workbook.save(spreadsheet)


if __name__ == "__main__":
    classify()
