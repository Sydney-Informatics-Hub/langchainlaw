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
