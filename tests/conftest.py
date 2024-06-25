import pytest


@pytest.fixture
def files():
    return {"config": "tests/config.json", "case": "tests/input/123456789abcdef0.json"}


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
        "will_date",
        "executor:name",
        "executor:representative",
        "parties1:name",
        "parties1:role_in_trial",
        "parties1:legal_representatives",
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
        "parties2:legal_representatives",
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
        "will_date": (
            """[{"document": "will", "paragraph": "1", "date": "19/12/2006"}, """
            """{"document": "will", "paragraph": "13", "date": "7/3/2010"}]"""
        ),
        "executor": {
            "name": "Joe Executor",
            "representative": "L Hutz",
        },
        "parties": [
            {
                "name": "John Smith",
                "role_in_trial": "Plaintiff",
                "legal_representatives": "R Bebbe",
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
