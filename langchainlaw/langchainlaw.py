import argparse
import json
import sys
from pathlib import Path
from langchain.chat_models import ChatOpenAI
from openpyxl import Workbook


from langchainlaw.prompts import CaseChat


def load_config(cf_file):
    with open(cf_file, "r") as fh:
        cf = json.load(fh)
        return cf


def load_case(casefile):
    with open(casefile, "r") as file:
        return json.load(file)
    # judgment = data.pop("judgment")
    # return judgment


def classify():
    ap = argparse.ArgumentParser("langchain-law")
    ap.add_argument(
        "--config",
        default="./config.json",
        type=Path,
        help="Config file",
    )
    ap.add_argument(
        "--test",
        action="store_true",
        default=False,
        help="Run without making calls to OpenAI, for testing prompts",
    )
    ap.add_argument(
        "--case",
        default="",
        type=str,
        help="Select a single case by its filename",
    )
    ap.add_argument(
        "--prompt",
        default="",
        type=str,
        help="Generate results from only one prompt",
    )
    ap.add_argument(
        "--output",
        default="./results.xlsx",
        type=Path,
        help="Output spreadsheet",
    )
    args = ap.parse_args()
    cf = load_config(args.config)
    prompts = CaseChat(cf["PROMPTS"])
    if args.prompt:
        if not prompts.prompt(args.prompt):
            print(f"No prompt defined with name '{args.prompt}'")
            sys.exit()
    chat = None
    if not args.test:
        chat = ChatOpenAI(
            model_name=cf["OPENAI_CHAT_MODEL"],
            openai_api_key=cf["OPENAI_API_KEY"],
            openai_organization=cf["OPENAI_ORGANIZATION"],
            temperature=cf["TEMPERATURE"],
        )

    workbook = Workbook()
    worksheet = workbook.active

    if not args.prompt:
        worksheet.append(["file", "mnc"] + prompts.prompt_names)

    if args.case:
        case = Path(cf["INPUT"]) / Path(args.case)
        if not case.is_file():
            print(f"Case file {args.case} not found")
            sys.exit()
        cases = [case]
    else:
        cases = Path(cf["INPUT"]).glob("*.json")

    for casefile in cases:
        judgment = load_case(casefile)
        print("Case: " + judgment["mnc"])
        # results = [str(casefile), judgment["mnc"]]

        system_prompt = prompts.start_chat()

        if not args.test:
            response = chat([system_prompt])

        # message = prompts.start_judgment(judgment)
        # print(message)
        # print("\n...\n\n")

        # if not args.test:
        #     response = chat([message])
        #     print(response)
        #     print("\n----\n\n")

        for message in prompts.next_prompt(judgment):
            if not args.test:
                try:
                    response = chat([message])
                    try:
                        json_response = json.loads(response.content)
                        outfile = Path(cf["OUTPUT"]) / Path(casefile.name)
                        with open(outfile, "w") as fh:
                            json.dump(json_response, fh, indent=2)
                    except json.decoder.JSONDecodeError as e:
                        textout = outfile.with_suffix(".txt")
                        print(f"invalid JSON in response: {e}")
                        print(f"writing raw content to {textout}")
                        with open(textout, "w") as fh:
                            fh.write(response.content)
                except Exception as e:
                    print(f"Error classifying {casefile}: {e}")

    #     for prompt in prompts:
    #         prompt_str = prompt.make_prompt(metadata, judgment)
    #         output = None
    #         if args.test:
    #             output = prompt_str
    #         else:
    #             output = chat(prompt_str)
    #             if prompt.multiple:
    #                 for follow_up in prompt.multiple_prompt(output):
    #                     more_output = llm(prompt_str)
    #         if args.prompt:
    #             print(output)
    #         else:
    #             results.append(output)
    #     if not args.prompt:
    #         worksheet.append(results)

    # if not args.prompt:
    #     workbook.save(args.output)


if __name__ == "__main__":
    classify()
