import csv

file_path = "data/transactions.csv"

bad_records = [
    [
        "9999991", "9999991", "500", "CASH_OUT", "-250.00",
        "C12345", "1000", "1250", "C99999", "5000", "4750",
        "0", "0", "not equal", "error", "error", "C-C",
        "less than a month"
    ],
    [
        "9999992", "9999992", "500", "PAYMENT", "NOT_A_NUMBER",
        "C12346", "1000", "1000", "M99999", "0", "0",
        "0", "0", "not equal", "error", "error", "C-M",
        "less than a month"
    ],
    [
        "9999993", "9999993", "500", "", "500.00",
        "", "1000", "500", "C99998", "5000", "5500",
        "7", "0", "not equal", "error", "error", "C-C",
        "less than a month"
    ]
]

existing_ids = set()

with open(file_path, "r", newline="") as file:
    reader = csv.reader(file)
    next(reader)

    for row in reader:
        if row:
            existing_ids.add(row[0])

with open(file_path, "a", newline="") as file:
    writer = csv.writer(file)

    for record in bad_records:
        transaction_id = record[0]

        if transaction_id not in existing_ids:
            writer.writerow(record)
            print(f"Added transaction: {transaction_id}")
        else:
            print(f"Skipped duplicate: {transaction_id}")
