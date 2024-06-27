# Langchain Law

A Python library for classifying legal judgements using the langchain library
and OpenAI.

Example use:
<img width="1169" alt="Example data extraction from NSW inheritance caselaw" src="https://github.com/Sydney-Informatics-Hub/langchainlaw/assets/20785842/addf8ad5-83bf-4c49-a33a-d3b843e78167">
On this case: https://www.caselaw.nsw.gov.au/decision/54a004453004262463c948bc 

## Installation

Prerequisites: Git and [Poetry](https://python-poetry.org/docs/)

Get a copy of the repo using `git clone` and then set up your Python environment
and dependencies with `poetry install`:

```
	> git clone git@github.com:Sydney-Informatics-Hub/langchainlaw.git
	> cd langchainlaw
	> poetry install
```

## Command Line

The `classify` command will classify a directory containing judgments in the
json format output by the [nswcaselaw](https://github.com/Sydney-Informatics-Hub/nswcaselaw) library,
caching the LLM responses and writing the results out to a spreadsheet. It
is configured using a JSON file with the following format:

```
	{
	    "providers": {
	        "OpenAI": {
	            "api_key": "SECRET_GOES_HERE",
	            "organization": "ORG_KEY_GOES_HERE",
	            "model": "gpt-4o"
	        }
	    },
	    "provider": "OpenAI",
	    "temperature": 0,
	    "rate_limit": 15,
	    "input": "./input/",
	    "output": "./output/results.xlsx",
	    "cache": "./output/cache",
	    "prompts": "./prompts.yaml"
	}
```

You should make a copy of `config.example.json` as `config.json` before you
add your API keys.

The configurations for files and directories for input and output are as
follows:

* `input`: all .json files here will be read as cases
* `output`: results are written to this spreadsheet, one line per case
* `cache`: a directory will be created in this for each case, and results from the LLM for each prompt will be written to it in a file with that prompt's name.

The prompts.yaml file contains the prompts used to ask the LLM to answer
questions about the judgment.  This repository contains two prompts files:

```
	prompts.yaml - inefficient, sends a request for each question
	prompts_grouped.yaml - groups the questions into 7 requests
```

To run the `classify` command, use `poetry run`:

```
    > poetry run classify --config config.json
```

If you re-run the classifier, it will look in the cache for each case / prompt combination and return a cached result if it exists, rather than going to the LLM. For now, the only way to stop caching is to delete the cache file or directory for a prompt or case.

GPT-4o sometimes adds 'notes' to its output even when instructed to return JSON - these notes are also saved to the cache, although they are ignored when building the results spreadsheet.

## API


```
	from langchainlaw.langchainlaw import Classifier
	from pandas import DataFrame
	from pathlib import Path
	import json

	with open("config.json", "r") as cfh:
		config = json.load(cfh)

	classifier = Classifier(config)

	# classify a single case

	output = classifier.classify("cases/123456789abcdef0.json")

	# iterate over a directory and build a dataframe

	results = []
	for casefile in Path("cases").glob("*.json"):
		output = classifier.classify(casefile)
		results.append(classifier.as_dict(output))
	df = DataFrame(results)
```

See the [sample notebook](notebook.ipynb) for an example of using langchainlaw from a Jupyter notebook. To run this notebook locally use the following poetry command:

```
	> poetry run jupyter notebook notebook.ipynb
```

The notebook assumes that you have a `config.json` file with your OpenAI
keys in the root directory of the repo. 

## Prompts

The following is an example of one of the prompts from `prompts_grouped.yaml`.

This asks three questions about the filing date and any interlocutory application date. You can adjust the prompt text by editing the value of the `prompt` section.

Note that you need to make sure that the `fields` section has the same list of field names as the JSON example in the prompt.

```
  - name: dates
    return_type: json
    fields:
      - filing_date
      - interlocutory
      - interlocutory_date
    prompt: |
      answer the following questions about the case:

      Q1: what is the filing date? DD/MM/YYYY
      Q2: does this judgment concern an interlocutory application? Answer "yes", "no" or "unclear" 
      Q3: if the judgment concerns an interlocutory application, what was the date of the application? DD/MM/YYYY

      Return your answer as a JSON object, following this example:

        {{
          "filing_date": "5/6/2010",
          "interlocutory": "yes",
          "interlocutory_date": "4/3/2010"
        }}
```

It is possible to construct prompts which ask for multiple sets of JSON results: an example of this can be seen in the `parties` prompt:

```
  - name: parties
    return_type: json_multiple
    fields:
      - name
      - role_in_trial
      - representatives
      - costs
      - natural_person
      - relationship_to_party
      - is_dependant
      - misconduct
      - estranged
      - financial
      - family
      - illegal
      - contingent
    repeats: 6
    prompt: [...]
```

Where prompts have a `return_type` of `json_multiple`, the results will be 
written to the spreadsheet one set of columns at a time, with headers as follows:

```
    parties:1:name
    parties:1:role_in_trial
    parties:1:representatives
    [...]
    parties:2:name
    parties:2:role_in_trial
    parties:2:representatives
```

The maximum number of sets of headers written to the spreadsheet is controlled
by the `repeats` parameter. Note that if there are more than `repeats` values
returned by a prompt, all of the values will be written to the spreadsheet.