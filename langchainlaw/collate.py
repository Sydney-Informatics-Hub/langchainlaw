import argparse
import logging
from itertools import chain
import json
from pathlib import Path
from openpyxl import load_workbook, Workbook
import re
import sys

from langchainlaw.cache import Cache

logger = logging.getLogger(__name__)

URI_RE = re.compile("https://www.caselaw.nsw.gov.au/decision/([0-9a-f]+)")

MAX_RE = re.compile("context length")


def load_config(cf_file):
    """Load the config JSON"""
    with open(cf_file, "r") as fh:
        cf = json.load(fh)
        return cf


def expand_ra_cols(cf):
    """Looks for columns CLAIMANT and DEFENDANT in the list of input
    columns amd expands them out to n sets of columns from PARTIES_IN_COLS
    for each category, so we end up with

    claimant_1_relationship_to_party
    claimant_1_is_dependant
    [...]
    claimant_2_relationship_to_party
    claimant_2_is_dependant
    [...]

    and so on
    """

    base = [[c] for c in cf["SPREADSHEET_IN_COLS"]]
    party_cols = cf["PARTIES_IN_COLS"]
    n = cf["PARTIES_N"]
    for p in ["CLAIMANT", "DEFENDANT"]:
        partytype = p.lower()
        i = base.index([p])
        base[i] = [f"{partytype}_{i + 1}_{col}" for i in range(n) for col in party_cols]
    return list(chain.from_iterable(base))  # flattens list of lists


def load_ra_spreadsheet(config):
    """Load the spreadsheet with the RA's summary of the cases

    Returns a dict of ID -> list of spreadsheet rows
    """
    cases = {}
    header = True
    cols = expand_ra_cols(config)
    wb = load_workbook(config["SPREADSHEET_IN"])
    for row in wb.active:
        if header:
            header = False
        else:
            case = dict(zip(cols, [cell.value for cell in row]))
            case["id"] = parse_case_uri(case["uri"])
            if case["id"]:
                if case["id"] not in cases:
                    cases[case["id"]] = [case]
                else:
                    cases[case["id"]].append(case)
            else:
                uri = case["uri"]
                row_i = row[0].row
                logger.warning(f"Row [{row_i}]: Couldn't parse case ID from {uri}")
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


def make_headers(out_cols):
    """Take the output columns and return a list of column headings by
    expanding the keys for multivalue columns"""
    header = []
    subhead = []
    for col, mapping in out_cols.items():
        header.append(col)
        if type(mapping) is str:
            subhead.append("")
        else:
            subheads = list(mapping.keys())
            header += ["" for _ in subheads[1:]]
            subhead += subheads
    return header, subhead


def multivalue(column, mapping, ra_prefix, llm_json, ra_case):
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

    This will return the following tuple llm_values, ra_values

    [ [ "Foo", "9", "2008/01/10" ] ] # the llm values
    [ [ ]"",     "", "2008/01/12" ] ]  # the RA values with None for missing fields

    Values are returned as a list of lists because there can be multiple
    values for a case

      "name", "role_in_trial", "representatives", "costs", "natural_person"[..]
      "Fred", "claimant", "Barristers", "yes", "yes"
      "Selma", "defendant", "Lawyer & sons", "no", "yes"

    It's up to the calling code to turn this into something sensible

    """
    ra_values = []
    if column in ra_prefix:
        for prefix in ra_prefix[column]:
            ra_set = []
            for llm_col, ra_col in mapping.items():
                if ra_col is not None:
                    ra_set.append(ra_case.get(prefix + ra_col))
                else:
                    ra_set.append("")
            ra_values.append(ra_set)
    else:
        ra_set = []
        for llm_col, ra_col in mapping.items():
            if ra_col is not None:
                ra_set.append(ra_case[ra_col])
            else:
                ra_set.append("")
        ra_values = [ra_set]
    # parse the llm json and build a row for each set of values
    llm_values = []
    if llm_json is None:
        llm_values = [["" for _ in mapping]]
    else:
        try:
            llm_parsed = json.loads(llm_json)
            if type(llm_parsed) is not list:
                llm_parsed = [llm_parsed]
            for llm_set in llm_parsed:
                llm_values.append([llm_set.get(f, "") for f in mapping.keys()])
        except Exception as e:
            logger.warning(f"Parse error in multivalue {column}: {e}")
            logger.warning(f'JSON: "{llm_json}"')
            # fallback: if it can't be parsed as JSON write it into the first
            # of the multivalue columns
            llm_values = [["" for _ in mapping]]
            llm_values[0][0] = llm_json
    return llm_values, ra_values


def add_case_to_worksheet(
    ws, row, case_id, title, out_cols, ra_prefix, ra_case, llm_results
):
    """Add the RA values and the llm values for a single case to the worksheet.
    Both of these values can span multiple rows, this returns the row number
    for the next row."""

    llm_cols = []
    ra_cols = []

    for col, mapping in out_cols.items():
        if type(mapping) is str:
            ra_cols.append([ra_case.get(mapping, "")])
            llm_cols.append([llm_results[col]])
        else:
            llm_values, ra_values = multivalue(
                col, mapping, ra_prefix, llm_results[col], ra_case
            )
            width = len(ra_values[0])
            for i in range(width):
                ra_cols.append([ra_set[i] for ra_set in ra_values])
                llm_cols.append([llm_set[i] for llm_set in llm_values])

    ra_height = max([len(c) for c in ra_cols])
    llm_height = max([len(c) for c in llm_cols])
    llm_row = row + ra_height

    for r in [row, llm_row]:
        ws.cell(row=r, column=1).value = case_id
        ws.cell(row=r, column=2).value = title
    ws.cell(row=row, column=3).value = "RA"
    ws.cell(row=llm_row, column=3).value = "LLM"
    col0 = 4

    write_columns(ws, row, col0, ra_cols)
    write_columns(ws, llm_row, col0, llm_cols)

    return llm_row + llm_height


def write_columns(ws, row, col, columns):
    """Write a list of columns into a worksheet starting at row, col. The
    columns can have different heights."""
    for i in range(len(columns)):
        for j in range(len(columns[i])):
            ws.cell(row=row + j, column=col + i).value = columns[i][j]


def add_ra_parties(ws, row, col, ra_parties):
    """Hack to expand the 'parties' field in the RA spreadsheet into the
    multiple rows in the collated spreadsheet"""
    json_parties = ra_parties.replace("'", '"')
    try:
        parties = json.loads(json_parties)
        ws.cell(row=row, column=col).value = parties[0]
        if len(parties) > 2:
            logger.warning("case has more parties than expected:")
            logger.warning(str(parties))
            ws.cell(row=row + 1, column=col).value = ",".join(parties[1:])
        else:
            ws.cell(row=row + 1, column=col).value = parties[1]
    except Exception as e:
        logger.warning("Expanding RA parties failed")
        logger.warning(ra_parties)
        logger.warning(str(e))


def collate():
    ap = argparse.ArgumentParser("collate-langchain")
    ap.add_argument(
        "--config",
        default="./collate_config.json",
        type=Path,
        help="Config file",
    )
    ap.add_argument(
        "--flatten",
        action="store_true",
        default=False,
        help="Flatten multiple results into a single row",
    )
    args = ap.parse_args()
    cf = load_config(args.config)
    out_cols = cf["SPREADSHEET_OUT_COLS"]
    ra_prefix = cf["SPREADSHEET_IN_MULTI_PREFIX"]
    ra_cases = load_ra_spreadsheet(cf)
    # print(ra_cases)
    sys.exit(-1)
    cache = Cache(cf["CACHE"])
    results = Workbook()
    ws = results.active
    headers, subheads = make_headers(out_cols)
    ws.append(["case_id", "citation", "source"] + headers)
    ws.append(["", "", ""] + subheads)
    parties_c = 4 + headers.index("parties")
    row = 3
    for ra_case in ra_cases:
        case_id = parse_case_uri(ra_case["uri"])
        title = ra_case["title"]
        if case_id:
            llm_results = find_cached_results(cache, case_id, out_cols)
            if llm_results is not None:
                next_row = add_case_to_worksheet(
                    ws,
                    row,
                    case_id,
                    title,
                    out_cols,
                    ra_prefix,
                    ra_case,
                    llm_results,
                )
                add_ra_parties(ws, row, parties_c, ra_case["parties"])
                row = next_row
    results.save(cf["SPREADSHEET_OUT"])
    logger.warning("Wrote collated results to " + cf["SPREADSHEET_OUT"])


if __name__ == "__main__":
    collate()
