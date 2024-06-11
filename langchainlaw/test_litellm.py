import litellm
import json

with open("config.json", "r") as fh:
    config = json.load(fh)

model = config["MODEL"]
cf = config["MODELS"][model]

litellm.set_verbose = True

print(f"Using config for {model}")

prompt = [
    {
        "content": "What is the plot of the Santaroga Barrier?",
        "role": "user",
    }
]

if model == "SIH_OPENAI":
    response = litellm.completion(
        model=cf["MODEL"],
        organization=cf["ORGANIZATION"],
        api_key=cf["API_KEY"],
        messages=prompt,
    )
else:
    headers = {
        "Content-type": "application/json",
        "Ocp-Apim-Subscription-Key": cf["API_KEY"],
    }
    response = litellm.completion(
        model="azure/" + cf["DEPLOYMENT"],
        api_base=cf["API_BASE"],
        api_version=cf["API_VERSION"],
        api_key=cf["API_KEY"],
        extra_headers=headers,
        messages=prompt,
    )
print(f"{model} response:\n")
print(response)
