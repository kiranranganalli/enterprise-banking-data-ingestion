import csv

source_path = "data/transactions.csv"
output_path = "data/transactions_1m.csv"

target_records = 1_000_000

with open(source_path, "r", newline="") as source_file:
    reader = csv.reader(source_file)

    header = next(reader)
    source_records = list(reader)


with open(output_path, "w", newline="") as output_file:
    writer = csv.writer(output_file)

    writer.writerow(header)

    for i in range(target_records):
        record = source_records[i % len(source_records)].copy()

        # Give each generated record a unique ID
        record[0] = str(10_000_000 + i)
        record[1] = str(10_000_000 + i)

        writer.writerow(record)


print(
    f"Created {output_path} with "
    f"{target_records:,} records"
)