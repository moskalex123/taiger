"""
Text formatting utilities for converting between different text formats.

This module provides utilities for converting Markdown-style formatting to
Telegram HTML tags and other text transformations.
"""

import re
from typing import Optional


class TextFormatter:
    """
    Utility class for text formatting operations.
    """

    @staticmethod
    def markdown_to_telegram_html(text: str) -> str:
        """
        Convert Markdown-style formatting to Telegram HTML tags.

        Supports:
        - **text** → <b>text</b> (bold)
        - *text* → <i>text</i> (italic)
        - __text__ → <u>text</u> (underline)
        - ~~text~~ → <s>text</s> (strikethrough)
        - `text` → <code>text</code> (inline code)
        - ```text``` → <pre>text</pre> (code block)

        Args:
            text: Input text with Markdown-style formatting

        Returns:
            Text with Telegram HTML tags
        """
        if not text:
            return text

        # Escape HTML entities first to prevent double-encoding
        text = text.replace("&", "&").replace("<", "<").replace(">", ">")

        # Convert Markdown to HTML tags
        text = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", text, flags=re.S)  # Bold
        text = re.sub(r"\*([^\*\n]+?)\*", r"<i>\1</i>", text)  # Italic (single *)
        text = re.sub(r"__(.*?)__", r"<u>\1</u>", text, flags=re.S)  # Underline
        text = re.sub(r"~~(.*?)~~", r"<s>\1</s>", text, flags=re.S)  # Strikethrough
        text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)  # Inline code
        text = re.sub(r"```([\s\S]*?)```", r"<pre>\1</pre>", text)  # Code block

        return text

    @staticmethod
    def clean_html_for_telegram(text: str) -> str:
        """
        Clean and prepare HTML text for safe display in Telegram.

        This function ensures HTML is properly escaped and formatted
        for Telegram's HTML parsing.

        Args:
            text: Input text that may contain HTML

        Returns:
            Cleaned text safe for Telegram HTML display
        """
        if not text:
            return text

        # Basic HTML escaping (in case it wasn't done already)
        text = text.replace("&", "&").replace("<", "<").replace(">", ">")

        # Convert back common HTML entities that should be displayed
        # (This is optional - depends on use case)
        text = text.replace("<b>", "<b>").replace("</b>", "</b>")
        text = text.replace("<i>", "<i>").replace("</i>", "</i>")
        text = text.replace("<u>", "<u>").replace("</u>", "</u>")
        text = text.replace("<s>", "<s>").replace("</s>", "</s>")
        text = text.replace("<code>", "<code>").replace("</code>", "</code>")
        text = text.replace("<pre>", "<pre>").replace("</pre>", "</pre>")

        return text

    @staticmethod
    def truncate_text(text: str, max_length: int, suffix: str = "...") -> str:
        """
        Truncate text to a maximum length with optional suffix.

        Args:
            text: Input text
            max_length: Maximum allowed length
            suffix: Suffix to add if text is truncated

        Returns:
            Truncated text
        """
        if not text or len(text) <= max_length:
            return text

        return text[:max_length - len(suffix)] + suffix


# Convenience function for backward compatibility
def markdown_to_telegram_html(text: str) -> str:
    """
    Convenience function for converting Markdown to Telegram HTML.

    Args:
        text: Input text with Markdown formatting

    Returns:
        Text with Telegram HTML tags
    """
    return TextFormatter.markdown_to_telegram_html(text)