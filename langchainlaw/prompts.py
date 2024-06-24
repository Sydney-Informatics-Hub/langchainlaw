from dataclasses import dataclass, field
import yaml
import json
import re

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


@dataclass
class CasePrompt:
    name: str
    prompt: str
    return_type: str
    fields: list[str] = field(default_factory=list)

    @property
    def headers(self):
        if self.fields is None:
            return [self.name]
        else:
            return [f"{self.name}:{f}" for f in self.fields]

    def parse_response(self, response):
        if self.return_type == "text":
            return {self.name: response}
        try:
            results = parse_llm_json(response)
            if self.return_type == "json_literal":
                return json.dumps(results)
            if self.return_type == "json_multiple":
                return self.multi_json_to_fields(results)
            return self.json_to_fields(results)
        except Exception as e:
            return ["error" + str(e)]

    def json_to_fields(self, o):
        return {f"{self.name}:{f}": o.get(f, "") for f in self.fields}

    def multi_json_to_fields(self, results):
        """returns a dict with keys like 'parties0:name' for multivalue fields"""
        return {
            f"{self.name}{i}:{f}": results[i].get(f, "")
            for i in range(len(results))
            for f in self.fields
        }

    def wrap_error(self, msg):
        if self.return_type == "text":
            return [msg]
        else:
            cols = ["" for f in self.fields]
            cols[0] = msg
            return cols

    def mock_response(self):
        # Note: a future version could merge this with the JSON for the prompt
        if self.return_type == "text":
            return "Response"
        o = {f: "value" for f in self.fields}
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

    def load_yaml(self, yaml_file):
        with open(yaml_file, "r") as fh:
            prompt_cf = yaml.load(fh, Loader=yaml.Loader)
            self._system = prompt_cf["system"]
            self._intro_template = prompt_cf["intro"]
            for p in prompt_cf["prompts"]:
                self.add_prompt(
                    p["name"],
                    p["prompt"],
                    p.get("return_type", "text"),
                    p.get("fields", None),
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

    def add_prompt(self, name, prompt, return_type, fields):
        if name in self._prompts:
            raise ValueError(f"Prompt with name {name} already defined")
        self._prompt_names.append(name)
        self._prompts[name] = CasePrompt(
            name=name,
            prompt=prompt,
            return_type=return_type,
            fields=fields,
        )

    def start_chat(self):
        return SystemMessage(content=self.system)

    def next_prompt(self):
        for prompt_name in self._prompt_names:
            yield self._prompts[prompt_name]

    def message(self, prompt):
        content = self._intro + prompt.prompt
        return HumanMessage(content=content)
