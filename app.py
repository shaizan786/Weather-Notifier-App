import sqlite3

import requests
from flask import Flask, render_template, request, flash

app = Flask(__name__)
app.secret_key = "replace_with_secure_key"
DB_FILE = "weather_db.sqlite"
API_KEY = "YOUR-WEATHER-API-KEY"  # Replace with your actual WeatherAPI key


def init_db():
    """Initialize the SQLite database for favorites."""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS favorites (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                city_name TEXT UNIQUE
            )
        ''')
        conn.commit()
    except Exception as e:
        print(f"Database initialization error: {e}")
    finally:
        conn.close()


def get_favorites():
    """Return a list of favorite cities."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT city_name FROM favorites")
    rows = cursor.fetchall()
    conn.close()
    return [row[0] for row in rows]


def add_favorite(city):
    """Add a city to the favorites table."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO favorites (city_name) VALUES (?)", (city,))
    conn.commit()
    conn.close()


def fetch_weather(city):
    """
    Fetch current weather + 3-day forecast from WeatherAPI.
    Returns a dictionary with current weather data and forecast.
    """
    if not city:
        return None

    # Current Weather
    url_current = f"http://api.weatherapi.com/v1/current.json?key={API_KEY}&q={city}"
    r_current = requests.get(url_current)
    r_current.raise_for_status()
    data_current = r_current.json()
    if "current" not in data_current:
        return None

    # 3-day Forecast
    url_forecast = f"http://api.weatherapi.com/v1/forecast.json?key={API_KEY}&q={city}&days=3"
    r_forecast = requests.get(url_forecast)
    r_forecast.raise_for_status()
    data_forecast = r_forecast.json()
    if "forecast" not in data_forecast:
        return None

    current_data = data_current["current"]
    condition_text = current_data["condition"]["text"]
    temp_c = current_data["temp_c"]
    humidity = current_data["humidity"]
    wind_kph = current_data["wind_kph"]

    # Sunrise/Sunset from forecast (day 0)
    try:
        sunrise = data_forecast["forecast"]["forecastday"][0]["astro"]["sunrise"]
        sunset = data_forecast["forecast"]["forecastday"][0]["astro"]["sunset"]
    except KeyError:
        sunrise = "N/A"
        sunset = "N/A"

    # Chance of Rain (using every 3 hours of day 0 as an example)
    chance_of_rain = {}
    try:
        hours_data = data_forecast["forecast"]["forecastday"][0]["hour"]
        for h in hours_data[::3]:
            time_label = h["time"][-5:]  # e.g. "00:00"
            chance_label = f"{h.get('chance_of_rain', 0)}%"
            chance_of_rain[time_label] = chance_label
    except KeyError:
        pass

    # Build 3-day forecast
    forecast_days = []
    try:
        for day in data_forecast["forecast"]["forecastday"]:
            day_date = day["date"]
            icon_url = day["day"]["condition"]["icon"]
            low_temp = day["day"]["mintemp_c"]
            high_temp = day["day"]["maxtemp_c"]
            forecast_days.append({
                "date": day_date,
                "icon": icon_url,
                "low": low_temp,
                "high": high_temp
            })
    except KeyError:
        pass

    return {
        "city": city,
        "condition": condition_text,
        "temp_c": temp_c,
        "humidity": humidity,
        "wind_kph": wind_kph,
        "sunrise": sunrise,
        "sunset": sunset,
        "chance_of_rain": chance_of_rain,
        "forecast_days": forecast_days
    }


@app.route("/", methods=["GET", "POST"])
def home():
    weather_data = None
    if request.method == "POST":
        if "search" in request.form:
            city = request.form.get("city")
            if not city:
                flash("Please enter a city name.")
            else:
                try:
                    weather_data = fetch_weather(city)
                    if not weather_data:
                        flash("No weather data found.")
                except Exception as e:
                    flash(f"Error fetching weather: {e}")
        elif "favorite" in request.form:
            city = request.form.get("city")
            if not city:
                flash("City name cannot be empty.")
            else:
                add_favorite(city)
                flash(f"{city} added to favorites.")
                try:
                    weather_data = fetch_weather(city)
                except Exception as e:
                    flash(f"Error fetching weather: {e}")
    favorites = get_favorites()
    return render_template("index.html", weather=weather_data, favorites=favorites)


@app.route("/forecast", methods=["GET", "POST"])
def forecast():
    weather_data = None
    if request.method == "POST":
        city = request.form.get("city")
        if not city:
            flash("Please enter a city name for forecast.")
        else:
            try:
                weather_data = fetch_weather(city)
                if not weather_data:
                    flash("No weather data found.")
            except Exception as e:
                flash(f"Error fetching forecast: {e}")
    return render_template("forecast.html", weather=weather_data)


@app.route("/favorite/<city>")
def favorite_city(city):
    """Route to fetch weather for a favorite city."""
    weather_data = None
    try:
        weather_data = fetch_weather(city)
        if not weather_data:
            flash("No weather data found.")
    except Exception as e:
        flash(f"Error fetching weather for {city}: {e}")
    favorites = get_favorites()
    return render_template("index.html", weather=weather_data, favorites=favorites)


@app.route("/locations")
def locations():
    """Page listing favorite cities."""
    favorites = get_favorites()
    return render_template("locations.html", favorites=favorites)


if __name__ == "__main__":
    init_db()
    app.run(debug=True)
