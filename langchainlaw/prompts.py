from dataclasses import dataclass, field
import yaml
import json
import random
import re

from langchainlaw.generate_prompts import assemble_complete_yaml
from langchain.schema import HumanMessage, SystemMessage

JSON_QUOTE_RE = re.compile("```json(.*)```")


def parse_llm_json(llm_json):
    """Deals with some of the models wrapping JSON in ```json ``` markup
    Raises a JSON decode error."""
    llm_oneline = llm_json.replace("\n", "")
    match = JSON_QUOTE_RE.search(llm_oneline)
    if match:
        json_raw = match.group(1)
        return json.loads(json_raw)
    else:
        return json.loads(llm_json)


class PromptException(Exception):
    pass


# TODO -
# put the structured data from the spreadsheet into this class
# for each field:
#    question_description
#    example
#    question_number (this can be inferred)
# return_instruction
# additional_instructions


def random_para_ref():
    return [
        f"(p{random.randint(1, 100)})",
        f"(pp{random.randint(1, 5)}-{random.randint(6, 10)})",
    ][random.randint(0, 1)]


@dataclass
class CaseQuestion:
    field: str
    question: str
    example_response: str


@dataclass
class CasePrompt:
    name: str
    question: str
    return_instruction: str
    return_type: str
    fields: list[CaseQuestion] = field(default_factory=list)
    additional_instruction: str = None
    repeats: int = 1

    @property
    def headers(self):
        if self.fields is None:
            return [self.name]
        else:
            if self.return_type == "json_multiple":
                return [
                    f"{self.name}{n}:{f}"
                    for n in range(1, self.repeats + 1)
                    for f in self.fields
                ]
            else:
                return [f"{self.name}:{f}" for f in self.fields]

    @property
    def prompt(self):
        prompt = f"      {self.question}\n\n"
        i = 1
        for f in self.fields:
            prompt += f"      Q{i}: {f.question}\n"
            i += 1
        prompt += f"\n      {self.return_instruction}\n\n"

        # reconstruct a dictionary from the fields, keeping the key and "example" value

        response = {
            f.field: f.example_response + " " + random_para_ref() for f in self.fields
        }

        prompt += f"""        {{{str(json.dumps(response, indent=10))[:-2]}
        }}}}
"""
        if self.additional_instruction is not None:
            prompt += f"      {self.additional_instruction}\n\n"
        return prompt

    def collimate(self, result):
        """Take a results set for this prompt and return an array of the
        results as columns."""
        print(f"collimate {self.name} {self.return_type}")
        print(result)
        if self.fields is None:
            return [result]
        if self.return_type == "json_multiple":
            if result is None:
                return ["" for _ in self.fields]
            return [single.get(f.field) for single in result for f in self.fields]
        if result is None:
            return ["" for _ in self.fields]
        return [result.get(f.field) for f in self.fields]

    def flatten(self, result):
        """Take a results set for this prompt and return a dict by either
        name, name:field or name:n:field depending on whether the return type
        is str / single json / multiple json"""
        if self.fields is None:
            return {self.name: result}
        if self.return_type == "json_multiple":
            return {
                f"{self.name}:{n + 1}:{f}": result[n].get(f.field)
                for n in range(len(result))
                for f in self.fields
            }
        return {f"{self.name}:{f}": result.get(f.field) for f in self.fields}

    def parse_response(self, response):
        """Parses the string returned by the LLM, and also does some basic
        checking that the return types matched what the prompt expected"""
        if self.return_type == "text":
            return response
        try:
            results = parse_llm_json(response)
            if self.return_type == "json_literal":
                return json.dumps(results)
            if self.return_type == "json":
                if type(results) is not dict:
                    print(
                        f"[warning] prompt {self.name}" " didn't return a JSON object"
                    )
                    print("returned type: " + str(type(results)))
            if self.return_type == "json_multiple":
                if type(results) is not list:
                    print(f"[warning] prompt {self.name}" " didn't return a JSON array")
                    print("returned type: " + str(type(results)))
            return results
        except Exception as e:
            message = f"error parsing {self.name}: '{response}'' " + str(e)
            print(message)
            return message

    def json_to_fields(self, o):
        return {f"{self.name}:{f.field}": o.get(f.field, "") for f in self.fields}

    def multi_json_to_fields(self, results):
        """returns a dict with keys like 'parties0:name' for multivalue fields"""
        return {
            f"{self.name}{i}:{f.field}": results[i].get(f.field, "")
            for i in range(len(results))
            for f in self.fields
        }

    def wrap_error(self, msg):
        if self.return_type == "text":
            return [msg]
        else:
            cols = ["" for _ in self.fields]
            cols[0] = msg
            return cols

    def mock_response(self):
        """returns string literals for JSON fields so that they can be parsed"""
        if self.fields is None:
            return "plaintext value"
        o = {f.field: f.example_response for f in self.fields}
        if self.return_type == "json_literal":
            return json.dumps(o)
        if self.return_type == "json_multiple":
            return json.dumps([o])
        return json.dumps(o)

    def validate(self):
        """Raise a PromptException if the config is invalid"""
        if self.return_type == "json_multiple" and not self.fields:
            raise PromptException("json_multiple needs a fields section")


class CaseChat:
    def __init__(self):
        self._system = None
        self._judgment = None
        self._intro = None
        self._intro_template = None
        self._prompts = {}
        self._prompt_names = []

    @property
    def system(self):
        return self._system

    @property
    def prompt_names(self):
        return self._prompt_names

    @property
    def judgment(self):
        return self._judgment

    @judgment.setter
    def judgment(self, v):
        self._judgment = v
        self._intro = self._intro_template.format(judgment=json.dumps(v))

    @property
    def intro(self):
        return self._intro

    def prompt(self, name):
        return self._prompts.get(name, None)

    def assemble_yaml_from_spreadsheet(self, input_file):
        output_file = input_file.split(".")[0] + ".yaml"
        assemble_complete_yaml(input_file, output_file)
        return output_file

    def load_yaml(self, input_file):
        output_file = self.assemble_yaml_from_spreadsheet(input_file)
        with open(output_file, "r") as fh:
            prompt_cf = yaml.load(fh, Loader=yaml.Loader)
            self._system = prompt_cf["system"]
            self._intro_template = prompt_cf["intro"]
            for p in prompt_cf["prompts"]:
                self.add_prompt(
                    p["name"],
                    p["prompt"],
                    p.get("return_type", "text"),
                    p.get("fields", None),
                    p.get("repeats", 1),
                )
            valid = True
            for prompt in self.next_prompt():
                try:
                    prompt.validate()
                except PromptException as e:
                    print(f"Prompt '{prompt.name}' config error: {e}")
                    valid = False
        return valid

    def debug(self):
        print("Debugging prompts")
        for name in self.prompt_names:
            prompt = self.prompt(name)
            print(f"\nprompt {name}")
            print(prompt.prompt)
            print(prompt.return_type)
            print(prompt.fields)

    def add_prompt(self, name, prompt, return_type, fields, repeats):
        if name in self._prompts:
            raise ValueError(f"Prompt with name {name} already defined")
        self._prompt_names.append(name)
        self._prompts[name] = CasePrompt(
            name=name,
            prompt=prompt,
            return_type=return_type,
            fields=fields,
            repeats=repeats,
        )

    def add_caseprompt(self, prompt):
        """New version where you pass in a CasePrompt"""
        if prompt.name in self._prompts:
            raise ValueError(f"Prompt with name {prompt.name} already exists")
        self._prompt_names.append(prompt.name)
        self._prompts[prompt.name] = prompt

    def start_chat(self):
        return SystemMessage(content=self.system)

    def next_prompt(self):
        for prompt_name in self._prompt_names:
            yield self._prompts[prompt_name]

    def message(self, prompt):
        content = self._intro + prompt.prompt
        return HumanMessage(content=content)
