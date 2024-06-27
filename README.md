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



## API


```
	from langchainlaw.langchainlaw import Classifier
	from pandas import DataFrame
	from pathlib import Path

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

See the [sample notebook](./notebook.ipynb) for an example of using langchainlaw from a Jupyter notebook. To run this notebook, use the following poetry command:

```
	> poetry run jupyter notebook notebook.ipynb
```


