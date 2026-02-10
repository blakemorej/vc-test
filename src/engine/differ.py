"""
Content differ for comparing raw and rendered page content.

Compares extracted content to identify differences between JS-disabled and JS-enabled versions.
"""

from .models import DifferenceReport, ExtractedContent


class ContentDiffer:
    """
    Compares content between two versions of a page.

    Identifies content that appears in one version but not the other,
    focusing on meaningful differences rather than raw HTML variations.
    """

    def __init__(self, text_block_size: int = 50) -> None:
        """
        Initialize the content differ.

        Args:
            text_block_size: Minimum number of words to group text differences into blocks
        """
        self.text_block_size = text_block_size

    def compare(self, raw: ExtractedContent, rendered: ExtractedContent) -> DifferenceReport:
        """
        Compare raw and rendered content.

        Args:
            raw: Content extracted from non-JS version
            rendered: Content extracted from JS-enabled version

        Returns:
            DifferenceReport with categorized differences
        """
        # Compare text content
        text_only_with_js, text_only_without_js = self._compare_text(
            raw.visible_text, rendered.visible_text
        )

        # Compare headings
        (
            headings_missing_without_js,
            headings_extra_without_js,
        ) = self._compare_headings(raw.headings, rendered.headings)

        # Compare internal links
        (
            internal_links_missing_without_js,
            internal_links_extra_without_js,
        ) = self._compare_internal_links(raw.internal_links, rendered.internal_links)

        # Create difference report
        return DifferenceReport(
            text_only_with_js=text_only_with_js,
            text_only_without_js=text_only_without_js,
            headings_missing_without_js=headings_missing_without_js,
            headings_extra_without_js=headings_extra_without_js,
            internal_links_missing_without_js=internal_links_missing_without_js,
            internal_links_extra_without_js=internal_links_extra_without_js,
            raw_word_count=raw.word_count,
            rendered_word_count=rendered.word_count,
            raw_heading_count=raw.heading_count,
            rendered_heading_count=rendered.heading_count,
            raw_internal_link_count=raw.internal_link_count,
            rendered_internal_link_count=rendered.internal_link_count,
        )

    def _compare_text(self, raw_text: str, rendered_text: str) -> tuple[list[str], list[str]]:
        """
        Compare visible text between versions.

        Uses word-level comparison and groups differences into readable blocks.

        Args:
            raw_text: Text from non-JS version
            rendered_text: Text from JS-enabled version

        Returns:
            Tuple of (text_only_with_js, text_only_without_js) - lists of text blocks
        """
        # Split text into words for comparison
        raw_words: set[str] = set(raw_text.lower().split())
        rendered_words: set[str] = set(rendered_text.lower().split())

        # Find words unique to each version
        words_only_with_js = rendered_words - raw_words
        words_only_without_js = raw_words - rendered_words

        # Group unique words into text blocks from original text
        text_only_with_js = self._group_words_into_blocks(rendered_text, words_only_with_js)
        text_only_without_js = self._group_words_into_blocks(raw_text, words_only_without_js)

        return text_only_with_js, text_only_without_js

    def _group_words_into_blocks(self, text: str, unique_words: set[str]) -> list[str]:
        """
        Group unique words into readable text blocks from original text.

        Finds contiguous sequences in the original text that contain
        multiple unique words, avoiding noisy micro-differences.

        Args:
            text: Original text
            unique_words: Set of words that are unique to this version

        Returns:
            List of text blocks containing unique content
        """
        if not unique_words:
            return []

        words = text.split()
        blocks: list[str] = []
        current_block: list[str] = []
        unique_count = 0

        for word in words:
            word_lower = word.lower()
            if word_lower in unique_words:
                current_block.append(word)
                unique_count += 1
            else:
                # End current block if we have enough unique words
                if unique_count >= 3:  # Minimum threshold for a meaningful block
                    blocks.append(" ".join(current_block))
                current_block = []
                unique_count = 0

        # Don't forget the last block
        if unique_count >= 3:
            blocks.append(" ".join(current_block))

        return blocks

    def _compare_headings(
        self, raw_headings: list[str], rendered_headings: list[str]
    ) -> tuple[list[str], list[str]]:
        """
        Compare headings between versions.

        Args:
            raw_headings: Headings from non-JS version
            rendered_headings: Headings from JS-enabled version

        Returns:
            Tuple of (headings_missing_without_js, headings_extra_without_js)
        """
        raw_set = set(raw_headings)
        rendered_set = set(rendered_headings)

        # Headings in rendered but not in raw (missing without JS)
        headings_missing_without_js = sorted(
            list(rendered_set - raw_set), key=lambda x: rendered_headings.index(x)
        )

        # Headings in raw but not in rendered (extra without JS)
        headings_extra_without_js = sorted(
            list(raw_set - rendered_set), key=lambda x: raw_headings.index(x)
        )

        return headings_missing_without_js, headings_extra_without_js

    def _compare_internal_links(
        self, raw_links: list[dict[str, str]], rendered_links: list[dict[str, str]]
    ) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
        """
        Compare internal links between versions.

        Links are considered the same if they have the same href and anchor text.

        Args:
            raw_links: Links from non-JS version
            rendered_links: Links from JS-enabled version

        Returns:
            Tuple of (links_missing_without_js, links_extra_without_js)
        """
        # Create sets for comparison (using tuple for hashability)
        raw_set = {(link["href"], link["anchor_text"]) for link in raw_links}
        rendered_set = {(link["href"], link["anchor_text"]) for link in rendered_links}

        # Links in rendered but not in raw (missing without JS)
        missing_tuples = rendered_set - raw_set
        links_missing_without_js = [
            {"href": href, "anchor_text": text} for href, text in missing_tuples
        ]

        # Links in raw but not in rendered (extra without JS)
        extra_tuples = raw_set - rendered_set
        links_extra_without_js = [
            {"href": href, "anchor_text": text} for href, text in extra_tuples
        ]

        return links_missing_without_js, links_extra_without_js
