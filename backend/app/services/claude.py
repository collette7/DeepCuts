import os
import uuid
import anthropic
from typing import List, Optional
import re
import xml.etree.ElementTree as ET
from app.models.albums import AlbumData

class ClaudeService:
    def __init__(self):
        self.client = anthropic.Anthropic(
            api_key=os.getenv("CLAUDE_API_KEY")
        )
        
    def get_recommendation_prompt(self, album_name: str) -> str:
        """Promp template."""
        return f"""You are an expert music recommender with extensive knowledge of albums across various genres, styles, and time periods.
        Your task is to recommend albums similar to a given input album, focusing on deeper cuts, overlooked records, or side projects by related producers.

        Here is the album you should base your recommendations on:

        <input_album>
        {album_name}
        </input_album>

        Please follow these steps to generate your recommendations:

        1. Analyze the input album:
        In <album_analysis> tags, break down the input album's characteristics. Consider:
        - Overall mood and atmosphere
        - Production style and sound quality
        - Album structure and flow
        - Track lengths
        - Instrumentation
        - Mix style
        - Any genre fusions or unique elements
        - Regional influences (especially important for house music and its subgenres)

        For each element, rate its importance to the album's sound on a scale of 1-10, with 10 being extremely important. Provide specific examples from the input album for each characteristic. Be specific about electronic music genres, avoiding overgeneralization. For house music, particularly styles like South African house, emphasize its energizing qualities.

        List out each characteristic with its importance rating and example, numbering them for clarity. It's OK for this section to be quite long.

        2. Search for similar albums:
        In <recommendation_search> tags, document your process of finding and scoring similar albums:

        a) Create a scoring rubric based on your analysis, assigning point values to each characteristic based on its importance.

        b) For each potential recommendation:
        - Apply the scoring rubric, explaining your reasoning for each point awarded
        - Calculate a total "similarity score" based on how well it matches the important elements from your analysis
        - Prioritize albums with comparable musical qualities, deeper cuts, overlooked records, side projects by related producers, and albums that a fan of the given album would likely obsess over
        - Explicitly check that recommended albums are not just similarly named but musically similar to the input album

        c) List at least 15 potential recommendations with their similarity scores and point breakdowns

        3. Generate and format recommendations:
        Present the top 10 album recommendations based on your similarity scoring. Use the following format for each recommendation:

        <recommendations>
        <album>
            <title>Album Name</title>
            <artist>Artist Name</artist>
            <year>Year</year>
            <explanation>Your explanation here, 2-3 sentences focusing on specific musical qualities and characteristics</explanation>
        </album>
        <!-- Repeat for all 10 recommendations -->
        </recommendations>

        Ensure that your recommendations are diverse while still maintaining a strong connection to the original album's qualities. Focus on albums that share musical similarities rather than just belonging to the same genre. Look for hidden gems and lesser-known releases that true fans of the given album would appreciate."""

    def parse_recommendations(self, response_text: str) -> List[AlbumData]:
        """Parse the XML"""
        recommendations = []
        
        recommendations_match = re.search(r'<recommendations>(.*?)</recommendations>', response_text, re.DOTALL)
        if not recommendations_match:
            return recommendations
            
        recommendations_xml = recommendations_match.group(1)
        
        # Parse each album rec
        album_pattern = r'<album>\s*<title>(.*?)</title>\s*<artist>(.*?)</artist>\s*<year>(.*?)</year>\s*<explanation>(.*?)</explanation>\s*</album>'
        album_matches = re.findall(album_pattern, recommendations_xml, re.DOTALL)
        
        for title, artist, year, explanation in album_matches:
            try:
                # Clean up 
                title = title.strip()
                artist = artist.strip()
                year_str = year.strip()
                explanation = explanation.strip()
                
                # Parse year
                try:
                    parsed_year = int(year_str) if year_str.isdigit() else None
                except ValueError:
                    parsed_year = None
                
                album = AlbumData(
                    id=str(uuid.uuid4()),
                    title=title,
                    artist=artist,
                    year=parsed_year,
                    genre="genre",  
                    spotify_preview_url=None,
                    spotify_url=None,
                    discogs_url=None,
                    cover_url=None,
                    reasoning=explanation
                )
                recommendations.append(album)
                
            except Exception as e:
                import logging
                logger = logging.getLogger('deepcuts')
                logger.error(f"Error parsing album: {e}")
                continue
                
        return recommendations

    async def get_album_recommendations(self, album_name: str) -> List[AlbumData]:
        """Get album recommendations from Claude"""
        try:
            prompt = self.get_recommendation_prompt(album_name)
            
            message = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=4000,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )
            
            response_text = message.content[0].text
            recommendations = self.parse_recommendations(response_text)
            
            return recommendations
            
        except Exception as e:
            # Import logger here to avoid circular imports
            import logging
            logger = logging.getLogger('deepcuts')
            logger.error(f"Error getting recommendations from Claude: {e}", exc_info=True)
            return []


claude_service = ClaudeService()