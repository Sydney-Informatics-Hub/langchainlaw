import argparse
import json 
import re
from pathlib import Path
from langchain.llms import OpenAI

# langchain law


# This function creates the prompt to identify the different parties mentioned in the case, and answer some relevant questions
# It uses information from both the metadata of the case, and also the first 15 paragraphs of the judgement itself

def identify_parties_prompt(case_json):
    parties = case_json["parties"]
    judgment = case_json["judgment"]
    return f"""From the following metadata: {parties}, and judgement text of an contested inheritance case:
    {judgment[:15]};
    1. Identify who is the claimant(s) and defendant(s). Also make a note on if they are a natural person.
    Then, for each natural person indentified from above,
    2. State their relationship with the deceased.
    3. Explain whether they were dependant on deceased.
    4. State the relevanet paragraph number.
    """


# This function reads the decision metadata and finds the paragraphs that make a decision, 
# or returns Application dismissed. if no paragraph is found

def find_decision_paragraph(case_json):
    numbers = re.findall(r'\d+', case_json["decision"])
    if len(numbers) == 0:
        return case_json["decision"]
    decisions = ""
    for para in case_json["judgment"]:
        for num in numbers:
            if para.startswith(num):
                decisions += (para + "\n")
        return decisions


# This function creates the prompt to identify if the claim failed or succeeded
# based on what is found from the decision metadata
# if the application was dismissed, the outcome is a fail

def success_or_fail_prompt(case_json):
    return f"""Based on the following court judgement text, did the outcome of claims succeed or fail:
    '{find_decision_paragraph(case_json)}'"""


def load_config(cf_file):
    with open(cf_file, "r") as fh:
        cf = json.load(fh)
        return cf


def process_judgement(llm, judgment):
    """Run all prompts on a judgment"""
    prompt_fns = { "parties": identify_parties_prompt, "success": success_or_fail_prompt }

    results = {}

    for label, prompt_fn in prompt_fns.items():
        print(f"Prompt: {label}")
        prompt = prompt_fn(judgment)
        results[label] = llm(prompt)

    return results

def classify():
    cf = load_config("./config.json")
    ap = argparse.ArgumentParser("langchain-law")
    ap.add_argument(
        "--dir", default="./", type=Path, help="Base directory to scan for files"
    )
    args = ap.parse_args()
    llm = OpenAI(
        openai_api_key=cf["OPENAI_API_KEY"],
        openai_organization=cf["OPENAI_ORGANIZATION"],
        temperature=cf["TEMPERATURE"]
        )

    for jsonfile in Path(cf["JUDGMENTS"]).glob("*.json"):
        with open(jsonfile, "r") as file:
            data = json.load(file)
            print(f"Case: " + data["mnc"])
            results = process_judgement(llm, data)
            print(results)




if __name__ == "__main__":
    classify()
