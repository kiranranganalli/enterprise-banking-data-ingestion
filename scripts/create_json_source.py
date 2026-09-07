import csv
import json


csv_path = "data/transactions.csv"
json_path = "data/partner_transactions.json"

records = []


with open(csv_path, "r", newline="") as csv_file:
    reader = csv.DictReader(csv_file)

    for index, row in enumerate(reader):

        if index == 10:
            break

        json_record = {
            "transaction_id": row["Unnamed: 0"],
            "transaction_type": row["type"],
            "transaction_amount": row["amount"],
            "source_account": row["nameOrig"],
            "destination_account": row["nameDest"],
            "fraud_flag": row["isFraud"],
        }

        records.append(json_record)


with open(json_path, "w") as json_file:
    json.dump(
        records,
        json_file,
        indent=2,
    )


print(
    f"Created {json_path} "
    f"with {len(records)} records"
)