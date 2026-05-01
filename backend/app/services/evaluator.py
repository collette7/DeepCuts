import logging
from typing import Any

from app.models.albums import AlbumData

logger = logging.getLogger('deepcuts')

# Expanded list of generic genres that should be penalized
GENERIC_GENRES = {
    'pop', 'rock', 'jazz', 'electronic', 'hip hop', 'r&b',
    'indie', 'alternative', 'folk', 'metal', 'dance',
    'soul', 'funk', 'ambient', 'experimental', 'country',
    'blues', 'classical', 'reggae', 'punk', 'disco',
    'techno', 'house', 'trap', 'drum and bass', 'dubstep',
    'trance', 'garage', 'grime', 'new wave', 'world',
}

# Words that indicate vague explanations
VAGUE_WORDS = {'similar', 'like', 'same', 'vibe', 'feels like'}


class AlbumEvaluator:
    """Evaluate AI-generated album recommendations for quality issues."""

    def __init__(self):
        self.issues: list[str] = []
        self.album_issues: list[dict[str, Any]] = []

    def evaluate(
        self,
        albums: list[AlbumData],
        original_query: str,
        verified_map: dict[str, bool] | None = None
    ) -> dict[str, Any]:
        """Evaluate a list of album recommendations.

        Args:
            albums: List of recommended albums
            original_query: The user's search query
            verified_map: Optional dict mapping album_key -> bool indicating
                         whether each album passed external verification
                         (Discogs/Spotify existence check)

        Returns:
            dict with score (0-100), issues found, and per-album feedback
        """
        self.issues = []
        self.album_issues = []

        if not albums or len(albums) == 0:
            self.issues.append("No albums returned")
            return {
                "score": 0,
                "issues": self.issues,
                "album_issues": [],
                "passed": False
            }

        score = 100
        vague_count = 0
        generic_count = 0
        unverified_count = 0

        # Per-album checks
        for album in albums:
            album_key = f"{album.title} by {album.artist}"
            album_problems = []

            # Check 1: External verification (highest priority)
            if verified_map is not None:
                is_verified = verified_map.get(album_key, False)
                if not is_verified:
                    album_problems.append("FAILED existence verification — may be fabricated")
                    unverified_count += 1

            # Check 2: Vague explanation
            if not album.reasoning or len(album.reasoning) < 50:
                album_problems.append("Explanation is too short (< 50 chars)")
                vague_count += 1
            elif any(word in album.reasoning.lower() for word in VAGUE_WORDS):
                # No length escape — banned words always penalize
                album_problems.append(
                    f"Explanation uses vague words ({', '.join(w for w in VAGUE_WORDS if w in album.reasoning.lower())})"
                )
                vague_count += 1

            # Check 3: Generic genre
            if album.genre and album.genre.lower().strip() in GENERIC_GENRES:
                album_problems.append(
                    f"Genre '{album.genre}' is too generic — use a specific subgenre"
                )
                generic_count += 1

            if album_problems:
                self.album_issues.append({
                    "album": album_key,
                    "problems": album_problems
                })

        # Global checks

        # Check 4: Album count
        if len(albums) < 10:
            self.issues.append(f"Only {len(albums)} albums returned (expected 10)")
            score -= (10 - len(albums)) * 5

        # Check 5: Heavy penalty for unverified albums
        if unverified_count > 0:
            self.issues.append(
                f"{unverified_count} album(s) failed external existence verification"
            )
            score -= unverified_count * 15

        # Check 6: Vague explanations
        if vague_count > 0:
            self.issues.append(f"{vague_count} albums have vague or short explanations")
            score -= vague_count * 3

        # Check 7: Generic genres
        if generic_count > 3:
            self.issues.append(f"{generic_count} albums have overly generic genres")
            score -= generic_count * 2

        # Check 8: Artist diversity
        artists = [a.artist for a in albums]
        unique_artists = len(set(artists))
        if unique_artists < len(albums) * 0.7:
            self.issues.append(
                f"Low artist diversity: {unique_artists} unique artists for {len(albums)} albums"
            )
            score -= 10

        # Check 9: Year range (conditional — only penalize for established genres)
        years = [a.year for a in albums if a.year]
        if years and len(years) >= 5:
            year_range = max(years) - min(years)
            # Only penalize if range is very narrow AND we have enough data
            if year_range < 3:
                self.issues.append(f"Very narrow year range: only {year_range} years covered")
                score -= 3

        score = max(0, min(100, score))

        return {
            "score": score,
            "issues": self.issues,
            "album_issues": self.album_issues,
            "passed": score >= 70,
            "album_count": len(albums),
            "vague_explanations": vague_count,
            "generic_genres": generic_count,
            "unverified_count": unverified_count,
            "unique_artists": unique_artists
        }

    def get_feedback_prompt(
        self,
        albums: list[AlbumData],
        evaluation: dict[str, Any]
    ) -> str:
        """Generate a feedback prompt with per-album specifics."""
        if evaluation["passed"]:
            return ""

        feedback = "Your previous recommendations had the following issues:\n\n"

        # Global issues
        for issue in evaluation["issues"]:
            feedback += f"- {issue}\n"

        # Per-album issues (most actionable)
        if evaluation.get("album_issues"):
            feedback += "\nSpecific albums that need fixes:\n"
            for item in evaluation["album_issues"]:
                feedback += f"\n{item['album']}:\n"
                for problem in item["problems"]:
                    feedback += f"  • {problem}\n"

        feedback += "\nPlease regenerate with these improvements:\n"

        if evaluation.get("unverified_count", 0) > 0:
            feedback += (
                "- CRITICAL: Every album MUST be a real, released record. "
                "If you are uncertain about any pick, replace it with an older, "
                "well-documented release you are certain about. "
                "Fabricated albums destroy user trust.\n"
            )

        if evaluation.get("vague_explanations", 0) > 0:
            feedback += (
                "- Replace vague descriptions with concrete musical details: "
                "name specific instruments, production techniques, BPM ranges, "
                "rhythmic patterns, or arrangement choices. "
                "Never use 'similar', 'like', 'same', 'vibe', or 'feels like'.\n"
            )

        if evaluation.get("generic_genres", 0) > 0:
            feedback += (
                "- Use specific subgenres: 'amapiano' not 'electronic', "
                "'spiritual jazz' not 'jazz', 'shoegaze' not 'rock', "
                "'deep house' not 'house', 'UK bass' not 'dance'.\n"
            )

        if any("translated" in str(i) for i in evaluation["issues"]):
            feedback += "- Keep original language titles for non-English albums\n"

        feedback += "\nReturn the improved recommendations in the same XML format."

        return feedback


evaluator = AlbumEvaluator()
