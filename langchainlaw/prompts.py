from dataclasses import dataclass, field
import json
import random
import re

JSON_QUOTE_RE = re.compile("```json(.*)```")


def parse_llm_json(llm_json: str):
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


def random_para_ref():
    return [
        f"(p{random.randint(1, 100)})",
        f"(pp{random.randint(1, 5)}-{random.randint(6, 10)})",
    ][random.randint(0, 1)]


@dataclass
class CasePromptField:
    field: str
    question: str
    example_response: str


@dataclass
class CasePrompt:
    name: str
    question: str
    return_instruction: str
    return_type: str
    fields: list[CasePromptField] = field(default_factory=list)
    additional_instruction: str = None
    repeats: int = 1

    @property
    def headers(self):
        if self.fields is None:
            return [self.name]
        else:
            if self.return_type == "json_multiple":
                return [
                    f"{self.name}{n}:{f.field}"
                    for n in range(1, self.repeats + 1)
                    for f in self.fields
                ]
            else:
                return [f"{self.name}:{f.field}" for f in self.fields]

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
                f"{self.name}:{n + 1}:{f.field}": result[n].get(f.field)
                for n in range(len(result))
                for f in self.fields
            }
        return {f"{self.name}:{f.field}": result.get(f.field) for f in self.fields}

    def parse_response(self, response: str):
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

    def json_to_fields(self, o: dict[str, str]):
        return {f"{self.name}:{f.field}": o.get(f.field, "") for f in self.fields}

    def multi_json_to_fields(self, results: dict[str, str]):
        """returns a dict with keys like 'parties0:name' for multivalue fields"""
        return {
            f"{self.name}{i}:{f.field}": results[i].get(f.field, "")
            for i in range(len(results))
            for f in self.fields
        }

    def wrap_error(self, msg: str):
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
