import json
import time
import sys
import pandas as pd

from langchain.chat_models import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage

from langchainlaw.prompts import CasePrompt, CasePromptField, PromptException
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
        self.prompts = {}
        self.prompt_names = []
        self.system = None
        self._judgment = None
        self._prompt_judgment = None
        self.judgment_template = None
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

    def message(self, str):
        """Print some progress info unless set to quiet mode"""
        if not self.quiet:
            print(str)

    @property
    def judgment(self):
        return self._judgment

    @judgment.setter
    def judgment(self, v):
        self._judgment = v
        self._prompt_judgment = self.judgment_template.format(judgment=json.dumps(v))

    def prompt(self, name):
        """Returns a named prompt object"""
        return self.prompts[name]

    def start_chat(self):
        return SystemMessage(content=self.system)

    def next_prompt(self):
        for prompt_name in self.prompt_names:
            yield self.prompts[prompt_name]

    def make_message(self, prompt):
        """Builds the complete prompt from the JSON-encoded judgment and
        the prompt questions (which also will include examples for the LLM to
        return)"""
        if self._prompt_judgment is not None:
            content = self._prompt_judgment + prompt.prompt
            return HumanMessage(content=content)
        else:
            raise PromptException(
                "Need to set the judgment with judgment() before"
                " calling make_message()"
            )

    def run_prompt(self, case_id, prompt, no_cache=False):
        """Actually send prompt to LLM, unless there's already a response in the
        cache or no_cache is True

        response == what we get back from the LLM (text or json)
        results == a list of values to be written into the spreadsheet

        The cache is response, not results - if we read from the cache we re-parse
        the response if required (for json prompts)

        """
        message = self.make_message(prompt)
        response = None
        try:
            if self.test:
                if self.cache and not no_cache:
                    response = self.cache.read(case_id, prompt.name)
                if response is not None:
                    self.message(f"[{case_id}] {prompt.name} - cached result")
                else:
                    self.message(f"[{case_id}] {prompt.name} - mock result")
                    response = prompt.mock_response()
            else:
                if self.cache and not no_cache:
                    response = self.cache.read(case_id, prompt.name)
                if response is not None:
                    self.message(f"[{case_id}] {prompt.name} - cached result")
                else:
                    self.message(f"[{case_id}] {prompt.name} - asking LLM")
                    response = self.chat([message]).content
                    self.message(f"[{case_id}] pausing for {self.rate_limit}")
                    time.sleep(self.rate_limit)
        except Exception as e:
            return prompt.wrap_error(str(e))
        if self.cache and not self.test:
            self.cache.write(case_id, prompt.name, response)
        return prompt.parse_response(response)

    def classify(self, casefile, test=False, prompts=None, no_cache=False):
        """Run the classifier for a single case and returns the results as a
        dict by prompt label."""
        self.test = test
        case_id = casefile.stem
        self.load_judgment(casefile)
        results = {"file": str(casefile), "mnc": self.judgment["mnc"]}
        system_prompt = self.start_chat()

        if not self.test:
            self.chat([system_prompt])

        for prompt in self.next_prompt():
            if not prompts or prompt.name in prompts:
                results[prompt.name] = self.run_prompt(
                    case_id, prompt, no_cache=no_cache
                )
        return results

    def load_judgment(self, casefile):
        """Loads a Path as a JSON casefile"""
        with open(casefile, "r") as fh:
            self.judgment = json.load(fh)

    def show_prompt(self, prompt_name):
        """This returns the named prompt without the judgement"""
        return self.prompts[prompt_name].prompt

    def load_prompts(self, spreadsheet):
        """Load the prompts, system prompt and intro template from spreadsheet"""

        if spreadsheet is None:
            spreadsheet = self.spreadsheet

        system = pd.read_excel(spreadsheet, sheet_name="system")
        # extract the first row from column System
        self.system = system["System"][0]

        intro = pd.read_excel(spreadsheet, sheet_name="intro")
        self.judgment_template = intro["Intro"][0]
        self.load_prompt_sheet(spreadsheet)

        self.headers = ["file", "mnc"]
        for name in self.prompt_names:
            self.headers.extend(self.prompts[name].headers)

    def load_prompt_sheet(self, spreadsheet):
        """Loads the worksheet with prompt definitions from the spreadsheet"""
        prompts = pd.read_excel(spreadsheet, sheet_name="prompts", dtype=str).fillna("")

        first_row = None
        fields = []
        for _, row in prompts.iterrows():
            if row["return_type"]:
                if first_row is not None:
                    self.add_prompt(first_row, fields)
                first_row = row[:]
                fields = []
            fields.append(
                CasePromptField(
                    field=row["fields"],
                    question=row["question_description"],
                    example_response=row["example"],
                )
            )

        if first_row is not None:
            self.add_prompt(first_row, fields)

    def add_prompt(self, row, fields):
        """Converts a spreadsheet row into a CasePrompt and add it to the
        prompts dict"""
        repeats = 1
        if row["return_type"] == "json_multiple":
            if row["repeats"]:
                try:
                    repeats = int(row["repeats"])
                except ValueError:
                    raise PromptException("'repeats' must be an integer")
        name = row["Prompt_name"]
        if name in self.prompt_names:
            raise ValueError(f"Prompt with name {name} defined twice")
        self.prompt_names.append(name)
        self.prompts[name] = CasePrompt(
            name=row["Prompt_name"],
            question=row["prompt_question"],
            return_instruction=row["return_instruction"],
            return_type=row["return_type"],
            additional_instruction=row["additional_instruction"],
            fields=fields,
            repeats=repeats,
        )

    def collimate_one(self, name, results):
        """Collimate one set of results."""
        return self.prompts[name].collimate(results)

    def as_columns(self, results):
        """Take the dict of results returned by classify and aligns it
        with the column headers from the prompts"""
        cols = [results["file"], results["mnc"]]
        for name in self.prompt_names:
            cols.extend(self.collimate_one(name, results.get(name, None)))
        return cols

    def as_dict(self, results):
        """Takes the dict of results returned by classify and returns a
        flattened dict (no nesting, keys are the same as prompts.headers)"""
        d = {"file": results["file"], "mnc": results["mnc"]}
        for name in self.prompt_names:
            r = self.prompts[name].flatten(results[name])
            for k, v in r.items():
                d[k] = v
        return d
