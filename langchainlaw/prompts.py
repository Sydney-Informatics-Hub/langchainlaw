from dataclasses import dataclass
import yaml


@dataclass
class CasePrompt:
    name: str
    prompt: str
    preamble: str = ""
    structure: str = ""
    followup: str = ""

    def make_prompt(self, metadata, judgment):
        prompt = self.preamble.format(metadata=metadata, judgment=judgment)
        prompt = prompt + self.prompt
        if self.structure:
            prompt = prompt + self.structure
        return prompt


def load_prompts(prompt_yaml):
    prompts = []
    print(f"loading prompts {prompt_yaml}")
    with open(prompt_yaml, "r") as fh:
        prompt_cf = yaml.load(fh, Loader=yaml.Loader)
        print(f"prompts: {prompt_cf}")
        preamble = prompt_cf["preamble"]
        for p in prompt_cf["prompts"]:
            prompt = CasePrompt(
                name=p["name"],
                prompt=p["prompt"],
                preamble=preamble,
            )
            prompts.append(prompt)
    return prompts
