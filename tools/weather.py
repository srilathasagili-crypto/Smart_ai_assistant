import requests
from langchain_core.tools import tool
from graph.config import OPENWEATHER_API_KEY

_BASE_URL = "https://api.openweathermap.org/data/2.5/weather"


@tool
def get_weather(city: str) -> str:
    """Get the current weather for a given city name, e.g. 'Hyderabad' or 'London'.
    Returns temperature in Celsius and a short condition description."""
    if not OPENWEATHER_API_KEY:
        return "Weather tool is not configured: missing OPENWEATHER_API_KEY."

    params = {
        "q": city,
        "appid": OPENWEATHER_API_KEY,
        "units": "metric",
    }

    try:
        response = requests.get(_BASE_URL, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.HTTPError:
        return f"Could not find weather for '{city}'. Check the city name and try again."
    except requests.exceptions.RequestException as e:
        return f"Weather service error: {e}"

    temp = data["main"]["temp"]
    feels_like = data["main"]["feels_like"]
    description = data["weather"][0]["description"]

    return (
        f"Weather in {city}: {temp}°C (feels like {feels_like}°C), {description}."
    )