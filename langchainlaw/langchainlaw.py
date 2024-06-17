import argparse
import json
import sys
import time
from pathlib import Path
from langchain.chat_models import ChatOpenAI
from openpyxl import Workbook


from langchainlaw.prompts import CaseChat
from langchainlaw.cache import Cache


def load_config(cf_file):
    with open(cf_file, "r") as fh:
        cf = json.load(fh)
        return cf


def load_case(casefile):
    with open(casefile, "r") as file:
        return json.load(file)


def run_prompt(
    chat, prompts, prompt, test=False, rate_limit=5, cache=None, case_id=None
):
    """Actually send prompt to LLM, unless there's already a response in the
    cache.

    response == what we get back from the LLM (text or json)
    results == a list of values to be written into the spreadsheet

    The cache is response, not results - if we read from the cache we re-parse
    the response if required (for json prompts)

    """
    message = prompts.message(prompt)
    try:
        if test:
            response = prompt.mock_response()
        else:
            if cache:
                response = cache.read(case_id, prompt.name)
            if response is None:
                response = chat([message]).content
                print(f"Sleeping for {rate_limit}")
                time.sleep(rate_limit)
    except Exception as e:
        if cache:
            cache.write(case_id, prompt.name, str(e))  # FIXME
        return prompt.wrap_error(str(e))
    if cache:
        cache.write(case_id, prompt.name, response)
    return prompt.parse_response(response)


def make_headers(prompts):
    headers = []
    for prompt in prompts.next_prompt():
        headers.extend(prompt.headers)
    return headers


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
    api_cf = cf["PROVIDERS"]["SIH_OPENAI"]
    prompts = CaseChat()

    if not prompts.load_yaml(cf["PROMPTS"]):
        sys.exit()

    if args.prompt:
        if not prompts.prompt(args.prompt):
            print(f"No prompt defined with name '{args.prompt}'")
            sys.exit()
    chat = None
    if not args.test:
        chat = ChatOpenAI(
            model_name=api_cf["MODEL"],
            openai_api_key=api_cf["API_KEY"],
            openai_organization=api_cf["ORGANIZATION"],
            temperature=cf["TEMPERATURE"],
        )

    rate_limit = cf.get("RATE_LIMIT", 5)
    spreadsheet = cf["OUTPUT"]
    cache_dir = cf.get("CACHE", "")
    cache = None
    if cache_dir:
        cache = Cache(cache_dir)

    workbook = Workbook()
    worksheet = workbook.active

    if not args.prompt:
        headers = make_headers(prompts)
        worksheet.append(["file", "mnc"] + headers)

    if args.case:
        case = Path(cf["INPUT"]) / Path(args.case)
        if not case.is_file():
            print(f"Case file {args.case} not found")
            sys.exit()
        cases = [case]
    else:
        cases = Path(cf["INPUT"]).glob("*.json")

    for casefile in cases:
        case_id = casefile.stem
        prompts.judgment = load_case(casefile)
        print("Case: " + prompts.judgment["mnc"])
        row = [str(casefile), prompts.judgment["mnc"]]

        system_prompt = prompts.start_chat()

        if not args.test:
            chat([system_prompt])

        for prompt in prompts.next_prompt():
            if not args.prompt or prompt.name == args.prompt:
                print(f"Prompt: {prompt.name}")
                results = run_prompt(
                    chat,
                    prompts,
                    prompt,
                    test=args.test,
                    rate_limit=rate_limit,
                    cache=cache,
                    case_id=case_id,
                )
                if args.prompt:
                    print(results)
                else:
                    row += results
        if not args.prompt:
            worksheet.append(row)

    if not args.prompt:
        if args.test:
            print(f"Writing sample prompts to {spreadsheet}")
        else:
            print(f"Writing results to {spreadsheet}")
        workbook.save(spreadsheet)


if __name__ == "__main__":
    classify()
