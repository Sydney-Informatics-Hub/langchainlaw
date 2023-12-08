from dataclasses import dataclass
import yaml
import json

from langchain.schema import HumanMessage, SystemMessage


@dataclass
class CasePrompt:
    name: str
    prompt: str
    return_type: str
    fields: list[str]

    def message(self, judgment):
        content = self.prompt.format(judgment=json.dumps(judgment))
        return HumanMessage(content=content)


class CaseChat:
    def __init__(self, yaml=None):
        self._system = None
        self._judgment = None
        self._prompts = {}
        self._prompt_names = []
        if yaml is not None:
            self.load_yaml(yaml)

    @property
    def system(self):
        return self._system

    @property
    def prompt_names(self):
        return self._prompt_names

    def prompt(self, name):
        return self._prompts.get(name, None)

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

    def load_yaml(self, yaml_file):
        with open(yaml_file, "r") as fh:
            prompt_cf = yaml.load(fh, Loader=yaml.Loader)
            self._system = prompt_cf["system"]
            for p in prompt_cf["prompts"]:
                self.add_prompt(
                    p["name"],
                    p["prompt"],
                    p.get("return_type", "text"),
                    p.get("fields", None),
                )

    def start_chat(self):
        return SystemMessage(content=self.system)

    def start_judgment(self, judgment):
        return HumanMessage(content=self.judgment.format(judgment=judgment))

    def next_prompt(self, judgment):
        for prompt_name in self._prompt_names:
            yield self._prompts[prompt_name]

    def multiple_prompt(self, response):
        try:
            responses = json.loads(response)
        except json.decoder.JSONDecodeError:
            return ""
        for x in responses:
            yield self.multiple.format(x=x)
