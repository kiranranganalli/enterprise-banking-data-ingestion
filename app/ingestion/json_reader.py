import json


def read_json_records(file_path):
    with open(file_path, "r") as file:
        data = json.load(file)

        for record in data:
            yield record