import pytest

NESTED_RESULTS = {
    "file": "tests/input/123456789abcdef0.json",
    "mnc": "This is a dummy case to feed to the classifier for tests",
    "dates": {
        "filing_date": "2010-06-05",
        "interlocutory": "yes",
        "interlocutory_date": "2010-03-04",
    },
    "deceased": {
        "date_of_death": "2008-05-02",
        "misconduct": "alleged",
        "name": "Susan Miller",
    },
    "wills": {
        "executor": "John Jones",
        "executor_representatives": "D Duck",
        "wills": (
            "5/6/1998 (will, p2); 3/4/2002 (will, p3);" " 5/10/2009 (codicil, p5)"
        ),
    },
    "legislation": {
        "acts": "Family Provision Act 1982",
        "other_claims": "None mentioned",
    },
    "outcome": {
        "successful": "no",
        "provision_awarded": (
            "The court awarded that each party should bear their own costs,"
            " with the defendants' costs to be paid out of the estate on"
            " an indemnity basis. (p9)"
        ),
        "costs_disputed": "yes",
        "costs_disputed_amount": "unclear",
        "costs_liable": (
            "Each party was liable for their own costs, with the"
            " defendants' costs to be paid out of the estate on an"
            " indemnity basis. (p9)"
        ),
        "mediation": "unclear",
        "mediation_date": "n/a",
    },
    "estate": {
        "assets": ("A property which was the principal asset of the estate" " (p7)"),
        "value": "Not stated",
        "family_home": "yes (p7)",
        "notional": "no",
        "distribution": (
            "The testator's wife left the whole of her estate to the"
            " plaintiff, but the testator wanted to treat his children"
            " equally (p6)"
        ),
    },
    "parties": [
        {
            "name": "John Smith",
            "role_in_trial": "Plaintiff",
            "representatives": "R Bebbe",
            "costs": (
                "Costs of the Notice of Motion to be the Plaintiff's "
                "costs in the cause (p35)"
            ),
            "natural_person": "true",
            "relationship_to_deceased": "son",
            "is_dependant": "false",
            "misconduct": "false",
            "estranged": "false",
            "financial": (
                "The plaintiff has an income of $90,000 per annum and " "no assets"
            ),
            "family": ("The plaintiff has three dependant children and is single"),
            "illegal": "false",
            "contingent": "not specified",
        },
        {
            "name": "Jane Doe",
            "role_in_trial": "Defendant",
            "representatives": "M Mouse",
            "costs": "none",
            "natural_person": "true",
            "relationship_to_deceased": "wife",
            "is_dependant": "false",
            "misconduct": "false",
            "estranged": "false",
            "financial": (
                "The party's financial circumstances "
                "are not detailed in the judgment"
            ),
            "family": (
                "The party's family and personal circumstances "
                "are not detailed in the judgment"
            ),
            "illegal": "false",
            "contingent": "not specified",
        },
    ],
}


@pytest.fixture
def files():
    return {
        "config": "tests/config.json",
        "case": "tests/input/123456789abcdef0.json",
        "prompt_spreadsheet": "tests/sample_prompts.xlsx",
        "prompt_json": "tests/sample_prompts.json",
    }


@pytest.fixture
def variants_of_json():
    return [
        {"string": '[ { "key": "value" }]', "json": [{"key": "value"}]},
        {
            "string": """
```json
{
    "here is some stuff": "hope you like it"
}
```
            """,
            "json": {"here is some stuff": "hope you like it"},
        },
    ]


@pytest.fixture
def headers():
    return [
        "file",
        "mnc",
        "dates:filing_date",
        "dates:interlocutory",
        "dates:interlocutory_date",
        "deceased:name",
        "deceased:date_of_death",
        "deceased:misconduct",
        "wills:wills",
        "wills:executor",
        "wills:executor_representatives",
        "legislation:acts",
        "legislation:other_claims",
        "outcome:successful",
        "outcome:provision_awarded",
        "outcome:costs_disputed",
        "outcome:costs_disputed_amount",
        "outcome:costs_liable",
        "outcome:mediation",
        "outcome:mediation_date",
        "estate:assets",
        "estate:value",
        "estate:family_home",
        "estate:notional",
        "estate:distribution",
        "parties1:name",
        "parties1:role_in_trial",
        "parties1:representatives",
        "parties1:costs",
        "parties1:natural_person",
        "parties1:relationship_to_deceased",
        "parties1:is_dependant",
        "parties1:misconduct",
        "parties1:estranged",
        "parties1:financial",
        "parties1:family",
        "parties1:illegal",
        "parties1:contingent",
        "parties2:name",
        "parties2:role_in_trial",
        "parties2:representatives",
        "parties2:costs",
        "parties2:natural_person",
        "parties2:relationship_to_deceased",
        "parties2:is_dependant",
        "parties2:misconduct",
        "parties2:estranged",
        "parties2:financial",
        "parties2:family",
        "parties2:illegal",
        "parties2:contingent",
    ]


@pytest.fixture
def results():
    return NESTED_RESULTS


@pytest.fixture
def flat_results():
    flat = {}
    for name, result in NESTED_RESULTS.items():
        if type(result) is str:
            flat[name] = result
        elif type(result) is dict:
            for field, answer in result.items():
                flat[f"{name}:{field}"] = answer
        else:
            for i in range(0, len(result)):
                for field, answer in result[i].items():
                    flat[f"{name}:{i + 1}:{field}"] = answer
    return flat
