import os
from dotenv import load_dotenv
from veryfi import Client

load_dotenv()

client = Client(
    client_id=os.getenv("VERYFI_CLIENT_ID"),
    client_secret=os.getenv("VERYFI_CLIENT_SECRET"),
    username=os.getenv("VERYFI_USERNAME"),
    api_key=os.getenv("VERYFI_API_KEY")
)

print("Client initialized...")  

file_path = "./test/test.jpg"

# proses OCR
response = client.process_document(file_path)

items = response.get("line_items")

parsed_items = []

for item in items:
    parsed_items.append({
        "name": item.get("description"),
        "qty": item.get("quantity"),
        "price": item.get("unit_price"),
        "total": item.get("total")
    })

for i in parsed_items:
    print(i)