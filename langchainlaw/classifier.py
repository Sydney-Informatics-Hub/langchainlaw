import json
import time
import sys
import pandas as pd

from typing import Generator
from pathlib import Path

from langchain.chat_models import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage

from langchainlaw.prompts import CasePrompt, CasePromptField, PromptException
from langchainlaw.cache import Cache

from langchainlaw.prompts import ResultsDict, FlatResultsDict

import openai
from datetime import datetime

RATE_LIMIT = 60


class Classifier:
    """Class which wraps up the case classifier. Config is a JSON object -
    see config.example.json"""

    def __init__(self, config: dict[str, str | dict], quiet: bool = False):
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
        self.api_key = self.api_cf["api_key"]
        self.model = self.api_cf["model"]
        self.temperature = config["temperature"]
        self.df_batch_records = pd.read_excel(config["batch_records"], dtype=str).fillna("")
        self.batch_records_name = config["batch_records"]
        self.rate_limit = config.get("rate_limit", RATE_LIMIT)
        cache_dir = config.get("cache", None)
        self.cache = None
        if cache_dir:
            self.cache = Cache(cache_dir)

    def log(self, msg: str):
        """Print some progress info unless set to quiet mode"""
        if not self.quiet:
            print(msg)

    @property
    def judgment(self) -> str:
        return self._judgment

    @judgment.setter
    def judgment(self, v: str):
        self._judgment = v
        self._prompt_judgment = self.judgment_template.format(judgment=json.dumps(v))

    def prompt(self, name: str) -> CasePrompt:
        """Returns a named prompt object"""
        return self.prompts[name]

    def start_chat(self) -> SystemMessage:
        return SystemMessage(content=self.system)

    def next_prompt(self) -> Generator[CasePrompt, None, None]:
        for prompt_name in self.prompt_names:
            yield self.prompts[prompt_name]

    def make_message(self, prompt: CasePrompt) -> HumanMessage:
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

    def run_prompt(
        self, case_id: str, prompt: CasePrompt, no_cache: bool = False
    ) -> ResultsDict:
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
                    self.log(f"[{case_id}] {prompt.name} - cached result")
                else:
                    self.log(f"[{case_id}] {prompt.name} - mock result")
                    response = prompt.mock_response()
            else:
                if self.cache and not no_cache:
                    response = self.cache.read(case_id, prompt.name)
                if response is not None:
                    self.log(f"[{case_id}] {prompt.name} - cached result")
                else:
                    self.log(f"[{case_id}] {prompt.name} - asking LLM")
                    response = self.chat([message]).content
                    self.log(f"[{case_id}] pausing for {self.rate_limit}")
                    time.sleep(self.rate_limit)
        except Exception as e:
            return prompt.wrap_error(str(e))
        if self.cache and not self.test:
            self.cache.write(case_id, prompt.name, response)
        return prompt.parse_response(response)

    def classify(
        self,
        casefile: Path,
        test: bool = False,
        prompts: list[str] = None,
        no_cache: bool = False,
    ) -> ResultsDict:
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

    def load_judgment(self, casefile: Path):
        """Loads a Path as a JSON casefile"""
        with open(casefile, "r") as fh:
            self.judgment = json.load(fh)

    def show_prompt(self, prompt_name: str):
        """This returns the named prompt without the judgement"""
        return self.prompts[prompt_name].prompt

    def load_prompts(self, spreadsheet: str):
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

    def load_prompt_sheet(self, spreadsheet: str):
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

    def add_prompt(self, row, fields: list[CasePromptField]):
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

    def collimate_one(self, name: str, results: ResultsDict):
        """Collimate one set of results."""
        return self.prompts[name].collimate(results)

    def as_columns(self, results: ResultsDict):
        """Take the dict of results returned by classify and aligns it
        with the column headers from the prompts"""
        cols = [results["file"], results["mnc"]]
        for name in self.prompt_names:
            cols.extend(self.collimate_one(name, results.get(name, None)))
        return cols

    def as_dict(self, results: ResultsDict) -> FlatResultsDict:
        """Takes the dict of results returned by classify and returns a
        flattened dict (no nesting, keys are the same as prompts.headers)"""
        d = {"file": results["file"], "mnc": results["mnc"]}
        for name in self.prompt_names:
            r = self.prompts[name].flatten(results[name])
            for k, v in r.items():
                d[k] = v
        return d

    def custom_id(
        self, 
        case_id: str, 
        prompt: CasePrompt, 
    ) -> str:
        """Generate a custom id for a case and a prompt (capturing a group for questions) for a line in a JSONL for a batch request.
        custom_id is used to map a line in an output JSONL to a case and a prompt. It is needed because the output line order may not match the input line order. 
        custom_id == case_id:prompt.name.
        """
        custom_id=f"{case_id}:{prompt.name}"
        return custom_id
        
    def batch_input_line(
        self, 
        case_id: str, 
        prompt: CasePrompt, 
        no_cache: bool = False
    ) -> dict:
        """Create one line of a JSONL which will be submitted to LLM as a batch, unless there's already a response in the
        cache or no_cache is True

        Each batch request is confined to one single case. Each line of the JSONL for this batch input captures one prompt for that case.

        batch_input_dict == one line of the JSONL to be submitted to the LLM (json)

        response == what we get or got back from the LLM (text or json)

        The cache is response, not results - if we read from the cache we re-parse
        the response if required (for json prompts)

        """
        response = None
        system_prompt = [{"role": "system", "content": self.start_chat().content}]
        user_prompt = [{"role": "user", "content": self.make_message(prompt).content}]
        messages = system_prompt + user_prompt
        response_format = {"type": "json_object"}
        
        body = {"model": self.model, 
            "messages": system_prompt + user_prompt,  
            "response_format": response_format, 
            "temperature": self.temperature, 
        }

        batch_input_dict = {}
        
        try:
            #Uncomment below if want to enable testing
            #if self.test:
                #if self.cache and not no_cache:
                    #response = self.cache.read(case_id, prompt.name)
                #if response is not None:
                    #self.log(f"[{case_id}] {prompt.name} - cached result")
                #else:
                    #self.log(f"[{case_id}] {prompt.name} - mock result")
                    #response = prompt.mock_response()
            #else:
            if self.cache and not no_cache:
                response = self.cache.read(case_id, prompt.name)
            if response is not None:
                self.log(f"[{case_id}] {prompt.name} - cached result")
            else:
                self.log(f"[{case_id}] {prompt.name} - producing batch input for LLM")
                batch_input_dict = {"custom_id": self.custom_id(case_id, prompt), 
                                    "method": "POST", 
                                    "url": "/v1/chat/completions", 
                                    "body": body
                }
                    
        except Exception as e:
            return prompt.wrap_error(str(e))
        return batch_input_dict

    def batch_send(
        self,
        casefile: Path,
        #test: bool = False, #Uncomment if want to enable testing
        prompts: list[str] = None,
        no_cache: bool = False,
    )-> dict:
        """Submit a batch request for a single case, keep the batch object/record in the batch records spreadsheet, and return the object/record as a dict."""
        case_id = casefile.stem
        self.load_judgment(casefile)
        batch_record_dict = {}

        #Uncomment below if want to enable testing
        #self.test = test
        #if not self.test:
        
        self.log(f"[{case_id}] - submitting batch input for all prompts for LLM")
        
        #Initialise openai
        openai.api_key = self.api_key
        
        #Create a list of prompts
        batch_input_list = []
        for prompt in self.next_prompt():
            if not prompts or prompt.name in prompts:
                batch_input_line = self.batch_input_line(case_id, prompt, no_cache=no_cache)
                batch_input_list.append(batch_input_line)
                
        #Convert the list of prompts to JSONL
        df_jsonl = pd.DataFrame(batch_input_list)
        jsonl_for_batching = df_jsonl.to_json(orient='records', lines=True)

        #Submit batch request to LLM
        batch_input_file = openai.files.create(
            file = jsonl_for_batching.encode(encoding="utf-8"),
            purpose="batch"
        )
        batch_input_file_id = batch_input_file.id
        batch_record = openai.batches.create(
            input_file_id=batch_input_file_id,
            endpoint="/v1/chat/completions",
            completion_window="24h", 

        )

        #Keep batch record
        self.log(f"[{case_id}] - saving batch record to {self.batch_records_name}")
        batch_record_dict = {"submission_time": datetime.now(), 
           'status': batch_record.status, 
           'batch_id': batch_record.id, 
           'input_file_id': batch_record.input_file_id, 
           'output_file_id': batch_record.output_file_id, 
           'case_id': case_id,
        }

        batch_record_df = pd.DataFrame([batch_record_dict])
        batch_records = pd.read_excel(self.batch_records_name, dtype=str).fillna("")
        batch_records_updated = pd.concat([batch_records, batch_record_df], ignore_index=True)
        batch_records_updated.to_excel(self.batch_records_name, index=False)

        self.log(f"[{case_id}] pausing for {self.rate_limit}")
        time.sleep(self.rate_limit)

        return batch_record_dict

    def batch_check(
        self,
        casefile: Path,
        status_report: bool = True, 
        #test: bool = False, #Uncomment if want to enable testing
        no_cache: bool = False,
    )-> dict:
        """Check the status of a batch request, update the batch records spreadsheet, return the status and output_id for that request as a dict.
        Where a case and a prompt have produced multiple batch requests, the status and output_id of the most recent request will be produced.
        """
        case_id = casefile.stem
        self.load_judgment(casefile)

        #Uncomment below if want to enable testing
        #self.test = test 
        #if not self.test: 
        
        #Initialise openai
        openai.api_key = self.api_key

        #Retrive records of batch requests
        batch_records = pd.read_excel(self.batch_records_name, dtype=str).fillna("")
        
        #Sort records by submission time
        if 'submission_time' in batch_records.columns:
            batch_records = batch_records.sort_values(by='submission_time')

        #Obtain the most recent record for the relevant case
        case_index = batch_records.index[batch_records['case_id']==case_id].tolist()[-1]

        #Get and keep batch record
        batch_id = batch_records.loc[case_index, 'batch_id']
        submission_time = batch_records.loc[case_index, 'submission_time']

        #Get and updated batch record
        batch_record = openai.batches.retrieve(batch_id)
        status = batch_record.status
        output_file_id = batch_record.output_file_id
        
        batch_records.loc[case_index, 'status']=status
        batch_records.loc[case_index, 'output_file_id']=output_file_id

        #Print status if want to
        if status_report == True:
            self.log(f"[{case_id}] - submitted at {submission_time}, current status == {status}, output_file_id == {output_file_id}")

        #Uodate batch records
        batch_records.to_excel(self.batch_records_name, index=False)
        
        return {'status': status, 'output_file_id': output_file_id}

    def batch_retrieve_online(
        self, 
        casefile: Path,
        prompt: CasePrompt, 
        status_report: bool = False,
    ) -> ResultsDict:
        """Retrive one line of completed results of a batch request to LLM

        Where a case and a prompt have produced multiple submitted batches, the most recent, completed results will be retrived.

        response == what we get back from the LLM (text or json)
        results == a list of values to be written into the spreadsheet

        The cache is response, not results - if we read from the cache we re-parse
        the response if required (for json prompts)

        If a JSON array is returned, it is usually in the form of "{{prompt.name}:[the JSON array]}". 
        Hence, if the return type for the prompt is json_multiple, the following extracts the JSON array from the dict.

        """
        case_id = casefile.stem
        response = None
        try:
            status_output_id = self.batch_check(casefile, status_report)
            if status_output_id['status'] == 'completed':
                self.log(f"[{case_id}] {prompt.name} - retrieving output from LLM")
                custom_id = self.custom_id(case_id, prompt)
                batch_response = openai.files.content(status_output_id['output_file_id'])
                
                df_batch_response = pd.read_json(batch_response.text, lines=True)
                response_index = df_batch_response.index[df_batch_response['custom_id']==custom_id].tolist()[0]
                response = df_batch_response.loc[response_index, 'response']['body']['choices'][0]['message']['content']

                #Check if a JSON array is sought and returned but in the dict form of {str:[dict, dict, ...]} rather than the list form [dict, dict ... ] sought 
                if prompt.return_type == "json_multiple":
                    response_list = []
                    response_json = json.loads(response)
                    for key in response_json.keys():
                        if type(response_json[key])==list:
                            response_list += response_json[key]
                        else:
                            response_list.append({key: response_json[key]})
                    response = json.dumps(response_list)
                
        except Exception as e:
            return prompt.wrap_error(str(e))
        if self.cache and not self.test:
            self.cache.write(casefile, prompt.name, response)
        return prompt.parse_response(response)
            
    def batch_get(
        self,
        casefile: Path,
        #test: bool = False, #Uncomment if want to enable testing
        prompts: list[str] = None,
        status_report: bool = False, 
        no_cache: bool = False,
    ) -> ResultsDict:
        """Retrieve the classifier for a single case and returns the results as a
        dict by prompt label."""
        case_id = casefile.stem
        self.load_judgment(casefile)
        results = {"file": str(casefile), "mnc": self.judgment["mnc"]}

        #Uncomment below if want to enable testing
        #self.test = test
        #if not self.test: 
        
        openai.api_key = self.api_key

        for prompt in self.next_prompt():
            if not prompts or prompt.name in prompts:                    
                results[prompt.name] = self.batch_retrieve_online(casefile, prompt, status_report)
                
        return results
