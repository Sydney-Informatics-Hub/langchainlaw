import pytest


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
        "parties{n}:name",
        "parties{n}:role_in_trial",
        "parties{n}:representatives",
        "parties{n}:costs",
        "parties{n}:natural_person",
        "parties{n}:relationship_to_deceased",
        "parties{n}:is_dependant",
        "parties{n}:misconduct",
        "parties{n}:estranged",
        "parties{n}:financial",
        "parties{n}:family",
        "parties{n}:illegal",
        "parties{n}:contingent",
    ]
