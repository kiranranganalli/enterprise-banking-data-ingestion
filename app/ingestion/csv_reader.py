import csv


def read_csv_headers(file_path):
    with open(file_path, "r", newline="") as file:
        reader = csv.DictReader(file)
        return reader.fieldnames


def read_csv_records(file_path):
    with open(file_path, "r", newline="") as file:
        reader = csv.DictReader(file)

        for record in reader:
            yield record