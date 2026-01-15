# Travel Data Aggregator API

A FastAPI service that aggregates real-time travel data from multiple public APIs (REST Countries and Open-Meteo) to provide comprehensive travel information including country details, weather data, and travel recommendations.

## Overview

This API serves as a data aggregation layer that:

- Fetches country information from REST Countries API
- Gets real-time weather data from Open-Meteo Weather API
- Generates personalized travel tips based on weather and region
- Provides best time to visit recommendations

**No API keys required** - all data sources are free public APIs!

## Features

- 🌍 **Country Information** - Population, currencies, languages, capital cities
- 🌤️ **Real-time Weather** - Current weather conditions in capital cities
- 💡 **Travel Tips** - Weather-based recommendations and cultural insights
- 📅 **Best Time to Visit** - Seasonal recommendations for each destination
- 🔍 **Country Search** - Find country codes by country name
- 🚀 **Fast & Async** - Built with FastAPI and async HTTP clients

## Prerequisites

- Python 3.8 or higher
- pip (Python package manager)

## Installation

1. Navigate to the backend-api directory:

   ```bash
   cd backend-api
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Running the API

Start the server:

```bash
python main.py
```

Or with uvicorn directly:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8080
```

The API will be available at:

- **Base URL**: `http://localhost:8080`
- **Interactive Docs**: `http://localhost:8080/docs`
- **ReDoc**: `http://localhost:8080/redoc`

## API Endpoints

### 1. Root Endpoint

**`GET /`**

Returns API information and available endpoints.

**Response:**

```json
{
  "message": "Travel Data Aggregator API",
  "description": "Aggregates data from multiple public APIs to provide travel information",
  "data_sources": [
    "REST Countries API - Country information",
    "Open-Meteo API - Weather data"
  ],
  "endpoints": { ... }
}
```

### 2. List Destinations

**`GET /destinations`**

Get a list of popular travel destinations with basic information.

**Response Model:** `List[Destination]`

**Example:**

```bash
curl http://localhost:8080/destinations
```

**Response:**

```json
[
  {
    "country_code": "JP",
    "country_name": "Japan",
    "capital": "Tokyo",
    "region": "Asia",
    "population": 123210000,
    "currencies": ["JPY"],
    "languages": ["Japanese"]
  },
  {
    "country_code": "FR",
    "country_name": "France",
    "capital": "Paris",
    "region": "Europe",
    "population": 67391582,
    "currencies": ["EUR"],
    "languages": ["French"]
  }
]
```

**Included Countries:**

- JP (Japan), FR (France), IT (Italy), ES (Spain), TH (Thailand)
- AU (Australia), GB (United Kingdom), DE (Germany), NZ (New Zealand), CA (Canada)

### 3. Search Destination by Name

**`GET /destinations/search?country=<country_name>`**

Search for a country by name and retrieve its country code.

**Query Parameters:**

- `country` (required): Country name (e.g., "Japan", "France", "Thailand")

**Response Model:** `CountryCodeResponse`

**Examples:**

```bash
# Search for Japan
curl "http://localhost:8080/destinations/search?country=Japan"

# Search with partial name
curl "http://localhost:8080/destinations/search?country=fran"

# Case insensitive
curl "http://localhost:8080/destinations/search?country=THAILAND"
```

**Response:**

```json
{
  "country_code": "JP",
  "country_name": "Japan"
}
```

**How it works:**

1. Searches popular destinations list first (fast)
2. If not found, queries REST Countries API for broader search
3. Returns first matching country with code and full name

**Error Response (404):**

```json
{
  "detail": "Country 'Atlantis' not found. Try: Japan, France, Italy, Spain, Thailand..."
}
```

### 4. Get Destination Info by Code

**`GET /destinations/{country_code}`**

Get detailed information about a specific destination using its 2-letter country code.

**Path Parameters:**

- `country_code` (required): 2-letter ISO country code (e.g., "JP", "FR", "TH")

**Response Model:** `Destination`

**Example:**

```bash
curl http://localhost:8080/destinations/JP
```

**Response:**

```json
{
  "country_code": "JP",
  "country_name": "Japan",
  "capital": "Tokyo",
  "region": "Asia",
  "population": 123210000,
  "currencies": ["JPY"],
  "languages": ["Japanese"]
}
```

**Error Response (404):**

```json
{
  "detail": "Country ZZ not found"
}
```

### 5. Get Travel Summary (Main Aggregation Endpoint)

**`POST /travel-summary`**

Get comprehensive travel information by aggregating data from multiple sources.

**Request Body:**

```json
{
  "country_code": "JP"
}
```

**Response Model:** `TravelSummary`

**Example:**

```bash
curl -X POST http://localhost:8080/travel-summary \
  -H "Content-Type: application/json" \
  -d '{"country_code": "JP"}'
```

**Response:**

```json
{
  "country_code": "JP",
  "country_name": "Japan",
  "capital": "Tokyo",
  "region": "Asia",
  "population": 123210000,
  "currencies": ["JPY"],
  "languages": ["Japanese"],
  "current_weather": {
    "location": "Tokyo",
    "temperature_celsius": 9.6,
    "weather_description": "Mainly clear",
    "humidity": 42,
    "wind_speed_kmh": 4.1
  },
  "travel_tips": [
    "Bring warm layers - it's cold!",
    "Pack a good jacket and warm accessories",
    "Learn a few local phrases - it's appreciated!",
    "Research local customs and etiquette for Japan"
  ],
  "best_time_to_visit": "March-May (cherry blossoms) or October-November (autumn colors)"
}
```

**What this endpoint does:**

1. Fetches country details from REST Countries API
2. Gets capital city coordinates using Open-Meteo Geocoding API
3. Fetches current weather from Open-Meteo Weather API
4. Generates context-aware travel tips
5. Provides seasonal recommendations

**Error Responses:**

_Missing country code (400):_

```json
{
  "detail": "country_code is required"
}
```

_Invalid country code (404):_

```json
{
  "detail": "Country ZZ not found"
}
```

_Geocoding failure (503):_

```json
{
  "detail": "Could not find coordinates for SomeCity"
}
```

### 6. Get Travel Summary by Name

**`POST /travel-summary-by-name`**

Get comprehensive travel information using a country name instead of code.

**Request Body:**

```json
{
  "country_name": "Japan"
}
```

**Response Model:** `TravelSummary` (same as /travel-summary)

**Example:**

```bash
curl -X POST http://localhost:8080/travel-summary-by-name \
  -H "Content-Type: application/json" \
  -d '{"country_name": "Japan"}'
```

**How it works:**

1. Searches for country in destinations list
2. Gets country code from match
3. Calls travel-summary logic with the code
4. Returns complete travel information

**Error Response (404):**

```json
{
  "detail": "Country 'Atlantis' not found in destinations. Available countries: Japan, France, Italy, Spain, Thailand..."
}
```

## Data Models

### Destination

```python
{
  "country_code": str,      # 2-letter ISO code
  "country_name": str,      # Full country name
  "capital": str,           # Capital city
  "region": str,            # Geographic region
  "population": int,        # Total population
  "currencies": List[str],  # Currency codes
  "languages": List[str]    # Spoken languages
}
```

### Weather

```python
{
  "location": str,              # City name
  "temperature_celsius": float, # Current temperature
  "weather_description": str,   # Weather condition
  "humidity": int,              # Humidity percentage
  "wind_speed_kmh": float      # Wind speed
}
```

### TravelSummary

```python
{
  **Destination,                    # All destination fields
  "current_weather": Weather,       # Weather object
  "travel_tips": List[str],         # Recommendations
  "best_time_to_visit": str        # Seasonal advice
}
```

### CountryCodeResponse

```python
{
  "country_code": str,  # 2-letter ISO code
  "country_name": str   # Full country name
}
```

## Data Sources

### REST Countries API

- **URL**: https://restcountries.com/v3.1
- **Purpose**: Country information, currencies, languages, population
- **Authentication**: None required
- **Rate Limits**: Generous, no API key needed

### Open-Meteo Geocoding API

- **URL**: https://geocoding-api.open-meteo.com/v1
- **Purpose**: Convert city names to coordinates
- **Authentication**: None required
- **Rate Limits**: 10,000 requests/day

### Open-Meteo Weather API

- **URL**: https://api.open-meteo.com/v1
- **Purpose**: Real-time weather data
- **Authentication**: None required
- **Rate Limits**: 10,000 requests/day

## Travel Tips Logic

The API generates intelligent travel tips based on:

1. **Temperature-based recommendations:**

   - Cold (< 15°C): Warm layers, jacket, accessories
   - Moderate (15-25°C): Light layers, comfortable clothing
   - Warm (25-35°C): Light clothing, sun protection, hydration
   - Hot (> 35°C): Minimal clothing, sun protection, hydration

2. **Regional insights:**

   - Asia: Learn local phrases, research customs
   - Europe: Bring power adapter, learn greetings
   - Americas: Check visa requirements, try local cuisine
   - Oceania: Sun protection, beach gear
   - Africa: Prepare for adventure, respect wildlife

3. **Weather-specific advice:**
   - Rainy: Pack umbrella, waterproof gear
   - Windy: Secure belongings, layer clothing

## Best Time to Visit

Seasonal recommendations are provided for each country based on:

- Climate patterns
- Tourist seasons
- Special events (e.g., cherry blossoms in Japan)
- Weather preferences

Examples:

- **Japan**: March-May (cherry blossoms) or October-November (autumn colors)
- **France**: April-June or September-October (pleasant weather, fewer crowds)
- **Thailand**: November-February (cool and dry season)

## Error Handling

The API uses standard HTTP status codes:

- **200 OK**: Successful request
- **400 Bad Request**: Missing required parameters
- **404 Not Found**: Country not found
- **503 Service Unavailable**: External API failure

All errors return JSON with a `detail` field:

```json
{
  "detail": "Error description"
}
```

## Integration with Kong Gateway

This API is designed to work with Kong's DataKit plugin for intelligent orchestration:

**Kong's `/travel` endpoint workflow:**

1. Receives: `{"country_name": "Japan"}`
2. Calls: `GET /destinations/search?country=Japan` → gets "JP"
3. Calls: `POST /travel-summary` with `{"country_code": "JP"}`
4. Returns: Complete travel information

This allows users to query by country name while the backend works with country codes.

## Development

### Running in Development Mode

```bash
# With auto-reload
uvicorn main:app --reload --port 8080

# With custom host
uvicorn main:app --reload --host 0.0.0.0 --port 8080
```

### Interactive API Documentation

Visit `http://localhost:8080/docs` for:

- Interactive API testing
- Request/response schemas
- Try-it-out functionality
- Automatic validation

### API Testing

Test individual endpoints:

```bash
# List destinations
curl http://localhost:8080/destinations

# Search by name
curl "http://localhost:8080/destinations/search?country=Japan"

# Get by code
curl http://localhost:8080/destinations/JP

# Get travel summary
curl -X POST http://localhost:8080/travel-summary \
  -H "Content-Type: application/json" \
  -d '{"country_code": "JP"}'

# Get travel summary by name
curl -X POST http://localhost:8080/travel-summary-by-name \
  -H "Content-Type: application/json" \
  -d '{"country_name": "Japan"}'
```

## Troubleshooting

**Port already in use:**

```bash
# Check what's using port 8080
lsof -i :8080

# Kill the process or use a different port
uvicorn main:app --reload --port 8081
```

**External API errors (503):**

- Public APIs may be temporarily unavailable
- Check your internet connection
- Wait a few moments and retry

**Geocoding failures:**

- Some smaller countries may not have coordinates in Open-Meteo
- The API will return a 503 error with details

**Dependencies not found:**

```bash
# Reinstall dependencies
pip install -r requirements.txt

# Or install individually
pip install fastapi uvicorn httpx pydantic
```

## Dependencies

- **FastAPI** - Modern web framework
- **Uvicorn** - ASGI server
- **httpx** - Async HTTP client
- **Pydantic** - Data validation
- **Python 3.8+** - Required Python version

## License

Apache 2.0

## Support

For issues or questions:

- Check the interactive docs at `/docs`
- Review error messages in responses
- Ensure all external APIs are accessible
- Verify Python version compatibility
