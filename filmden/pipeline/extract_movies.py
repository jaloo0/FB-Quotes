import os
import json
import logging
import requests
from youtube_transcript_api import YouTubeTranscriptApi
from filmden.db.schema import get_conn, insert_movie, mark_video, now

logger = logging.getLogger("filmden.pipeline.extract_movies")

OPENROUTER_BASE = "https://openrouter.ai/api/v1/chat/completions"
# Use a fast/free model for extraction
FREE_MODELS = [
    "google/gemini-2.0-flash-exp:free",
    "meta-llama/llama-3.3-70b-instruct:free",
    "google/gemma-2-9b-it:free",
    "mistralai/mistral-7b-instruct:free"
]

# from youtube_transcript_api import YouTubeTranscriptApi

def fetch_transcript(video_id: str) -> str | None:
    """Fetches the transcript for a video using RapidAPI to bypass IP blocks."""
    api_key = os.getenv("RAPIDAPI_KEY")
    if not api_key:
        logger.error("RAPIDAPI_KEY is not set.")
        return None

    try:
        url = "https://youtube-transcripts.p.rapidapi.com/youtube/transcript"
        querystring = {"url": f"https://www.youtube.com/watch?v={video_id}"}
        headers = {
            "x-rapidapi-host": "youtube-transcripts.p.rapidapi.com",
            "x-rapidapi-key": api_key
        }

        response = requests.get(url, headers=headers, params=querystring, timeout=30)
        response.raise_for_status()
        data = response.json()

        content = data.get("content")
        if not content:
            logger.warning("No transcript content found for video %s. Response: %s", video_id, data)
            return None

        # Parse the transcript blocks
        if isinstance(content, list):
            # The API formats blocks inside a 'content' key list containing dicts with 'text'
            lines = []
            for entry in content:
                if isinstance(entry, dict) and "text" in entry:
                    lines.append(entry["text"])
                else:
                    lines.append(str(entry))
            full_text = " ".join(lines)
        else:
            full_text = str(content)

        return full_text

    except Exception as e:
        logger.error("Failed to fetch transcript for video %s via RapidAPI: %s", video_id, e)
        return None

def extract_movies_via_ai(transcript_text: str) -> list[dict] | None:
    """Uses OpenRouter AI to extract movie names and details from the transcript."""
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        logger.error("OPENROUTER_API_KEY is not set.")
        return None

    # We might need to truncate the transcript if it's too long for the model
    # A typical 10 min video might have ~1500 words. Let's limit to ~15000 characters just in case.
    if len(transcript_text) > 15000:
        transcript_text = transcript_text[:15000]

    prompt = (
        "You are an expert film analyst and translator. "
        "The following is a YouTube video transcript (likely translated from Hindi to English or raw Hindi/Hinglish). "
        "The video talks about multiple movies. "
        "Your task is to extract every individual movie mentioned in the transcript. "
        "For each movie, provide the 'movie_name' (in English) and 'details', which is a 1-paragraph summary (in English) "
        "of what the host said about that specific movie, translating it to sound natural and engaging.\n\n"
        "Return the output STRICTLY as a JSON array of objects. "
        "Each object must have exactly two keys: 'movie_name' and 'details'. "
        "Do not include any other text or markdown formatting.\n\n"
        f"Transcript:\n{transcript_text}"
    )

    headers = {
        "Authorization": f"Bearer {api_key}",
        "HTTP-Referer": "https://github.com/jaloo0/FB-Quotes",
        "X-Title": "Filmden Content Extractor",
        "Content-Type": "application/json",
    }

    for model in FREE_MODELS:
        try:
            payload = {
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 1500,
                "temperature": 0.3, # Keep it focused for extraction
            }
            resp = requests.post(OPENROUTER_BASE, headers=headers, json=payload, timeout=60)
            resp.raise_for_status()
            text = resp.json()["choices"][0]["message"]["content"].strip()
            
            # Try to parse JSON. Some models wrap in ```json ... ```
            if text.startswith("```json"):
                text = text.replace("```json", "").replace("```", "").strip()
            elif text.startswith("```"):
                text = text.replace("```", "").strip()

            movies = json.loads(text)
            if isinstance(movies, list) and len(movies) > 0:
                logger.info("Successfully extracted %d movies using model %s", len(movies), model)
                return movies
            else:
                logger.warning("Model %s returned invalid or empty JSON array.", model)
                
        except json.JSONDecodeError:
             logger.warning("Model %s failed to return valid JSON. Output snippet: %s...", model, text[:100])
        except Exception as e:
            logger.warning("OpenRouter model %s failed: %s", model, e)
            continue

    return None

def process_pending_videos():
    """Finds pending videos, extracts movies, and saves them."""
    with get_conn() as conn:
        # Get up to 5 pending videos to process in this run
        rows = conn.execute("""
            SELECT video_id, playlist_id, genre 
            FROM videos 
            WHERE status = 'pending' AND movies_extracted = 0
            LIMIT 5
        """).fetchall()

    if not rows:
        logger.info("No pending videos to extract movies from.")
        return

    import time

    for row in rows:
        video_id = row["video_id"]
        playlist_id = row["playlist_id"]
        genre = row["genre"]

        logger.info("Processing video %s...", video_id)
        
        # Mark as using while we process
        mark_video(video_id, status="using")

        # 10s break to avoid YouTube rate limit/IP block
        time.sleep(10)

        transcript = fetch_transcript(video_id)
        if not transcript:
            # Mark as used even if failed, so we don't retry endlessly. Or mark as 'error'. Let's mark as 'error'
            mark_video(video_id, status="error")
            continue

        movies = extract_movies_via_ai(transcript)
        
        if movies:
            for movie in movies:
                movie_name = movie.get("movie_name")
                details = movie.get("details")
                if movie_name and details:
                    insert_movie(video_id, playlist_id, genre, movie_name, details)
            
            # Successfully extracted
            mark_video(video_id, status="used", movies_extracted=1)
            logger.info("Extracted and saved %d movies for video %s.", len(movies), video_id)
        else:
            # Failed to extract, mark as error
            mark_video(video_id, status="error")
            logger.error("Failed to extract movies for video %s.", video_id)

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    logging.basicConfig(level=logging.INFO)
    process_pending_videos()
