import os
import psycopg2
import requests
from dotenv import load_dotenv

load_dotenv(".env.local")
load_dotenv(".env")
DB_URL = os.getenv("DATABASE_URL")

conn = psycopg2.connect(DB_URL)
cursor = conn.cursor()

# Get a chatbot
cursor.execute("SELECT id FROM chatbots LIMIT 1")
row = cursor.fetchone()
if not row:
    print("No chatbots found to test.")
    exit(0)

chatbot_id = row[0]
test_api_key = "test_key_12345"

cursor.execute("UPDATE chatbots SET api_key = %s WHERE id = %s", (test_api_key, chatbot_id))
conn.commit()
cursor.close()
conn.close()

# Test the API endpoint
url = "http://localhost:8000/api/v1/chat"
headers = {
    "x-api-key": test_api_key,
    "Content-Type": "application/json"
}
data = {
    "message": "Hello!"
}

response = requests.post(url, json=data, headers=headers)
print("Status Code:", response.status_code)
print("Response Text:", response.text)
