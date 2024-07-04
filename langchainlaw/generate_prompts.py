import argparse
import json
import pandas as pd
from collections import defaultdict
import random


def parse_arguments():
    parser = argparse.ArgumentParser(description="Convert XLSX prompts to YAML")
    parser.add_argument("input_file", help="Path to the input XLSX file")
    parser.add_argument("output_file", help="Path to the output YAML file")
    return parser.parse_args()


# write function to process sheet called system in the xlsx file
def process_system_intro(input_file):
    system = pd.read_excel(input_file, sheet_name="system")

    # extract the first row from column System
    system_string = system["System"][0]

    intro = pd.read_excel(input_file, sheet_name="intro")
    intro_string = intro["Intro"][0]

    return f"""system: |
  {system_string}

intro: {intro_string}
"""


def process_prompts(input_file):
    prompts = pd.read_excel(input_file, sheet_name="sample_prompts", dtype=str)
    # fill na with empty string
    prompts = prompts.fillna("")
    prompt_responses = defaultdict(
        lambda: {
            "fields": defaultdict(dict),
            "return_type": "",
            "repeats": "",
            "prompt_question": "",
            "return_instruction": "",
            "additional_instruction": "",
        }
    )
    # for each row in the prompts sheet, extract the prompt and the response

    for i, row in prompts.iterrows():
        if row["return_type"]:
            prompt_responses[row["Prompt_name"]]["return_type"] = row["return_type"]
        if row["repeats"]:
            prompt_responses[row["Prompt_name"]]["repeats"] = row["repeats"]
        if row["prompt_question"]:
            prompt_responses[row["Prompt_name"]]["prompt_question"] = row[
                "prompt_question"
            ]
        if row["return_instruction"]:
            prompt_responses[row["Prompt_name"]]["return_instruction"] = row[
                "return_instruction"
            ]
        if row["additional_instruction"]:
            prompt_responses[row["Prompt_name"]]["additional_instruction"] = row[
                "additional_instruction"
            ]

        prompt_responses[row["Prompt_name"]]["fields"][row["fields"]][
            "question_description"
        ] = row["question_description"]
        prompt_responses[row["Prompt_name"]]["fields"][row["fields"]]["example"] = row[
            "example"
        ]
        prompt_responses[row["Prompt_name"]]["fields"][row["fields"]][
            "question_number"
        ] = len(prompt_responses[row["Prompt_name"]]["fields"])

    return prompt_responses


def generate_random_page_reference():
    return [
        f"(p{random.randint(1, 100)})",
        f"(pp{random.randint(1, 5)}-{random.randint(5, 10)})",
    ][random.randint(0, 1)]


def assemble_prompts_to_yaml(prompts: dict):

    result = "prompts:\n\n"

    for prompt in prompts.keys():
        result += f"  - name: {prompt}\n"
        result += f"    return_type: {prompts[prompt]['return_type']}\n"
        result += "    fields:\n"
        for field in prompts[prompt]["fields"].keys():
            result += f"      - {field}\n"
        result += "    prompt: |\n"
        result += f"      {prompts[prompt]['prompt_question']}\n\n"
        for field in prompts[prompt]["fields"].keys():
            result += f"      Q{prompts[prompt]['fields'][field]['question_number']}: \
                {prompts[prompt]['fields'][field]['question_description']}\n"

        result += f"\n      {prompts[prompt]['return_instruction']}\n\n"

        # reconstruct a dictionary from the fields, keeping the key and "example" value

        fields = {
            field: prompts[prompt]["fields"][field]["example"]
            + f" {generate_random_page_reference()}"
            for field in prompts[prompt]["fields"].keys()
        }

        result += f"""        {{{str(json.dumps(fields, indent=10))[:-2]}
        }}}}

"""
        if prompts[prompt]["additional_instruction"]:
            result += f"      {prompts[prompt]['additional_instruction']}\n\n"

    return result


def main():
    args = parse_arguments()
    system = process_system_intro(args.input_file)
    print(system)
    prompts = process_prompts(args.input_file)
    # nicely print prompts dictionary with indent 4
    print(json.dumps(prompts, indent=4))
    assembled_prompts = assemble_prompts_to_yaml(prompts)
    print(assembled_prompts)

    final = system + "\n" + assembled_prompts
    with open(args.output_file, "w") as f:
        f.write(final)


if __name__ == "__main__":
    main()
