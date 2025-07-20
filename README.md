# McDonald's Kuala Lumpur Outlet Finder

> **Advanced AI-powered McDonald's outlet discovery system with intelligent chatbot, interactive mapping, and comprehensive outlet information management.**

## 🌟 Project Overview

This project is a comprehensive solution for finding and managing McDonald's outlets in Kuala Lumpur, featuring web scraping, geocoding, interactive mapping, and an intelligent AI chatbot. Built as part of the MindHive Technical Assessment, it demonstrates modern web development practices, AI integration, and scalable architecture.

### ✨ Key Features

- **🔍 Intelligent Web Scraping**: Automated data extraction from McDonald's Malaysia website
- **🗺️ Interactive Mapping**: Real-time outlet visualization with 5KM radius analysis
- **🤖 AI-Powered Chatbot**: Natural language processing for outlet queries
- **📍 Precise Geocoding**: Multi-source location coordinate resolution
- **🔧 RESTful API**: Comprehensive backend service with FastAPI
- **📱 Modern Frontend**: Responsive web application with real-time features

## 🏗️ Architecture Overview

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Web Scraper   │────│    Database      │────│   FastAPI       │
│   (Selenium)    │    │   (MySQL)        │    │   Backend       │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │                        │
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Geocoding     │────│  Outlet Data     │    │   Frontend      │
│   Services      │    │  Coordinates     │    │   (HTML/JS)     │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │                        │
                       ┌──────────────────┐    ┌─────────────────┐
                       │   AI Chatbot     │────│  Interactive    │
                       │   (NLP/RAG)      │    │  Map (Leaflet)  │
                       └──────────────────┘    └─────────────────┘
```

## 🚀 Quick Start

### Prerequisites

- **Python**: 3.8 - 3.11 (recommended: 3.10)
- **MySQL**: 8.0+ or compatible
- **Chrome**: For Selenium WebDriver
- **Git**: For version control

### 1. Clone Repository

```bash
git clone <your-repository-url>
cd mcdonalds-outlet-finder
```

### 2. Environment Setup

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Database Configuration

```sql
-- Create database
CREATE DATABASE mcd_kualalumpur;
USE mcd_kualalumpur;

-- Create tables
CREATE TABLE outlets (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    address TEXT,
    waze_link TEXT,
    latitude DECIMAL(10, 8),
    longitude DECIMAL(11, 8)
);

CREATE TABLE perks (
    id INT AUTO_INCREMENT PRIMARY KEY,
    code VARCHAR(100) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL
);

CREATE TABLE outlet_perks (
  outlet_id INT NOT NULL,
  perk_id   INT NOT NULL,
  PRIMARY KEY (outlet_id, perk_id),
  FOREIGN KEY (outlet_id) REFERENCES outlets(id)  ON DELETE CASCADE,
  FOREIGN KEY (perk_id)   REFERENCES perks(id)    ON DELETE CASCADE
);
```

### 4. Configuration

Update database credentials in the Python files:

```python
# In mcd_kualalumpur.py, outlet_coords.py, and main.py
db_config = {
    'host': 'localhost',
    'user': 'username',
    'password': 'password',
    'database': 'mcd_kualalumpur'
}
```

### 5. Run the System

```bash
# Step 1: Scrape outlet data
python mcd_kualalumpur.py

# Step 2: Geocode coordinates
python outlet_coords.py

# Step 3: Start the API server
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# Step 4: Access the application
# Frontend: http://localhost:8000/static/index.html
# API Documentation: http://localhost:8000/docs
```

## 📋 Detailed Setup Instructions

### Part 1: Web Scraping Setup

1. **ChromeDriver Installation**:
   ```bash
   # Option 1: Use webdriver-manager (recommended)
   pip install webdriver-manager
   
   # Option 2: Manual download
   # Download ChromeDriver from https://chromedriver.chromium.org/
   # Add to PATH or place in project directory
   ```

2. **Run the scraper**:
   ```bash
   python mcd_kualalumpur.py
   ```

3. **Expected output**:
   ```
   [INFO] Initializing headless Chrome driver...
   [INFO] Driver initialized.
   [INFO] Processing outlet 1/45...
   [INFO] Saved 'McDonald's Pavilion KL' with perks: ['24 Hours', 'Drive-Thru']
   [INFO] All done.
   ```

### Part 2: Geocoding Setup

The geocoding script uses multiple services for accuracy:

1. **Nominatim** (OpenStreetMap) - Primary
2. **Photon** - Fallback
3. **Google Maps** (via Selenium) - Final fallback

```bash
python outlet_coords.py
```

**Progress visualization**:
```
[████████████████████████████████████████] 100.0% (45/45) McDonald's Pavilion KL        → GMap   | Updated: 43
```

### Part 3: API Development

**FastAPI Backend Features**:
- RESTful endpoints for outlet management
- Advanced AI chatbot with NLP
- Real-time query processing
- Comprehensive error handling
- API documentation with Swagger UI

**Key Endpoints**:
- `GET /outlets` - List all outlets
- `GET /outlets/{id}` - Get specific outlet
- `POST /chat` - AI chatbot interaction
- `GET /health` - System health check

### Part 4: Frontend Development

**Interactive Map Features**:
- Leaflet.js-based mapping
- 5KM radius visualization
- Outlet overlap detection

### Part 5: AI Chatbot

**Advanced NLP Features**:
- Intent recognition and reasoning
- Entity extraction (locations, services, time)
- Context-aware responses
- Service-specific querying
- Natural language understanding

**Supported Query Examples**:
```
• "Which outlets are open 24 hours?"
• "Show me outlets with birthday party services"
• "Where can I find McCafé in Bukit Bintang?" 
```

## 🛠️ Technical Decisions & Architecture

### Framework Selections

#### **1. FastAPI for Backend API**
**Decision**: FastAPI over Flask/Django
**Reasoning**:
- **Performance**: ASGI-based, significantly faster than WSGI frameworks
- **Type Safety**: Built-in Pydantic integration for request/response validation
- **Documentation**: Automatic OpenAPI/Swagger documentation generation
- **Async Support**: Native async/await support for concurrent operations
- **Modern Python**: Leverages Python 3.6+ type hints and modern features

#### **2. Selenium for Web Scraping**
**Decision**: Selenium over BeautifulSoup/Scrapy
**Reasoning**:
- **JavaScript Rendering**: McDonald's website heavily relies on JavaScript for content loading
- **Dynamic Content**: Handles AJAX requests and dynamic page updates
- **Pagination**: Can interact with "Load More" buttons programmatically
- **Real Browser Environment**: Mimics actual user interaction, reducing detection risk

#### **3. MySQL for Database**
**Decision**: MySQL over PostgreSQL/SQLite
**Reasoning**:
- **Relational Data**: Perfect for outlet-perk relationships with foreign keys
- **Performance**: Excellent performance for read-heavy operations
- **Ecosystem**: Wide tool support and hosting options
- **Familiarity**: Industry standard with extensive documentation

#### **4. Leaflet.js for Mapping**
**Decision**: Leaflet over Google Maps API
**Reasoning**:
- **Open Source**: No API key requirements or usage limits
- **Lightweight**: Smaller bundle size compared to Google Maps
- **Customizable**: Highly extensible with plugins
- **Cost-Effective**: Free for commercial use

### Architecture Patterns

#### **1. Multi-Source Geocoding Strategy**
```python
# Fallback chain for maximum accuracy
1. Nominatim (OpenStreetMap) - Free, reliable
2. Photon - Alternative free service
3. Google Maps (Selenium) - High accuracy fallback
```

**Benefits**:
- **Reliability**: Multiple fallbacks ensure high success rate
- **Cost Efficiency**: Free services first, expensive services as backup
- **Accuracy**: Different services excel in different regions

#### **2. Agentic AI Chatbot Design**
```python
class AgenticChatbot:
    def __init__(self):
        self.text_processor = TextProcessor()      # NLP processing
        self.knowledge_base = KnowledgeBase()      # Service knowledge
        self.conversation_memory = []              # Context retention
```

**Key Components**:
- **Intent Recognition**: Advanced reasoning for user intent
- **Entity Extraction**: Location, service, and temporal entity detection
- **Knowledge Base**: RAG-style service information storage
- **Context Memory**: Conversation history for better responses

#### **3. Service-Oriented Architecture**
```
┌─────────────────┐
│   Web Scraper   │ (Independent script)
└─────────────────┘
         │
┌─────────────────┐
│   Geocoding     │ (Independent script)
└─────────────────┘
         │
┌─────────────────┐
│   API Service   │ (FastAPI application)
└─────────────────┘
         │
┌─────────────────┐
│   Frontend      │ (Static web application)
└─────────────────┘
```

**Benefits**:
- **Modularity**: Each component can be developed/deployed independently
- **Maintainability**: Clear separation of concerns
- **Scalability**: Individual components can be scaled as needed
- **Testability**: Each service can be unit tested in isolation

### Database Schema Design

#### **Normalized Relational Design**
```sql
outlets (1) ←→ (N) outlet_perks (N) ←→ (1) perks
```

**Design Decisions**:
- **Normalization**: Prevents data duplication for perks
- **Flexibility**: Easy to add new perks without schema changes
- **Query Performance**: Optimized JOINs for common queries
- **Data Integrity**: Foreign key constraints ensure consistency

#### **Indexing Strategy**
```sql
-- Geospatial queries
CREATE INDEX idx_coordinates ON outlets(latitude, longitude);

-- Text searches
CREATE INDEX idx_outlet_name ON outlets(name);
CREATE INDEX idx_outlet_address ON outlets(address(100));

-- Join optimization
CREATE INDEX idx_outlet_perks_outlet ON outlet_perks(outlet_id);
CREATE INDEX idx_outlet_perks_perk ON outlet_perks(perk_id);
```

### AI/NLP Implementation

#### **Intent Classification System**
```python
intent_weights = {
    'location_search': 0.3,    # "Find outlets near X"
    'service_inquiry': 0.4,    # "Which outlets have Y?"
    'general_info': 0.2,       # "List all outlets"
    'navigation': 0.1          # "How to get to X?"
}
```

**Reasoning Process**:
1. **Entity Extraction**: Identify locations, services, time references
2. **Keyword Analysis**: Match against service knowledge base
3. **Context Evaluation**: Consider conversation history
4. **Intent Scoring**: Calculate confidence scores for each intent
5. **Response Generation**: Craft contextually appropriate responses

#### **Knowledge Base Design**
```python
service_knowledge = {
    '24_hours': {
        'keywords': ['24', 'hour', 'hours', 'all', 'day', 'night', 'late'],
        'perk_codes': ['24_HOURS'],
        'description': 'Outlets operating 24 hours a day'
    }
}
```

**Benefits**:
- **Semantic Understanding**: Maps natural language to database codes
- **Extensibility**: Easy to add new services and synonyms
- **Accuracy**: Reduces false positives in service matching

### Performance Optimizations

#### **1. Database Query Optimization**
- **Eager Loading**: Single query with JOINs instead of N+1 queries
- **Result Caching**: In-memory caching for frequently accessed data
- **Connection Pooling**: Reuse database connections

#### **2. Frontend Optimization**
- **Lazy Loading**: Load map markers only when visible
- **Debounced Search**: Reduce API calls during user input
- **Cached Responses**: Store API responses in browser cache

#### **3. Geocoding Efficiency**
- **Batch Processing**: Process multiple addresses in sequence
- **Progress Tracking**: Real-time progress updates with ASCII progress bar
- **Error Recovery**: Continue processing despite individual failures

## 🧪 Testing Strategy

### Unit Testing
```bash
# Install testing dependencies
pip install pytest pytest-asyncio httpx

# Run tests
pytest tests/ -v
```

### API Testing
```bash
# Test all endpoints
curl http://localhost:8000/health
curl http://localhost:8000/outlets
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "Which outlets are open 24 hours?"}'
```

### Database Testing
```sql
-- Verify data integrity
SELECT COUNT(*) FROM outlets WHERE latitude IS NOT NULL;
SELECT COUNT(*) FROM outlet_perks;
SELECT * FROM outlets o JOIN outlet_perks op ON o.id = op.outlet_id LIMIT 5;
```

## 🔧 Configuration Options

### Environment Variables
```bash
# Database configuration
export DB_HOST=localhost
export DB_USER=root
export DB_PASSWORD=your_password
export DB_NAME=mcd_kualalumpur

# API configuration
export API_HOST=0.0.0.0
export API_PORT=8000

# Scraping configuration
export SCRAPER_DELAY=2
export SCRAPER_HEADLESS=true
```

### Configuration Files
```python
# config.py
class Config:
    DB_CONFIG = {
        'host': os.getenv('DB_HOST', 'localhost'),
        'user': os.getenv('DB_USER', 'root'),
        'password': os.getenv('DB_PASSWORD', 'root'),
        'database': os.getenv('DB_NAME', 'mcd_kualalumpur')
    }
    
    SCRAPER_CONFIG = {
        'delay': int(os.getenv('SCRAPER_DELAY', 2)),
        'headless': os.getenv('SCRAPER_HEADLESS', 'true').lower() == 'true'
    }
```

## 📊 System Monitoring

### Health Check Endpoint
```bash
curl http://localhost:8000/health
```

**Response includes**:
- Database connection status
- Outlet count verification
- Chatbot initialization status
- Memory usage statistics

### Logging Configuration
```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)
```

## 🔒 Security Considerations

### 1. Database Security
- Use environment variables for credentials
- Enable SSL connections
- Regular backup and recovery procedures
- Input validation and SQL injection prevention

### 2. API Security
- Rate limiting on endpoints
- CORS configuration
- Input sanitization
- Error message sanitization

### 3. Web Scraping Ethics
- Respect robots.txt
- Implement reasonable delays
- Use rotating user agents
- Monitor for rate limiting

## 📈 Performance Metrics

### Expected Performance
- **Scraping**: ~45 outlets in 2-3 minutes
- **Geocoding**: ~45 addresses in 5-10 minutes
- **API Response**: < 100ms for typical queries
- **Chatbot Response**: < 500ms for complex queries
- **Map Loading**: < 2 seconds for all markers

### Scalability Considerations
- **Database**: Can handle 10,000+ outlets with current schema
- **API**: Supports 1000+ concurrent users with proper hosting
- **Chatbot**: Stateless design allows horizontal scaling

## 🐛 Troubleshooting

### Common Issues

#### 1. ChromeDriver Issues
```bash
# Error: ChromeDriver not found
# Solution: Install webdriver-manager
pip install webdriver-manager

# Or download manually and add to PATH
```

#### 2. Database Connection Issues
```python
# Error: Access denied for user
# Solution: Check credentials and privileges
GRANT ALL PRIVILEGES ON mcd_kualalumpur.* TO 'username'@'localhost';
```

#### 3. Geocoding Rate Limits
```python
# Error: Too many requests
# Solution: Increase delays in outlet_coords.py
PAUSE_OSM = 2.0  # Increase from 1.0 to 2.0 seconds
```

#### 4. Memory Issues During Scraping
```python
# Solution: Process in smaller batches
# Modify scrape_and_store() to process outlets in chunks
```

## 📚 API Documentation

### Core Endpoints

#### `GET /outlets`
List all McDonald's outlets with their services and coordinates.

**Response Example**:
```json
[
  {
    "id": 1,
    "name": "McDonald's Pavilion KL",
    "address": "Pavilion Kuala Lumpur, Bukit Bintang",
    "latitude": 3.1490,
    "longitude": 101.7143,
    "perks": ["24 Hours", "Drive-Thru", "McCafé"]
  }
]
```

#### `POST /chat`
Interact with the AI chatbot for intelligent outlet queries.

**Request Example**:
```json
{
  "question": "Which outlets are open 24 hours?",
  "user_location": "Kuala Lumpur",
  "context": {}
}
```

**Response Example**:
```json
{
  "answer": "Great news! I found 8 McDonald's outlets that operate 24 hours...",
  "outlets": [...],
  "intent": "service_inquiry",
  "confidence": 0.95,
  "reasoning": "Detected service keywords: ['24_hours']",
  "suggested_actions": ["Get directions", "View menu", "Check other services"]
}
```

#### `GET /health`
System health check with comprehensive status information.
