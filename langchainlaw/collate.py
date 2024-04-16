import argparse
import json
from pathlib import Path
from openpyxl import load_workbook
import re

from langchainlaw.cache import Cache

URI_RE = re.compile("https://www.caselaw.nsw.gov.au/decision/([0-9a-f]+)")


def load_config(cf_file):
    with open(cf_file, "r") as fh:
        cf = json.load(fh)
        return cf


def load_spreadsheet(columns, infile):
    wb = load_workbook(infile)
    cases = []
    ncols = len(columns)
    header = True
    for row in wb.active:
        if header:
            header = False
        else:
            case = {}
            for i in range(ncols):
                case[columns[i]] = row[i].value
            cases.append(case)
    return cases


def parse_case_uri(uri):
    if uri is None:
        return None
    m = URI_RE.match(uri)
    if m:
        return m.group(1)
    return None


def find_cached_results(cache, caseid, mapping):
    mapped = {}
    for field, spreadsheet in mapping.items():
        try:
            mapped[field] = cache.read(caseid, field)
        except Exception as e:
            mapped[field] = f"Cache read failed: {e}"
    return mapped


def collate():
    ap = argparse.ArgumentParser("collate-langchain")
    ap.add_argument(
        "--config",
        default="./collate_config.json",
        type=Path,
        help="Config file",
    )
    args = ap.parse_args()
    cf = load_config(args.config)
    cases = load_spreadsheet(cf["SPREADSHEET_COLS"], cf["SPREADSHEET_IN"])
    cache = Cache(cf["CACHE"])
    for case in cases:
        case_id = parse_case_uri(case["uri"])
        if case_id:
            llm_results = find_cached_results(cache, case_id, cf["MAPPING"])
            print(llm_results)


if __name__ == "__main__":
    collate()


# what this needs to do
# read the spreadsheet - which is in the scraper directory
# load the results from the cache for the given prompt
# collate the results against columns in the original spreadsheet

# so first thing is to map original spreadsheet columns to prompt names
