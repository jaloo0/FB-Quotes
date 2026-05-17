import logging
import random
from filmden.db.schema import get_genres_with_pending_movies, get_pending_movie

logger = logging.getLogger("filmden.pipeline.pick_movie")

def pick_movie_to_post() -> dict | None:
    """
    Picks a random pending movie from the database.
    First picks a random genre, then a random movie in that genre.
    """
    genres = get_genres_with_pending_movies()
    
    if not genres:
        logger.warning("No genres with pending movies found in the database.")
        return None
        
    chosen_genre = random.choice(genres)
    logger.info("Randomly picked genre: %s", chosen_genre)
    
    movie_row = get_pending_movie(chosen_genre)
    if not movie_row:
        logger.warning("Could not find a pending movie for genre %s despite it being in the list.", chosen_genre)
        return None
        
    movie = dict(movie_row)
    logger.info("Selected movie: %s (ID: %s)", movie['movie_name'], movie['id'])
    
    return movie

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    movie = pick_movie_to_post()
    if movie:
        print(f"\nMovie: {movie['movie_name']}")
        print(f"Genre: {movie['genre']}")
        print(f"Details: {movie['details']}")
