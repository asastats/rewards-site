"""This module provides a class for parsing social media messages."""

import re

from utils.constants.core import REWARDS_COLLECTION


class MessageParser:
    """A parser for social media messages to extract type, level, and title."""

    def __init__(self):
        """Initialize the MessageParser."""
        self.alias_to_code_map, self.sorted_aliases = self._build_alias_maps()

    def _build_alias_maps(self):
        """Build alias maps from the rewards collection.

        :return: A tuple containing the alias-to-code map and sorted aliases.
        :rtype: tuple
        """
        alias_map = {}
        for entry in REWARDS_COLLECTION:
            parts = entry[0].split("]")
            code = parts[0].strip("[]")
            full_name = parts[1].strip().lower()

            alias_map[full_name] = code
            for word in full_name.split():
                alias_map[word] = code
            alias_map[code.lower()] = code

        sorted_aliases = sorted(alias_map.keys(), key=len, reverse=True)
        return alias_map, sorted_aliases

    def _clean_message(self, message, arg):
        """Remove argument and extra whitespace from the message.

        :param message: The original message string.
        :type message: str
        :param arg: The argument to remove from the message.
        :type arg: str
        :return: The cleaned message.
        :rtype: str
        """
        work_message = message.replace(arg, "").strip()
        return " ".join(work_message.split())

    def _full_type_from_parsed_type(self, parsed_type):
        """Return full request type from provided parsed type/code.

        :param parsed_type: request type code
        :type parsed_type: str
        :rtype: str
        """
        return next(
            entry[0] for entry in REWARDS_COLLECTION if f"[{parsed_type}]" in entry[0]
        )

    def _parse_combined_type_level(self, message):
        """Parse combined type and level from the message (e.g., F1, CT2).

        :param message: The message string to parse.
        :type message: str
        :return: A tuple containing the parsed type, level, and the remaining message.
        :rtype: tuple
        """
        type_words = [alias for alias in self.sorted_aliases if " " not in alias]
        type_pattern = "|".join(re.escape(word) for word in type_words)
        match = re.search(rf"\b({type_pattern})([1-3])\b", message, re.IGNORECASE)
        if match:
            type_alias = match.group(1).lower()
            parsed_type = self.alias_to_code_map.get(type_alias)
            level = int(match.group(2))
            remaining_message = message.replace(match.group(0), "", 1).strip()
            return parsed_type, level, remaining_message

        return None, None, message

    def _parse_explicit_level(self, message):
        """Parse explicit level from the message (e.g., level:1, l2).

        :param message: The message string to parse.
        :type message: str
        :return: A tuple containing the parsed level and the remaining message.
        :rtype: tuple
        """
        level_match = re.search(
            r"\b(level|l)\s*[:\s]?\s*([1-3])\b", message, re.IGNORECASE
        )
        if level_match:
            level = int(level_match.group(2))
            remaining_message = message.replace(level_match.group(0), "", 1).strip()
            return level, remaining_message

        return None, message

    def _parse_explicit_type(self, message):
        """Parse explicit type from the message.

        :param message: The message string to parse.
        :type message: str
        :return: A tuple containing the parsed type and the remaining message.
        :rtype: tuple
        """
        for alias in self.sorted_aliases:
            type_match = re.search(rf"\b{re.escape(alias)}\b", message, re.IGNORECASE)
            if type_match:
                parsed_type = self.alias_to_code_map[alias]
                remaining_message = message.replace(type_match.group(0), "", 1).strip()
                return parsed_type, remaining_message

        return None, message

    def _parse_title(self, message):
        """Parse the title from the message.

        :param message: The message string to parse.
        :type message: str
        :return: The parsed title.
        :rtype: str
        """
        title_match = re.search(
            r"\b(title|subject|s)\s*:\s*(.+)", message, re.IGNORECASE
        )
        if title_match:
            title = title_match.group(2).strip()

        else:
            title = message.strip()

        return " ".join(title.split())

    def parse(self, message, arg):
        """Parse a social media message to extract type, level, and title.

        :param message: The message string to parse.
        :type message: str
        :param arg: The argument to remove from the message (e.g., a username).
        :type arg: str
        :return: A dictionary containing the parsed type, level, and title.
        :rtype: dict
        """
        result = {"type": None, "level": 1, "comment": ""}

        work_message = self._clean_message(message, arg)

        parsed_type, level, work_message = self._parse_combined_type_level(work_message)
        if parsed_type:
            result["type"] = self._full_type_from_parsed_type(parsed_type)
            result["level"] = level

        explicit_level, work_message = self._parse_explicit_level(work_message)
        if explicit_level:
            result["level"] = explicit_level

        if not result["type"]:
            explicit_type, work_message = self._parse_explicit_type(work_message)
            if explicit_type:
                result["type"] = self._full_type_from_parsed_type(explicit_type)

        result["comment"] = self._parse_title(work_message)

        if result["type"] is None:
            result["type"] = "[F] Feature Request"

        return result
