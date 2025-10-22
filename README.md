# Web Agent Project

This project implements an AI agent that can scrape a given website URL, answer user-defined questions about its content using a LangGraph workflow powered by Gemini 2.5 Flash, and supports scheduled execution for recurring information retrieval.

## Architecture

The project follows a client-server architecture:
- **Frontend**: A Streamlit application for user interaction.
- **Backend**: A FastAPI application that orchestrates the LangGraph agent and handles scheduling.
- **Core Services**: Utilizes Gemini 2.5 Flash for LLM capabilities, a free embedding model (e.g., Nomic), and ChromaDB for local vector storage.

## Project Structure

```
web_agent_project/
├── backend/
│   ├── core/
│   │   └── agent.py              # LangGraph agent workflow definition
│   ├── data/                   # Directory for persistent data (e.g., ChromaDB)
│   ├── .env                    # Environment variables (e.g., GEMINI_API_KEY)
│   ├── main.py                 # FastAPI application and scheduler
│   └── requirements.txt        # Python dependencies for the backend
├── frontend/
│   └── streamlit_app.py        # Streamlit user interface
└── README.md                   # Project documentation
```

## Setup and Installation

1.  **Clone the repository (or create the files as provided):**

    ```bash
    git clone <repository_url>
    cd web_agent_project
    ```

2.  **Set up the backend:**

    Navigate to the `backend` directory:
    ```bash
    cd backend
    ```

    Create a `.env` file with your Gemini API key:
    ```
    GEMINI_API_KEY="YOUR_GEMINI_API_KEY"
    ```
    (Replace `YOUR_GEMINI_API_KEY` with your actual key. The key provided in the prompt was `AIzaSyDMnYlBvHxYXLI15g0BhMkNNxaLG496sqs`)

    Install the required Python packages:
    ```bash
    pip install -r requirements.txt
    ```

3.  **Run the backend server:**

    From the `backend` directory, start the FastAPI application:
    ```bash
    uvicorn main:app --host 0.0.0.0 --port 8000 --reload
    ```
    The `--reload` flag is optional but useful for development.

4.  **Run the frontend application:**

    Open a new terminal, navigate to the `frontend` directory:
    ```bash
    cd ../frontend
    ```

    Run the Streamlit application:
    ```bash
    streamlit run streamlit_app.py
    ```

## Usage

1.  Open your web browser and navigate to the address provided by Streamlit (usually `http://localhost:8501`).
2.  Enter the website URL you want to analyze.
3.  Provide a question or prompt for the AI agent.
4.  Select the mode (Q&A or Report).
5.  Choose a schedule: "Run Once" for immediate execution or a recurring interval (e.g., "Every 4 Hours").
6.  Click "Generate".

-   For "Run Once" tasks, the result will be displayed directly on the page.
-   For scheduled tasks, a confirmation message will appear. You can refresh the "Scheduled Tasks" section to see active schedules.

## Important Notes

-   **Local Storage**: Currently, results and scheduled tasks are stored in-memory in the FastAPI backend. This means data will be lost if the backend server restarts. For production, a persistent database (e.g., SQLite, PostgreSQL) would be required.
-   **Web Scraping Depth**: The recursive web scraping is limited to a depth of 3 to prevent excessive resource usage and potential abuse.
-   **Error Handling**: Basic error handling is in place, but robust error logging and reporting would be needed for a production system.
-   **Gemini API Key**: Ensure your `GEMINI_API_KEY` is correctly set in the `.env` file. If you encounter issues, double-check its validity and permissions.

