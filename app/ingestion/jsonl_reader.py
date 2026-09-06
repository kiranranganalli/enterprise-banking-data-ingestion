import json


def read_jsonl_records(file_path):
    with open(file_path, "r") as file:
        for line in file:

            line = line.strip()

            if not line:
                continue

            record = json.loads(line)

            yield record