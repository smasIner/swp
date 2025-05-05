import re
from typing import Set

class SimilarityChecker:
    @staticmethod
    def check_content_similarity(original: str, comparison: str, threshold: float = 0.5) -> bool:
        """Compare semantic similarity between texts."""
        def process_text(text: str) -> Set[str]:
            if not text:
                return set()
            text = text.lower()
            text = re.sub(r'[^\w\s]', '', text)
            return set(text.split())

        original_words = process_text(original)
        comparison_words = process_text(comparison)

        if not original_words:
            return True

        common_words = original_words & comparison_words
        similarity_score = len(common_words) / len(original_words)

        return similarity_score >= threshold