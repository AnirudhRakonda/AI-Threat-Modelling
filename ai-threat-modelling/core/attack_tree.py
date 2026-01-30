from llm.mistral_client import query_mistral

def generate_attack_tree(system_description):
    with open("prompts/attack_tree.txt") as f:
        prompt = f.read().format(system=system_description)

    return query_mistral(prompt)
