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


def cache_write(cache, case_id, filename, results):
    cache_dir = Path(cache) / Path(case_id)
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_file = cache_dir / Path(filename)
    with open(cache_file, "w") as fh:
        for result in results:
            fh.write(result + "\n")


def cache_read(cache, case_id, filename):
    cache_file = Path(cache) / Path(case_id) / Path(filename)
    if cache_file.is_file():
        with open(cache_file, "r") as fh:
            results = fh.read()
            return results


def run_prompt(chat, prompts, prompt, test=False, cache=None, case_id=None):
    """Actually send prompt to LLM, unless there's a result in the cache"""
    if cache:
        result = cache_read(cache, case_id, prompt.name)
        if result:
            return result
    message = prompts.message(prompt)
    try:
        if test:
            response = prompt.mock_response()
        else:
            response = chat([message]).content
        results = prompt.parse_response(response)
    except Exception as e:
        results = prompt.wrap_error(str(e))
    if cache:
        cache_write(cache, case_id, prompt.name, results)
    return results


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
        chat = ChatOpenAI(
            model_name=cf["OPENAI_CHAT_MODEL"],
            openai_api_key=cf["OPENAI_API_KEY"],
            openai_organization=cf["OPENAI_ORGANIZATION"],
            temperature=cf["TEMPERATURE"],
        )

    rate_limit = cf.get(cf["RATE_LIMIT"], 5)
    spreadsheet = cf["OUTPUT"]
    cache = cf["CACHE"]

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
                    cache=cache,
                    case_id=case_id,
                )
                if args.prompt:
                    print(results)
                else:
                    row += results
                if not args.test:
                    time.sleep(rate_limit)
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
