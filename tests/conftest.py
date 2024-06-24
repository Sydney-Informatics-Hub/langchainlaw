import pytest


@pytest.fixture
def files():
    return {
        "config": "tests/config.json",
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
