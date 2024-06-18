import argparse
import json
import time
from pathlib import Path
from langchain.chat_models import ChatOpenAI
from openpyxl import Workbook
import sys

from langchainlaw.prompts import CaseChat
from langchainlaw.cache import Cache

RATE_LIMIT = 60


class Classifier:
    """Class which wraps up the case classifier. Config is a JSON object -
    see config.example.json"""

    def __init__(self, config):
        self.provider = config["provider"]
        try:
            self.api_cf = config["providers"][self.provider]
        except KeyError:
            print(f"Unknown provider: {self.provider}")
            sys.exit(-1)
        self.prompts = CaseChat()
        # will throw a PromptException if misconfigured
        self.prompts.load_yaml(config["prompts"])
        self.test = False
        self.headers = ["file", "mnc"]
        for prompt in self.prompts.next_prompt():
            self.headers.extend(prompt.headers)

        self.chat = ChatOpenAI(
            model_name=self.api_cf["model"],
            openai_api_key=self.api_cf["api_key"],
            openai_organization=self.api_cf["organization"],
            temperature=config["temperature"],
        )

        self.rate_limit = config.get("rate_limit", RATE_LIMIT)
        cache_dir = config.get("cache", None)
        self.cache = None
        if cache_dir:
            self.cache = Cache(cache_dir)

    def load_case(self, casefile):
        """Load JSON casefile"""
        with open(casefile, "r") as file:
            return json.load(file)

    def run_prompt(self, case_id, prompt):
        """Actually send prompt to LLM, unless there's already a response in the
        cache.

        response == what we get back from the LLM (text or json)
        results == a list of values to be written into the spreadsheet

        The cache is response, not results - if we read from the cache we re-parse
        the response if required (for json prompts)

        """
        message = self.prompts.message(prompt)
        try:
            if self.test:
                response = prompt.mock_response()
            else:
                if self.cache:
                    response = self.cache.read(case_id, prompt.name)
                if response is None:
                    response = self.chat([message]).content
                    time.sleep(self.rate_limit)
        except Exception as e:
            if self.cache:
                self.cache.write(case_id, prompt.name, str(e))  # FIXME
            return prompt.wrap_error(str(e))
        if self.cache:
            self.cache.write(case_id, prompt.name, response)
        return prompt.parse_response(response)

    def classify(self, casefile, test=False, one_prompt=None):
        """Run the classifier for a single case and returns the results as a
        dict by prompt label."""
        self.test = test
        case_id = casefile.stem
        self.prompts.judgment = self.load_case(casefile)
        results = {"file": str(casefile), "mnc": self.prompts.judgment["mnc"]}

        system_prompt = self.prompts.start_chat()

        if not self.test:
            self.chat([system_prompt])

        for prompt in self.prompts.next_prompt():
            if not one_prompt or prompt.name == one_prompt:
                results[prompt.name] = self.run_prompt(case_id, prompt)
        return results


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

    if not args.prompt:
        worksheet.append(["file", "mnc"] + classifier.headers)

    if args.case:
        case = Path(config["input"]) / Path(args.case)
        if not case.is_file():
            print(f"Case file {args.case} not found")
            return
        cases = [case]
    else:
        cases = Path(config["input"]).glob("*.json")

    if args.prompt:
        columns = ["file", "mnc", args.prompt]
    else:
        columns = classifier.headers

    for casefile in cases:
        results = classifier.classify(casefile, test=args.test, one_prompt=args.prompt)
        print(results)
        col_results = [results.get(c, "") for c in columns]
        print(columns)
        print(col_results)
        # FIXME - the results for multivalue fields are like parties:illegal
        worksheet.append([results.get(c, "") for c in columns])

    spreadsheet = config["output"]
    if args.test:
        print(f"Writing sample prompts to {spreadsheet}")
    else:
        print(f"Writing results to {spreadsheet}")
    workbook.save(spreadsheet)


if __name__ == "__main__":
    cli()
