import argparse
import logging
import json
from pathlib import Path
from openpyxl import load_workbook, Workbook
import re

from langchainlaw.cache import Cache

logger = logging.getLogger(__name__)

URI_RE = re.compile("https://www.caselaw.nsw.gov.au/decision/([0-9a-f]+)")

MAX_RE = re.compile("context length")


def load_config(cf_file):
    """Load the config JSON"""
    with open(cf_file, "r") as fh:
        cf = json.load(fh)
        return cf


def load_spreadsheet(columns, infile):
    """Load the spreadsheet with the RA's summary of the case"""
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
    """Try to get a case ID from a URI in the input spreadsheet"""
    if uri is None:
        return None
    m = URI_RE.match(uri)
    if m:
        return m.group(1)
    return None


def find_cached_results(cache, caseid, mapping):
    """Look up a returned value from the LLM in the cache. Returns None if
    the case isn't in the cache or if the LLM request failed."""
    mapped = {}
    if not cache.exists(caseid):
        logger.debug(f"Case {caseid} not in cache")
        return None
    for field, spreadsheet in mapping.items():
        try:
            mapped[field] = cache.read(caseid, field)
            if MAX_RE.search(mapped[field]):
                logger.warning(f"Case {caseid} exceeded token length")
                return None
        except Exception as e:
            mapped[field] = f"Cache read failed: {e}"

    return mapped


def col_headers(field, mapping):
    """header or headers for a field, depending on mapping"""
    if type(mapping) is str:
        return [field]
    else:
        return list(mapping.keys())


def make_headers(out_cols):
    """Take the output columns and return a list of column headings by
    expanding the keys for multivalue columns"""
    nested = [col_headers(col, out_cols[col]) for col in out_cols.keys()]
    return sum(nested, [])


def multivalue(column, mapping, llm_json, ra_case):
    """Maps a multivalue result to columns for the llm and ra
    tables. Returns two arrays to be concatenated as rows. For example, with
    a mapping as follows

        "will_date": {
            "document": null,
            "paragraph": null,
            "date": "will_date"
        },

    and the llm_values a JSON string like

    '[ { "document": "Foo", "paragraph": "9", "date": "2008/01/10"}]'

    and the Ra value for will_date: "2008/01/12"

    This will return the following tuple llm_cols, ra_cols

    [ [ "Foo", "9", "2008/01/10" ] ] # the llm values
    [ "",     "", "2008/01/12" ]  # the RA values with None for missing fields

    LLM values are returned as a list of lists because there can be multiple
    values. These should be written into the spreadsheet as rows, like so

      "name", "role_in_trial", "representatives", "costs", "natural_person"[..]
      "Fred", "claimant", "Barristers", "yes", "yes"
      "Selma", "defendant", "Lawyer & sons", "no", "yes"

    It's up to the calling code to turn this into something sensible

    """
    ra_values = []
    # assume ra_values only have one set
    for llm_col, ra_col in mapping.items():
        if ra_col is not None:
            ra_values.append(ra_case[ra_col])
        else:
            ra_values.append("")
    # parse the llm json and build a row for each set of values
    llm_values = []
    if llm_json is None:
        llm_values = [["" for _ in mapping]]
    else:
        # this makes too many assumptions about the state of the JSON it gets
        try:
            llm_parsed = json.loads(llm_json)
            for llm_set in llm_parsed:
                llm_values.append([llm_set.get(f, "") for f in mapping.keys()])
        except Exception as e:
            logger.warning(f"JSON parse error in {column}: {e}")
            logger.warning(f"JSON: {llm_json}")
            llm_values = [["" for _ in mapping]]
            llm_values[0][0] = str(e)
    return llm_values, ra_values


def add_case_to_worksheet(ws, row, case_id, title, out_cols, ra_case, llm_results):
    """Add the RA values and the llm values for a single case to the worksheet.
    Multiple values from the LLM are spanned over multiple rows and the y-index
    for the next row is returned"""
    for r in [row, row + 1]:
        ws.cell(row=r, column=1).value = case_id
        ws.cell(row=r, column=2).value = title
    ws.cell(row=row, column=3).value = "RA"
    ws.cell(row=row + 1, column=3).value = "LLM"
    c = 4
    m = row
    print(f"Crosswalking {case_id}")
    for col, mapping in out_cols.items():
        if type(mapping) is str:
            try:
                v = ra_case[mapping]
            except KeyError as e:
                print(f"{mapping} couldn't get column {e}")
                v = ""
            ws.cell(row=row, column=c).value = v
            ws.cell(row=row + 1, column=c).value = llm_results[col]
            c = c + 1
        else:
            llm_values, ra_values = multivalue(col, mapping, llm_results[col], ra_case)
            for i in range(len(ra_values)):
                j = 1
                ws.cell(row=row, column=c + i).value = ra_values[i]
                for ll_set in llm_values:
                    ws.cell(row=row + j, column=c + i).value = ll_set[i]
                    j += 1
            if row + j > m:
                m = row + j
            c = c + len(ra_values)
    return m


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
    in_cols = cf["SPREADSHEET_IN_COLS"]
    out_cols = cf["SPREADSHEET_OUT_COLS"]
    ra_cases = load_spreadsheet(in_cols, cf["SPREADSHEET_IN"])
    cache = Cache(cf["CACHE"])
    results = Workbook()
    ws = results.active
    headers = ["case_id", "citation", "source"] + make_headers(out_cols)
    ws.append(headers)
    row = 2
    for ra_case in ra_cases:
        case_id = parse_case_uri(ra_case["uri"])
        title = ra_case["title"]
        if case_id:
            llm_results = find_cached_results(cache, case_id, out_cols)
            if llm_results is not None:
                row = add_case_to_worksheet(
                    ws,
                    row,
                    case_id,
                    title,
                    out_cols,
                    ra_case,
                    llm_results,
                )
    results.save(cf["SPREADSHEET_OUT"])
    logger.warning("Wrote collated results to " + cf["SPREADSHEET_OUT"])


if __name__ == "__main__":
    collate()


# what this needs to do
# collate the results against columns in the original spreadsheet

# so first thing is to map original spreadsheet columns to prompt names
