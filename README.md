# AgroMind – AI Crop Disease Diagnosis & Recommendation Platform

## Project Summary

AgroMind is an AI-powered web application that helps farmers identify crop diseases from images and receive treatment recommendations and product suggestions.

The platform uses GPT-4.1-mini Vision to analyze crop images, a hybrid recommendation system that combines curated disease-to-product mappings with a TF-IDF-based Retrieval-Augmented Generation (RAG) pipeline, and GPT-4.1-mini to generate treatment guidance.

Key features include:

* AI-powered crop disease diagnosis
* Treatment recommendations
* Product recommendation system
* Product browsing and shopping cart
* User authentication (JWT)
* Diagnosis history tracking
* PostgreSQL database integration

---

## Requirements

### Software

* Python 
* Node.js 
* PostgreSQL

### Python Packages

Install using:

```bash
pip install -r ../../requirements.txt
```

### Accounts

* OpenAI API account with a valid API key

---

## Installation

### Backend Setup

Navigate to the backend folder:

```bash
cd backend
```

Create a virtual environment:

```bash
python -m venv .venv
```

Activate the virtual environment:

#### Windows (Git Bash)

```bash
source .venv/Scripts/activate
```

#### Windows (Command Prompt)

```bash
.venv\Scripts\activate
```

#### macOS / Linux

```bash
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r ../../requirements.txt
```

Create a PostgreSQL database named:

```text
agromind
```

Create a `.env` file in the `backend` directory and add the required configuration:

```env
OPENAI_API_KEY=your_openai_api_key_here
DATABASE_URL=postgresql://postgres:YOUR_POSTGRES_PASSWORD@localhost:5432/agromind
SECRET_KEY=your_secret_key_here
```

Generate the TF-IDF product index:

```bash
python ingest.py
```

Seed the disease-product mapping database:

```bash
python seed_db.py
```

Start the backend server:

```bash
uvicorn main:app --reload
```

Backend will run on:

```text
http://127.0.0.1:8000
```

---

### Frontend Setup

Open a separate terminal and navigate to the frontend folder:

```bash
cd frontend
```

Install dependencies:

```bash
npm install
```

Start the development server:

```bash
npm run dev
```

Open:

```text
http://localhost:5173
```

---

## API Keys & Environment Variables

Create a `.env` file inside the `backend` directory.

Example:

```env
OPENAI_API_KEY=your_openai_api_key
DATABASE_URL=postgresql://postgres:YOUR_POSTGRES_PASSWORD@localhost:5432/agromind
```

## Running the Project

Start the backend:

```bash
cd backend
source .venv/Scripts/activate
uvicorn main:app --reload
```

Start the frontend in a separate terminal:

```bash
cd frontend
npm run dev
```

---

## Known Issues

* Diagnosis accuracy depends on image quality and available visual information.
* Product recommendations rely on curated disease mappings and TF-IDF retrieval and may not always provide the optimal recommendation.
* Product catalog data may contain incomplete or inconsistent usage instructions.
* No administrative interface currently exists for managing products or the knowledge base.
* Checkout and payment functionality have not been implemented.
* Follow-up conversational Q&A with the AI assistant has not yet been implemented.

---

## Technologies Used

### Frontend

* React
* React Router
* CSS

### Backend

* FastAPI
* SQLAlchemy
* PostgreSQL
* JWT Authentication

### AI & Retrieval

* GPT-4.1-mini Vision
* GPT-4.1-mini
* TF-IDF Vectorization
* Cosine Similarity Search
* Retrieval-Augmented Generation (RAG)

### Deployment

* Docker
* Amazon EC2

