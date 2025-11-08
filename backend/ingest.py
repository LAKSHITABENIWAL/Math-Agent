# backend/ingest.py
import requests, json

KB = [
    {"id":"q1","question":"What is 2+2?","answer":"2 + 2 = 4. Explanation: 2 plus 2 equals 4."},
    {"id":"q2","question":"Solve 2x + 5 = 15","answer":"Step 1: subtract 5 => 2x = 10. Step 2: divide by 2 => x = 5."},
    {"id":"q3","question":"Derivative of x^2","answer":"Derivative of x^2 with respect to x is 2x."}
]

def ingest():
    resp = requests.post("http://localhost:5000/api/ingest", json={"items": KB})
    print(resp.status_code)
    try:
        print(resp.json())
    except Exception:
        print(resp.text)

if __name__ == "__main__":
    ingest()
