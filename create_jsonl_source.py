import json

input_file = "data/partner_transactions.json"
output_file = "data/partner_transactions.jsonl"

with open(input_file, "r") as source_file:
    records = json.load(source_file)

with open(output_file, "w") as output:
    for record in records:
        output.write(json.dumps(record) + "\n")

print(f"Created {output_file}")