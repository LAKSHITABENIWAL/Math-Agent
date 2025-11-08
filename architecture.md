# Math Routing Agent - Architecture

```mermaid
graph TB
    subgraph Frontend
        UI[React Frontend]
        UI --> |HTTP Requests| API
    end

    subgraph Backend [FastAPI Backend]
        API[FastAPI Application] --> Router[Route Handler]
        
        Router --> |1| Guardrails[Guardrail Check]
        Router --> |2| ArithmeticHandler[Arithmetic Handler]
        Router --> |3| LinearSolver[Linear Equation Solver]
        Router --> |4| DerivativeLookup[Derivative Lookup]
        Router --> |5| KBSearch[Knowledge Base Search]
        Router --> |6| WebSearch[Web Search]
        Router --> |7| LLMFallback[LLM Fallback]
        Router --> |8| FeedbackHandler[Feedback Handler]

        Guardrails --> |Safety Check| SafetyLib[Safety Libraries]
        ArithmeticHandler --> |Compute| MathLib[Math Libraries]
        LinearSolver --> |Solve| MathLib
        DerivativeLookup --> |Search| MathLib
        KBSearch --> |Vector Search| VectorDB[Qdrant Vector DB]
        WebSearch --> |Search| TavilyAPI[Tavily API]
        LLMFallback --> |Generate| GroqAPI[Groq API]
        FeedbackHandler --> |Store| SQLiteDB[SQLite Database]

        VectorDB --> |Embeddings| SentenceTransformer[Sentence Transformer]
    end

    subgraph External Services
        GroqAPI
        TavilyAPI
    end

    subgraph Storage
        SQLiteDB
        VectorDB
    end

classDef frontend fill:#d4e6f1,stroke:#2874a6,stroke-width:2px;
classDef backend fill:#d5f5e3,stroke:#196f3d,stroke-width:2px;
classDef external fill:#fdebd0,stroke:#d35400,stroke-width:2px;
classDef storage fill:#ebdef0,stroke:#6c3483,stroke-width:2px;

class UI,Frontend frontend;
class API,Router,Guardrails,ArithmeticHandler,LinearSolver,DerivativeLookup,KBSearch,WebSearch,LLMFallback,FeedbackHandler,SafetyLib,MathLib,SentenceTransformer backend;
class GroqAPI,TavilyAPI external;
class SQLiteDB,VectorDB storage;
```

## Component Description

1. **Frontend**
   - React-based user interface
   - Makes HTTP requests to the backend API
   - Handles user interactions and displays results

2. **Backend**
   - FastAPI application handling all requests
   - Multiple specialized handlers for different types of math problems
   - Processing pipeline with priority order:
     1. Safety checks (Guardrails)
     2. Direct arithmetic computation
     3. Linear equation solving
     4. Derivative lookup
     5. Knowledge base search
     6. Web search
     7. LLM-based fallback

3. **External Services**
   - Groq API for LLM capabilities
   - Tavily API for web search

4. **Storage**
   - SQLite database for feedback storage
   - Qdrant vector database for knowledge base
   - Sentence Transformer for text embeddings

## Request Flow

1. User submits a math question through the React frontend
2. FastAPI backend receives the request
3. Question goes through the processing pipeline:
   - First, safety checks ensure the input is appropriate
   - Then, specialized handlers attempt to solve the problem
   - If no direct solution is found, knowledge base is searched
   - Web search and LLM fallback as last resort
4. Response is sent back to frontend
5. User can provide feedback, which is stored in SQLite database
6. Feedback can be used to improve knowledge base

## Technologies Used

- Frontend: React, JavaScript
- Backend: FastAPI, Python 3.13
- Databases: SQLite, Qdrant
- ML/AI: Sentence Transformers, Groq LLM
- External APIs: Tavily, Groq
- Math Libraries: Custom Python implementations