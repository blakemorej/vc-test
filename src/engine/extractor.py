"""
Content extractor for parsing HTML into structured data.

Extracts meaningful content while ignoring scripts, styles, and other non-content elements.
"""

import re
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup, Comment
from bs4.element import Tag

from .models import ExtractedContent


class ContentExtractor:
    """
    Extracts structured content from HTML.

    Focuses on visible, SEO-relevant content while ignoring
    scripts, styles, tracking pixels, and other noise.
    """

    # Tags to completely ignore
    IGNORED_TAGS = {
        "script",
        "style",
        "noscript",
        "iframe",
        "svg",
        "path",
        "circle",
        "rect",
        "polygon",
        "line",
        "ellipse",
        "defs",
        "use",
        "g",
        "symbol",
        "marker",
        "pattern",
        "filter",
        "mask",
        "clippath",
        "textpath",
    }

    # Heading tags to extract
    HEADING_TAGS = ["h1", "h2", "h3", "h4", "h5", "h6"]

    # Selectors for cookie banners (best-effort identification)
    COOKIE_BANNER_SELECTORS = [
        "[id*='cookie']",
        "[class*='cookie']",
        "[id*='consent']",
        "[class*='consent']",
        "[id*='gdpr']",
        "[class*='gdpr']",
        "[role='dialog'][id*='cookie']",
    ]

    def __init__(self, base_url: str | None = None):
        """
        Initialize the content extractor.

        Args:
            base_url: Base URL for resolving relative links (optional)
        """
        self.base_url = base_url

    def extract(self, html: str) -> ExtractedContent:
        """
        Extract structured content from HTML.

        Args:
            html: HTML string to parse

        Returns:
            ExtractedContent containing structured content
        """
        soup = BeautifulSoup(html, "lxml")

        # Remove ignored elements
        self._remove_ignored_elements(soup)

        # Extract visible text
        visible_text = self._extract_visible_text(soup)

        # Extract headings
        headings = self._extract_headings(soup)

        # Extract internal links
        internal_links = self._extract_internal_links(soup)

        return ExtractedContent(
            visible_text=visible_text,
            headings=headings,
            internal_links=internal_links,
        )

    def _remove_ignored_elements(self, soup: BeautifulSoup):
        """
        Remove elements that should not be considered as content.

        Args:
            soup: BeautifulSoup object
        """
        # Remove script and style tags
        for tag in soup.find_all(self.IGNORED_TAGS):
            tag.decompose()

        # Remove HTML comments
        for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
            comment.extract()

        # Remove cookie banners (best-effort)
        for selector in self.COOKIE_BANNER_SELECTORS:
            for element in soup.select(selector):
                # Check if the element is likely a cookie banner
                element_text = element.get_text().lower()
                if any(
                    word in element_text
                    for word in ["cookie", "consent", "privacy", "accept", "reject"]
                ):
                    element.decompose()

    def _extract_visible_text(self, soup: BeautifulSoup) -> str:
        """
        Extract and normalize visible text from the page.

        Args:
            soup: BeautifulSoup object

        Returns:
            Normalized visible text string
        """
        # Get all text, excluding hidden elements
        text_parts = []

        for element in soup.find_all(string=True):
            parent = element.parent
            if parent and self._is_element_visible(parent):
                text_parts.append(str(element))

        # Join and normalize whitespace
        full_text = " ".join(text_parts)
        normalized = self._normalize_whitespace(full_text)

        return normalized.strip()

    def _is_element_visible(self, element: Tag) -> bool:
        """
        Check if an element is likely visible.

        Args:
            element: BeautifulSoup Tag element

        Returns:
            True if element appears visible
        """
        # Check for common hidden patterns
        if not isinstance(element, Tag):
            return True

        style = element.get("style", "").lower()
        class_attr = " ".join(element.get("class", [])).lower()
        aria_hidden = element.get("aria-hidden", "").lower()

        # Elements marked as hidden
        if (
            "display:none" in style
            or "visibility:hidden" in style
            or "hidden" in class_attr
            or aria_hidden == "true"
        ):
            return False

        # Check parent visibility recursively
        parent = element.parent
        if parent and parent.name:
            return self._is_element_visible(parent)

        return True

    def _normalize_whitespace(self, text: str) -> str:
        """
        Normalize whitespace in text.

        Args:
            text: Input text

        Returns:
            Text with normalized whitespace
        """
        # Replace multiple whitespace characters with single space
        text = re.sub(r"\s+", " ", text)
        # Remove leading/trailing whitespace from lines
        text = re.sub(r"^\s+|\s+$", "", text, flags=re.MULTILINE)
        return text

    def _extract_headings(self, soup: BeautifulSoup) -> list[str]:
        """
        Extract all headings (H1-H6) in document order.

        Args:
            soup: BeautifulSoup object

        Returns:
            List of heading texts
        """
        headings: list[str] = []

        for heading_tag in self.HEADING_TAGS:
            for element in soup.find_all(heading_tag):
                text = element.get_text(strip=True)
                if text:
                    headings.append(text)

        return headings

    def _extract_internal_links(self, soup: BeautifulSoup) -> list[dict[str, str]]:
        """
        Extract internal links from the page.

        Args:
            soup: BeautifulSoup object

        Returns:
            List of dictionaries with 'href' and 'anchor_text' keys
        """
        links: list[dict[str, str]] = []

        for link in soup.find_all("a", href=True):
            href = link["href"].strip()
            anchor_text = link.get_text(strip=True)

            # Skip empty links or links without anchor text
            if not href or not anchor_text:
                continue

            # Skip JavaScript and mailto links
            if href.startswith(("javascript:", "mailto:", "tel:", "#")):
                continue

            # Resolve relative URLs if base_url is provided
            if self.base_url:
                href = urljoin(self.base_url, href)

            # Check if it's an internal link
            if self._is_internal_link(href):
                links.append({"href": href, "anchor_text": anchor_text})

        return links

    def _is_internal_link(self, href: str) -> bool:
        """
        Check if a link is internal (points to the same domain).

        Args:
            href: URL to check

        Returns:
            True if the link is internal
        """
        if not self.base_url:
            # If no base_url, consider all links as internal
            return True

        try:
            base_parsed = urlparse(self.base_url)
            link_parsed = urlparse(href)

            # Check if domains match (subdomains considered internal)
            base_domain = base_parsed.netloc.replace("www.", "")
            link_domain = link_parsed.netloc.replace("www.", "")

            return base_domain == link_domain

        except Exception:
            # If parsing fails, consider as internal
            return True
