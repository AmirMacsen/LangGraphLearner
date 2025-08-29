from typing import Any

import httpx
from mcp.server import FastMCP

BASER_URL = "https://api.weather.gov"
USER_AGENT = "weather-app/1.0"
mcp = FastMCP(
    host="localhost",
    port=8000,
)

async def make_nws_request(url:str)-> dict[str, Any] | None:
    """
    查询天气信息
    :param url:
    :return:
    """
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/geo+json",
    }

    async with httpx.AsyncClient(headers=headers) as client:
        response = await client.get(url)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error: {response.status_code}")
            return None

def format_alert(feature:dict)->str:
    """
    格式化天气预警信息
    :param feature:
    :return:
    """
    props = feature["properties"]
    return f"""
    Event:{props.get('event','N/A')}
    Severity:{props.get('severity','N/A')}
    Areas:{props.get('areaDesc','N/A')}
    Description:{props.get('description','N/A')}
    Instruction:{props.get('instruction','N/A')}
    """


@mcp.tool()
async def get_alerts(state:str)-> str:
    """
    获取指定州的天气预警信息
    :param state: 州的缩写，例如CA, TX
    :return:
    """
    url = f"{BASER_URL}/alerts/active/area/{state}"
    data = await make_nws_request(url)
    if not data or "features" not in data:
        return "No alerts found."

    if not data["features"]:
        return "No alerts found."
    alerts = [format_alert(feature) for feature in data["features"]]
    return "\n".join(alerts)


@mcp.tool()
async def get_forecast(latitude: float, longitude: float) -> str:
    """Get weather forecast for a location.

    Args:        latitude: Latitude of the location        longitude: Longitude of the location    """
    points_url = f"{BASER_URL}/points/{latitude},{longitude}"
    points_data = await make_nws_request(points_url)

    if not points_data:
        return "Unable to fetch forecast data for this location."

    forecast_url = points_data["properties"]["forecast"]
    forecast_data = await make_nws_request(forecast_url)

    if not forecast_data:
        return "Unable to fetch detailed forecast."

    periods = forecast_data["properties"]["periods"]
    forecasts = []
    for period in periods[:5]:
        forecast = f"""  
        {period['name']}:  
        Temperature: {period['temperature']}°{period['temperatureUnit']}  
        Wind: {period['windSpeed']} {period['windDirection']}  
        Forecast: {period['detailedForecast']}  
        """
        forecasts.append(forecast)

    return "\n---\n".join(forecasts)


if __name__ == '__main__':
    mcp.run(transport="streamable-http")