import argparse
import json
import sys
import os
import time
from pathlib import Path
from langchain_openai import AzureChatOpenAI
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
    prompts = CaseChat()

    if not prompts.load_yaml(cf["PROMPTS"]):
        sys.exit()

    if args.prompt:
        if not prompts.prompt(args.prompt):
            print(f"No prompt defined with name '{args.prompt}'")
            sys.exit()
    chat = None
    if not args.test:
        llm_cf = cf["LLM"]["USYD_AZURE"]
        # fixme drop in other models here
        os.environ["AZURE_OPENAI_API_KEY"] = llm_cf["API_KEY"]
        os.environ["AZURE_OPENAI_ENDPOINT"] = llm_cf["ENDPOINT"]
        os.environ["AZURE_OPENAI_API_VERSION"] = llm_cf["API_VERSION"]
        os.environ["AZURE_OPENAI_CHAT_DEPLOYMENT_NAME"] = llm_cf["DEPLOYMENT"]
        chat = AzureChatOpenAI(
            azure_deployment=llm_cf["DEPLOYMENT"],
            openai_api_version=llm_cf["API_VERSION"],
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
            print(f"Case file {case} not found")
            sys.exit()
        cases = [case]
    else:
        cases = Path(cf["INPUT"]).glob("*.json")

    for casefile in cases:
        prompts.judgment = load_case(casefile)
        print("Case: " + prompts.judgment["mnc"])
        row = [str(casefile), prompts.judgment["mnc"]]

        system_prompt = prompts.start_chat()

        if not args.test:
            response = chat([system_prompt])

        for prompt in prompts.next_prompt():
            if not args.prompt or prompt.name == args.prompt:
                message = prompts.message(prompt)
                try:
                    if args.test:
                        response = prompt.mock_response()
                    else:
                        response = chat([message]).content
                    results = prompt.parse_response(response)
                except Exception as e:
                    results = prompt.wrap_error(str(e))
                if args.prompt:
                    print(results)
                else:
                    row += results
                if not args.test:
                    print(f"Sleeping {rate_limit}")
                    time.sleep(rate_limit)
        if not args.prompt:
            worksheet.append(row)

    # fixme - append to a CSV and then write to spreadsheet?
    if not args.prompt:
        if args.test:
            print(f"Writing sample prompts to {spreadsheet}")
        else:
            print(f"Writing results to {spreadsheet}")
        workbook.save(spreadsheet)


if __name__ == "__main__":
    classify()
