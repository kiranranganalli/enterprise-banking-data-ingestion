import httpx


url = "http://localhost:8000/data/api_transactions.json"

response = httpx.get(
    url,
    timeout=5.0,
)

print("Status code:", response.status_code)

transactions = response.json()

print("Number of transactions:", len(transactions))
print("First transaction:", transactions[0])