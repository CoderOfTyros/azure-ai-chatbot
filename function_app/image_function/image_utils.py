import os, requests, logging

endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT")
key = os.environ.get("AZURE_OPENAI_KEY")
deployment = os.environ.get("AZURE_OPENAI_DALLE_DEPLOYMENT")
api_version = os.environ.get("AZURE_OPENAI_API_VERSION", "2024-05-01-preview")

def generate_image(prompt: str, size="1024x1024"):
    # DALL-E deployment path
    url = f"{endpoint.rstrip('/')}/openai/deployments/{deployment}/images/generations?api-version={api_version}"
    headers = {"api-key": key, "Content-Type": "application/json"}
    payload = {"prompt": prompt, "size": size, "n": 1}

    response = requests.post(url, headers=headers, json=payload)

    if not response.ok:
        logging.error(f"Image API error {response.status_code}: {response.text}")

    response.raise_for_status()
    data = response.json()

    return data["data"][0].get("url") or data["data"][0].get("b64_json")

def sanitize_prompt(user_prompt: str) -> str:
    return (
        "Create a safe, family-friendly artistic illustration based on this request: "
        f"{user_prompt}"
    )
