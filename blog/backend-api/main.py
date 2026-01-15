from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import httpx
import asyncio

app = FastAPI(title="Travel Data Aggregator API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Models
class Destination(BaseModel):
    country_code: str
    country_name: str
    capital: str
    region: str
    population: int
    currencies: List[str]
    languages: List[str]

class Weather(BaseModel):
    location: str
    temperature_celsius: float
    weather_description: str
    humidity: int
    wind_speed_kmh: float

class TravelSummary(BaseModel):
    country_code: str
    country_name: str
    capital: str
    region: str
    population: int
    currencies: List[str]
    languages: List[str]
    current_weather: Weather
    travel_tips: List[str]
    best_time_to_visit: str

class TravelRequest(BaseModel):
    country_code: Optional[str] = None

class TravelByNameRequest(BaseModel):
    country_name: str

class CountryCodeResponse(BaseModel):
    country_code: str
    country_name: str

# Public API endpoints (no API keys required)
REST_COUNTRIES_API = "https://restcountries.com/v3.1"
OPEN_METEO_API = "https://api.open-meteo.com/v1"
GEOCODING_API = "https://geocoding-api.open-meteo.com/v1"


@app.get("/")
def read_root():
    return {
        "message": "Travel Data Aggregator API",
        "description": "Aggregates data from multiple public APIs to provide travel information",
        "data_sources": [
            "REST Countries API - Country information",
            "Open-Meteo API - Weather data"
        ],
        "endpoints": {
            "destinations": "GET /destinations - List popular travel destinations",
            "destination_info": "GET /destinations/{country_code} - Get detailed country info",
            "travel_summary": "POST /travel-summary - Get aggregated travel summary with weather"
        }
    }


@app.get("/destinations", response_model=List[Destination])
async def get_destinations():
    """
    Get a list of popular travel destinations.
    Fetches real data from REST Countries API.
    """
    popular_codes = ["JP", "FR", "IT", "ES", "TH", "AU", "GB", "DE", "NZ", "CA"]
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(
                f"{REST_COUNTRIES_API}/alpha",
                params={"codes": ",".join(popular_codes)}
            )
            response.raise_for_status()
            countries_data = response.json()
        except httpx.HTTPError as e:
            raise HTTPException(status_code=503, detail=f"Failed to fetch country data: {str(e)}")
    
    destinations = []
    for country in countries_data:
        currencies = list(country.get("currencies", {}).keys()) if country.get("currencies") else ["N/A"]
        languages = list(country.get("languages", {}).values()) if country.get("languages") else ["N/A"]
        capital = country.get("capital", ["N/A"])[0] if country.get("capital") else "N/A"
        
        destinations.append(Destination(
            country_code=country.get("cca2", ""),
            country_name=country.get("name", {}).get("common", "Unknown"),
            capital=capital,
            region=country.get("region", "Unknown"),
            population=country.get("population", 0),
            currencies=currencies,
            languages=languages
        ))
    
    return destinations


@app.get("/destinations/search", response_model=CountryCodeResponse)
async def search_destination_by_name(country: str):
    """
    Search for a country by name and return its country code.
    Searches through the destinations list and returns the matching country code.
    Example: /destinations/search?country=Japan returns {'country_code': 'JP', 'country_name': 'Japan'}
    """
    country_name = country
    # Get all destinations
    destinations = await get_destinations()
    
    # Find matching country (case-insensitive partial match)
    for dest in destinations:
        if country_name.lower() in dest.country_name.lower() or dest.country_name.lower() in country_name.lower():
            return CountryCodeResponse(
                country_code=dest.country_code,
                country_name=dest.country_name
            )
    
    # If not found in popular destinations, try REST Countries API search
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(f"{REST_COUNTRIES_API}/name/{country_name}")
            response.raise_for_status()
            countries = response.json()
            if countries and len(countries) > 0:
                country = countries[0]
                return CountryCodeResponse(
                    country_code=country.get("cca2", ""),
                    country_name=country.get("name", {}).get("common", "Unknown")
                )
        except httpx.HTTPError:
            pass
    
    raise HTTPException(
        status_code=404,
        detail=f"Country '{country_name}' not found. Try: {', '.join([d.country_name for d in destinations[:5]])}..."
    )


@app.get("/destinations/{country_code}", response_model=Destination)
async def get_destination_info(country_code: str):
    """
    Get detailed information about a specific destination.
    Fetches real data from REST Countries API.
    """
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(f"{REST_COUNTRIES_API}/alpha/{country_code.upper()}")
            response.raise_for_status()
            country_data = response.json()
            if isinstance(country_data, list):
                country_data = country_data[0]
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise HTTPException(status_code=404, detail=f"Country {country_code} not found")
            raise HTTPException(status_code=503, detail=f"Failed to fetch country data: {str(e)}")
        except httpx.HTTPError as e:
            raise HTTPException(status_code=503, detail=f"Failed to fetch country data: {str(e)}")
    
    currencies = list(country_data.get("currencies", {}).keys()) if country_data.get("currencies") else ["N/A"]
    languages = list(country_data.get("languages", {}).values()) if country_data.get("languages") else ["N/A"]
    capital = country_data.get("capital", ["N/A"])[0] if country_data.get("capital") else "N/A"
    
    return Destination(
        country_code=country_data.get("cca2", ""),
        country_name=country_data.get("name", {}).get("common", "Unknown"),
        capital=capital,
        region=country_data.get("region", "Unknown"),
        population=country_data.get("population", 0),
        currencies=currencies,
        languages=languages
    )


async def get_coordinates(city: str, country_code: str) -> tuple:
    """Get latitude and longitude for a city using Open-Meteo Geocoding API."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(
                f"{GEOCODING_API}/search",
                params={"name": city, "count": 1, "format": "json"}
            )
            response.raise_for_status()
            data = response.json()
            if data.get("results"):
                result = data["results"][0]
                return result["latitude"], result["longitude"]
        except httpx.HTTPError:
            pass
    return None, None


async def get_weather_for_location(lat: float, lon: float, location_name: str) -> Weather:
    """Get current weather for coordinates using Open-Meteo API."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(
                f"{OPEN_METEO_API}/forecast",
                params={
                    "latitude": lat,
                    "longitude": lon,
                    "current": "temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m"
                }
            )
            response.raise_for_status()
            data = response.json()
            current = data.get("current", {})
            
            weather_codes = {
                0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
                45: "Foggy", 48: "Depositing rime fog", 51: "Light drizzle", 53: "Moderate drizzle",
                55: "Dense drizzle", 61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
                71: "Slight snow", 73: "Moderate snow", 75: "Heavy snow", 80: "Slight rain showers",
                81: "Moderate rain showers", 82: "Violent rain showers", 95: "Thunderstorm"
            }
            weather_code = current.get("weather_code", 0)
            
            return Weather(
                location=location_name,
                temperature_celsius=current.get("temperature_2m", 0),
                weather_description=weather_codes.get(weather_code, "Unknown"),
                humidity=current.get("relative_humidity_2m", 0),
                wind_speed_kmh=current.get("wind_speed_10m", 0)
            )
        except httpx.HTTPError as e:
            raise HTTPException(status_code=503, detail=f"Failed to fetch weather data: {str(e)}")


def generate_travel_tips(country_name: str, region: str, weather: Weather) -> List[str]:
    """Generate travel tips based on destination and weather."""
    tips = []
    
    if weather.temperature_celsius > 30:
        tips.append("Pack light, breathable clothing - it's hot!")
        tips.append("Stay hydrated and use sunscreen")
    elif weather.temperature_celsius < 10:
        tips.append("Bring warm layers - it's cold!")
        tips.append("Pack a good jacket and warm accessories")
    else:
        tips.append("Weather is mild - pack versatile clothing")
    
    if "rain" in weather.weather_description.lower() or "drizzle" in weather.weather_description.lower():
        tips.append("Bring an umbrella or rain jacket")
    
    region_tips = {
        "Europe": "Consider getting a travel adapter for EU plugs",
        "Asia": "Learn a few local phrases - it's appreciated!",
        "Oceania": "Don't forget reef-safe sunscreen for beach visits",
        "Americas": "Check visa requirements before traveling",
        "Africa": "Consult a travel health clinic for vaccinations"
    }
    if region in region_tips:
        tips.append(region_tips[region])
    
    tips.append(f"Research local customs and etiquette for {country_name}")
    
    return tips


def get_best_time_to_visit(region: str, country_code: str) -> str:
    """Get best time to visit based on region."""
    best_times = {
        "JP": "March-May (cherry blossoms) or October-November (autumn colors)",
        "FR": "April-June or September-October for mild weather",
        "IT": "April-June or September-October to avoid crowds",
        "ES": "March-May or September-November for pleasant weather",
        "TH": "November-February (cool and dry season)",
        "AU": "September-November (spring) or March-May (autumn)",
        "GB": "May-September for warmer weather",
        "DE": "May-September for outdoor activities",
        "NZ": "December-February (summer) for best weather",
        "CA": "June-August for summer, December-March for skiing"
    }
    return best_times.get(country_code, f"Research the best season for {region}")


@app.post("/travel-summary-by-name", response_model=TravelSummary)
async def get_travel_summary_by_name(request: TravelByNameRequest):
    """
    Get a comprehensive travel summary for a destination by country name.
    First searches for the country in the destinations list to get the code,
    then aggregates data from REST Countries API and Open-Meteo Weather API.
    Returns country info, current weather, and travel tips.
    """
    country_name = request.country_name.strip()
    
    # Get all destinations to search for the country
    destinations = await get_destinations()
    
    # Find matching country (case-insensitive partial match)
    matching_country = None
    for dest in destinations:
        if country_name.lower() in dest.country_name.lower() or dest.country_name.lower() in country_name.lower():
            matching_country = dest
            break
    
    if not matching_country:
        raise HTTPException(
            status_code=404, 
            detail=f"Country '{country_name}' not found in destinations. Available countries: {', '.join([d.country_name for d in destinations[:5]])}..."
        )
    
    country_code = matching_country.country_code
    
    # Fetch country information
    destination = await get_destination_info(country_code)
    
    # Get coordinates for the capital city
    lat, lon = await get_coordinates(destination.capital, country_code)
    
    if lat is None or lon is None:
        raise HTTPException(
            status_code=503, 
            detail=f"Could not find coordinates for {destination.capital}"
        )
    
    # Fetch weather data
    weather = await get_weather_for_location(lat, lon, destination.capital)
    
    # Generate travel tips
    tips = generate_travel_tips(destination.country_name, destination.region, weather)
    
    # Get best time to visit
    best_time = get_best_time_to_visit(destination.region, country_code)
    
    return TravelSummary(
        country_code=destination.country_code,
        country_name=destination.country_name,
        capital=destination.capital,
        region=destination.region,
        population=destination.population,
        currencies=destination.currencies,
        languages=destination.languages,
        current_weather=weather,
        travel_tips=tips,
        best_time_to_visit=best_time
    )


@app.post("/travel-summary", response_model=TravelSummary)
async def get_travel_summary(request: TravelRequest):
    """
    Get a comprehensive travel summary for a destination.
    Aggregates data from REST Countries API and Open-Meteo Weather API.
    Returns country info, current weather, and travel tips.
    """
    if not request.country_code:
        raise HTTPException(status_code=400, detail="country_code is required")
    
    country_code = request.country_code.upper()
    
    # Fetch country information
    destination = await get_destination_info(country_code)
    
    # Get coordinates for the capital city
    lat, lon = await get_coordinates(destination.capital, country_code)
    
    if lat is None or lon is None:
        raise HTTPException(
            status_code=503, 
            detail=f"Could not find coordinates for {destination.capital}"
        )
    
    # Fetch weather data
    weather = await get_weather_for_location(lat, lon, destination.capital)
    
    # Generate travel tips
    tips = generate_travel_tips(destination.country_name, destination.region, weather)
    
    # Get best time to visit
    best_time = get_best_time_to_visit(destination.region, country_code)
    
    return TravelSummary(
        country_code=destination.country_code,
        country_name=destination.country_name,
        capital=destination.capital,
        region=destination.region,
        population=destination.population,
        currencies=destination.currencies,
        languages=destination.languages,
        current_weather=weather,
        travel_tips=tips,
        best_time_to_visit=best_time
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
