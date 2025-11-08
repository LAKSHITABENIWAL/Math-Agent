# backend/test_tavily_search.py
from web_search_helper import search_web
q = "Who proved Fermat's Last Theorem?"
print("Query:", q)
res = search_web(q, depth="basic", limit=3)
print("Result:", res)

