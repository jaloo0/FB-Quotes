import os
import requests
from dotenv import load_dotenv

load_dotenv()

TMDB_API_KEY = "30959d8b46ef03ac4c8b81d06be9ba18"
movie_name = "Inception"

url = f"https://api.themoviedb.org/3/search/movie"
params = {
    "api_key": TMDB_API_KEY,
    "query": movie_name
}
resp = requests.get(url, params=params)
data = resp.json()

if data.get("results"):
    first_movie = data["results"][0]
    poster_path = first_movie.get("poster_path")
    backdrop_path = first_movie.get("backdrop_path")
    print(f"Movie: {first_movie['title']}")
    print(f"Poster URL: https://image.tmdb.org/t/p/original{poster_path}")
    print(f"Backdrop URL: https://image.tmdb.org/t/p/original{backdrop_path}")
else:
    print("No results found.")
