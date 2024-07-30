import json
import time
import sys

from langchain.chat_models import ChatOpenAI
from langchainlaw.prompts import CaseChat
from langchainlaw.cache import Cache

RATE_LIMIT = 60


class Classifier:
    """Class which wraps up the case classifier. Config is a JSON object -
    see config.example.json"""

    def __init__(self, config, quiet=False):
        self.provider = config["provider"]
        self.spreadsheet = config["prompts"]
        try:
            self.api_cf = config["providers"][self.provider]
        except KeyError:
            print(f"Unknown provider: {self.provider}")
            sys.exit(-1)
        self.prompts = CaseChat()
        # # will throw a PromptException if misconfigured
        # self.prompts.load_yaml(config["prompts_spreadsheet"])
        self.test = False
        self.headers = None
        self.quiet = quiet
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

    def load_prompts(self, spreadsheet=None):
        """Load prompts from the spreadsheet file passed in, or the config"""
        if spreadsheet is None:
            spreadsheet = self.spreadsheet

        response = self.prompts.load(spreadsheet)
        self.headers = ["file", "mnc"]
        for prompt in self.prompts.next_prompt():
            self.headers.extend(prompt.headers)
        return response

    def message(self, str):
        """Print some progress info unless set to quiet mode"""
        if not self.quiet:
            print(str)

    def run_prompt(self, case_id, prompt):
        """Actually send prompt to LLM, unless there's already a response in the
        cache.

        response == what we get back from the LLM (text or json)
        results == a list of values to be written into the spreadsheet

        The cache is response, not results - if we read from the cache we re-parse
        the response if required (for json prompts)

        """
        message = self.prompts.make_message(prompt)
        try:
            if self.test:
                if self.cache:
                    response = self.cache.read(case_id, prompt.name)
                if response is not None:
                    self.message(f"[{case_id}] {prompt.name} - cached result")
                else:
                    self.message(f"[{case_id}] {prompt.name} - mock result")
                    response = prompt.mock_response()
            else:
                if self.cache:
                    response = self.cache.read(case_id, prompt.name)
                if response is not None:
                    self.message(f"[{case_id}] {prompt.name} - cached result")
                else:
                    self.message(f"[{case_id}] {prompt.name} - asking LLM")
                    response = self.chat([message]).content
                    self.message(f"[{case_id}] pausing for {self.rate_limit}")
                    time.sleep(self.rate_limit)
        except Exception as e:
            if self.cache:
                self.cache.write(case_id, prompt.name, str(e))  # FIXME
            return prompt.wrap_error(str(e))
        if self.cache and not self.test:
            self.cache.write(case_id, prompt.name, response)
        return prompt.parse_response(response)

    def collimate_one(self, name, results):
        """Collimate one set of results."""
        return self.prompts.prompt(name).collimate(results)

    def as_columns(self, results):
        """Take the dict of results returned by classify and aligns it
        with the column headers from the prompts"""
        cols = [results["file"], results["mnc"]]
        for name in self.prompts.prompt_names:
            cols.extend(self.collimate_one(name, results.get(name, None)))
        return cols

    def as_dict(self, results):
        """Takes the dict of results returned by classify and returns a
        flattened dict (no nesting, keys are the same as prompts.headers)"""
        d = {"file": results["file"], "mnc": results["mnc"]}
        for name in self.prompts.prompt_names:
            r = self.prompts.prompt(name).flatten(results[name])
            for k, v in r.items():
                d[k] = v
        return d

    def classify(self, casefile, test=False, one_prompt=None):
        """Run the classifier for a single case and returns the results as a
        dict by prompt label."""
        self.test = test
        case_id = casefile.stem
        with open(casefile, "r") as file:
            self.prompts.judgment = json.load(file)
        results = {"file": str(casefile), "mnc": self.prompts.judgment["mnc"]}

        system_prompt = self.prompts.start_chat()

        if not self.test:
            self.chat([system_prompt])

        for prompt in self.prompts.next_prompt():
            if not one_prompt or prompt.name == one_prompt:
                results[prompt.name] = self.run_prompt(case_id, prompt)
        return results
