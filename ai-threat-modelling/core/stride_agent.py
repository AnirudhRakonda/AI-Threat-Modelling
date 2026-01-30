from llm.mistral_client import query_mistral

def generate_stride_threats(system_description):
    with open("prompts/stride.txt") as f:
        prompt_template = f.read()

    prompt = prompt_template.format(system=system_description)
    return query_mistral(prompt)
