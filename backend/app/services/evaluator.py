import logging
from typing import Any

from app.models.albums import AlbumData

logger = logging.getLogger('deepcuts')


class AlbumEvaluator:
    """Evaluate AI-generated album recommendations for quality issues."""

    def __init__(self):
        self.issues = []

    def evaluate(self, albums: list[AlbumData], original_query: str) -> dict[str, Any]:
        """Evaluate a list of album recommendations.

        Returns:
            dict with score (0-100), issues found, and recommendations for improvement
        """
        self.issues = []

        if not albums or len(albums) == 0:
            self.issues.append("No albums returned")
            return {"score": 0, "issues": self.issues, "passed": False}

        score = 100

        # Check 1: Do we have 10 albums?
        if len(albums) < 10:
            self.issues.append(f"Only {len(albums)} albums returned (expected 10)")
            score -= (10 - len(albums)) * 5

        # Check 2: Are explanations detailed enough?
        vague_count = 0
        for album in albums:
            if not album.reasoning or len(album.reasoning) < 50:
                vague_count += 1
            elif any(word in album.reasoning.lower() for word in ['similar', 'like', 'same', 'vibe']):
                if len(album.reasoning) < 80:
                    vague_count += 1

        if vague_count > 0:
            self.issues.append(f"{vague_count} albums have vague or short explanations")
            score -= vague_count * 3

        # Check 3: Are titles in original language? (heuristic)
        translated_count = 0
        for album in albums:
            # If query contains non-ASCII but result is ASCII, might be translated
            if any(ord(c) > 127 for c in original_query):
                if all(ord(c) < 128 for c in album.title):
                    # Check if it's a known Japanese album that should have Japanese title
                    translated_count += 1

        if translated_count > 2:
            self.issues.append(f"{translated_count} albums may be translated from original language")
            score -= translated_count * 2

        # Check 4: Genre specificity
        generic_genres = ['pop', 'rock', 'jazz', 'electronic', 'hip hop', 'r&b']
        generic_count = 0
        for album in albums:
            if album.genre and album.genre.lower().strip() in generic_genres:
                generic_count += 1

        if generic_count > 3:
            self.issues.append(f"{generic_count} albums have overly generic genres")
            score -= generic_count * 2

        # Check 5: Diversity of artists
        artists = [a.artist for a in albums]
        unique_artists = len(set(artists))
        if unique_artists < len(albums) * 0.7:
            self.issues.append(f"Low artist diversity: {unique_artists} unique artists for {len(albums)} albums")
            score -= 10

        # Check 6: Year range
        years = [a.year for a in albums if a.year]
        if years:
            year_range = max(years) - min(years)
            if year_range < 5:
                self.issues.append(f"Narrow year range: only {year_range} years covered")
                score -= 5

        score = max(0, min(100, score))

        return {
            "score": score,
            "issues": self.issues,
            "passed": score >= 70,
            "album_count": len(albums),
            "vague_explanations": vague_count,
            "generic_genres": generic_count,
            "unique_artists": unique_artists
        }

    def get_feedback_prompt(self, albums: list[AlbumData], evaluation: dict[str, Any]) -> str:
        """Generate a feedback prompt to improve recommendations."""
        if evaluation["passed"]:
            return ""

        feedback = "Your previous recommendations had the following issues:\n\n"

        for issue in evaluation["issues"]:
            feedback += f"- {issue}\n"

        feedback += "\nPlease regenerate with these improvements:\n"

        if evaluation.get("vague_explanations", 0) > 0:
            feedback += "- Provide more specific explanations with concrete musical details (production techniques, instrumentation, specific sonic qualities)\n"

        if evaluation.get("generic_genres", 0) > 0:
            feedback += "- Use more specific genre descriptions (e.g., 'city pop' instead of 'pop', 'deep house' instead of 'electronic')\n"

        if "translated" in str(evaluation["issues"]):
            feedback += "- Keep original language titles for non-English albums\n"

        feedback += "\nReturn the improved recommendations in the same XML format."

        return feedback


evaluator = AlbumEvaluator()
