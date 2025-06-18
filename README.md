# Python API Project

This project is a FastAPI application with SQLite database, featuring a real-time dashboard with HTMX for dynamic updates and in-memory caching for optimal performance.

## Features

- **FastAPI**: Modern, fast web framework for building APIs
- **Pure SQL**: No ORM overhead, direct SQL queries for full control
- **SQLite**: Lightweight, file-based database
- **Real-time Dashboard**: Web interface with live updates using HTMX
- **In-memory Caching**: 10-second cache for dashboard data to reduce database load
- **SQL File Management**: Database schema and seed data managed via SQL files
- **Automatic Initialization**: Database setup on application startup
- **Type Safety**: Pydantic models for request/response validation

## Project Structure

```
python-api
├── app
│   ├── __init__.py
│   ├── main.py
│   ├── models
│   │   ├── __init__.py
│   │   ├── database.py    # Raw SQL database functions
│   │   └── item.py        # Pydantic models
│   ├── routers
│   │   ├── __init__.py
│   │   └── api.py         # API endpoints
│   ├── templates
│   │   └── dashboard.html # Dashboard web interface
│   └── utils
│       ├── __init__.py
│       ├── cache.py       # In-memory caching system
│       └── helpers.py
├── sql
│   ├── create_tables.sql  # Database schema
│   └── seed_data.sql      # Initial data
├── data
│   └── database.db        # SQLite database file
├── db_manager.py          # Database management script
├── requirements.txt
├── manifest.json
└── README.md
```

## Setup Instructions

1. **Clone the repository:**

   ```bash
   git clone <repository-url>
   cd python-api
   ```

2. **Create a virtual environment:**

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   ```

3. **Install the required dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

4. **Run the application:**

   ```bash
   uvicorn app.main:app --reload
   ```

5. **Access the application:**
   - **Dashboard**: <http://localhost:8000> - Real-time web interface
   - **API Documentation**: <http://localhost:8000/docs> - Interactive API docs
   - **Health Check**: <http://localhost:8000/health> - Service status

## Dashboard Features

### 🚀 Real-time Web Interface
- **Live Updates**: Dashboard refreshes every 2 seconds using HTMX
- **Total Item Count**: Shows current number of items in database
- **Recent Items**: Displays 10 most recently added items
- **Auto-refresh**: Updates automatically when new items are created

### ⚡ Performance Optimizations
- **In-memory Cache**: Dashboard data cached for 10 seconds
- **Smart Invalidation**: Cache automatically cleared when items are modified
- **Reduced Database Load**: Serves cached data unless expired or modified

### 🎨 Modern UI
- **Responsive Design**: Works on desktop and mobile devices
- **Professional Styling**: Clean, modern interface
- **Real-time Indicators**: Visual feedback during data updates

## API Endpoints

The API provides the following endpoints:

### Dashboard Routes
- `GET /` - Real-time dashboard web interface
- `GET /dashboard-stats` - Dashboard statistics (JSON/HTML)
- `GET /dashboard-items` - Recent items list (JSON/HTML)

### API Routes
- `GET /health` - Health check
- `GET /api/v1/items` - Get all items
- `GET /api/v1/items/{id}` - Get item by ID
- `POST /api/v1/items` - Create new item
- `PUT /api/v1/items/{id}` - Update item
- `DELETE /api/v1/items/{id}` - Delete item

## Database Management

Use the included database management script:

```bash
# Initialize database (first time setup)
python db_manager.py init

# Reset database (drop all tables and recreate)
python db_manager.py reset

# Add seed data
python db_manager.py seed

# Interactive SQL query mode
python db_manager.py query
```

## Usage

Once the application is running, you can:

1. **Access the API** at `http://127.0.0.1:8000`
2. **View API documentation** at `http://127.0.0.1:8000/docs` (Swagger UI)
3. **Use the ReDoc documentation** at `http://127.0.0.1:8000/redoc`

## Database Schema

The database uses pure SQL with the following table structure:

```sql
CREATE TABLE items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## SQL Files

- `sql/create_tables.sql` - Database schema definition
- `sql/seed_data.sql` - Initial sample data



## Publishing

### Setup Environment Variables

1. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and fill in your values:
   ```bash
   CONNECT_USERNAME=your_username
   CONNECT_SERVER=https://your-connect-server.com
   CONNECT_APP_ID=your-app-id-here
   CONNECT_API_KEY=your_api_key_here
   ```

### Publishing to RStudio Connect

Use the deployment script which automatically loads configuration from `.env`:

```bash
./deploy.sh
```

Or manually deploy:

```bash
# First deployment
rsconnect deploy fastapi . \
    --server $CONNECT_SERVER \
    --api-key $CONNECT_API_KEY \
    -e app.main:app \
    --title "Python FastAPI"

# Subsequent deployments (updates existing app)
rsconnect deploy fastapi . \
    --server $CONNECT_SERVER \
    --api-key $CONNECT_API_KEY \
    -e app.main:app \
    --app-id $CONNECT_APP_ID \
    --title "Python FastAPI"
```

**Note:** Environment variables referenced with `$` will be loaded from your `.env` file or shell environment.

## Testing the Dashboard

### 🎪 Dashboard Demo Script

Use the included demo script to see real-time updates in action:

```bash
# Start the API server
uvicorn app.main:app --reload

# In another terminal, run the demo script
python dashboard_demo.py
```

The demo script will:

- Create new items every 3 seconds
- Show the dashboard updating in real-time
- Demonstrate cache invalidation when items are added

### 🧪 Testing with test_api.py

The `test_api.py` script can test both local and deployed instances:

```bash
# Test local development server
uvicorn app.main:app --reload
python test_api.py

# Test deployed app (automatically uses .env values)
# If CONNECT_SERVER and CONNECT_APP_ID are set in .env:
python test_api.py 5  # Send 5 test requests

# Test specific URL
API_BASE_URL=https://your-server.com/content/your-app-id python test_api.py
```

**How it works:**
- Automatically loads `.env` and constructs deployed app URL from `CONNECT_SERVER` + `CONNECT_APP_ID`
- Falls back to localhost if .env is not present
- Supports `CONNECT_API_KEY` for authenticated requests

### 🧪 Manual Testing

You can also test manually using the API:

```bash
# Create a new item
curl -X POST "http://localhost:8000/api/v1/items" \
     -H "Content-Type: application/json" \
     -d '{"name": "Test Item", "description": "This is a test"}'

# Watch the dashboard update automatically!
```

## Cache System

### How It Works

- **10-second TTL**: Dashboard data is cached for 10 seconds
- **Smart Invalidation**: Cache is cleared when items are created, updated, or deleted
- **Thread-safe**: Uses threading locks for concurrent access
- **Memory efficient**: Automatic cleanup of expired entries

### Cache Statistics

Access cache statistics via the `/health` endpoint or by checking the application logs.
