import pytest


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
    return {
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
            "assets": (
                "A property which was the principal asset of the estate" " (p7)"
            ),
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
                "legal_representatives": "R Bebbe",
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
                "legal_representatives": "M Mouse",
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
def flat_results():
    return {
        "file": "tests/input/123456789abcdef0.json",
        "mnc": "This is a dummy case to feed to the classifier for tests",
        "will_date": (
            """[{"document": "will", "paragraph": "1", "date": "19/12/2006"}, """
            """{"document": "will", "paragraph": "13", "date": "7/3/2010"}]"""
        ),
        "executor:name": "Joe Executor",
        "executor:representative": "L Hutz",
        "parties:1:name": "John Smith",
        "parties:1:role_in_trial": "Plaintiff",
        "parties:1:legal_representatives": "R Bebbe",
        "parties:1:costs": (
            "Costs of the Notice of Motion to be the Plaintiff's "
            "costs in the cause (p35)"
        ),
        "parties:1:natural_person": "true",
        "parties:1:relationship_to_deceased": "son",
        "parties:1:is_dependant": "false",
        "parties:1:misconduct": "false",
        "parties:1:estranged": "false",
        "parties:1:financial": (
            "The plaintiff has an income of $90,000 per annum and no assets"
        ),
        "parties:1:family": (
            "The plaintiff has three dependant children and is single"
        ),
        "parties:1:illegal": "false",
        "parties:1:contingent": "not specified",
        "parties:2:name": "Jane Doe",
        "parties:2:role_in_trial": "Defendant",
        "parties:2:legal_representatives": "M Mouse",
        "parties:2:costs": "none",
        "parties:2:natural_person": "true",
        "parties:2:relationship_to_deceased": "wife",
        "parties:2:is_dependant": "false",
        "parties:2:misconduct": "false",
        "parties:2:estranged": "false",
        "parties:2:financial": (
            "The party's financial circumstances " "are not detailed in the judgment"
        ),
        "parties:2:family": (
            "The party's family and personal circumstances "
            "are not detailed in the judgment"
        ),
        "parties:2:illegal": "false",
        "parties:2:contingent": "not specified",
    }
