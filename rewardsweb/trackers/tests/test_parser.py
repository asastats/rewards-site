"""Testing module for :py:mod:`trackers.parser` module."""

import pytest

from trackers.parser import MessageParser


class TestTrackersParser:
    """Testing class for :py:mod:`trackers.parser`. functions"""

    @pytest.fixture
    def parser(self):
        """Return a MessageParser instance."""
        return MessageParser()

    @pytest.mark.parametrize(
        "code,typ",
        [
            ("F", "[F] Feature Request"),
            ("B", "[B] Bug Report"),
            ("AT", "[AT] Admin Task"),
            ("CT", "[CT] Content Task"),
            ("IC", "[IC] Issue Creation"),
            ("TWR", "[TWR] Twitter Post"),
            ("D", "[D] Development"),
            ("ER", "[ER] Ecosystem Research"),
        ],
    )
    def test_trackers_parser_full_type_from_parsed_type(self, parser, code, typ):
        """Test the _clean_message method."""
        assert parser._full_type_from_parsed_type(code) == typ

    @pytest.mark.parametrize(
        "message, arg, expected",
        [
            ("  @myhandle  message  ", "@myhandle", "message"),
            ("message with no arg", "@myhandle", "message with no arg"),
            ("  multiple   spaces  ", "arg", "multiple spaces"),
        ],
    )
    def test_trackers_parser_clean_message(self, parser, message, arg, expected):
        """Test the _clean_message method."""
        assert parser._clean_message(message, arg) == expected

    @pytest.mark.parametrize(
        "message, expected_type, expected_level, expected_remaining",
        [
            ("F1 title", "F", 1, "title"),
            ("CT2 another title", "CT", 2, "another title"),
            ("bug3 yet another", "B", 3, "yet another"),
            ("no type level", None, None, "no type level"),
        ],
    )
    def test_trackers_parser_parse_combined_type_level(
        self, parser, message, expected_type, expected_level, expected_remaining
    ):
        """Test the _parse_combined_type_level method."""
        parsed_type, level, remaining_message = parser._parse_combined_type_level(
            message
        )
        assert parsed_type == expected_type
        assert level == expected_level
        assert remaining_message == expected_remaining

    @pytest.mark.parametrize(
        "message, expected_level, expected_remaining",
        [
            ("level:1 title", 1, "title"),
            ("l2 another title", 2, "another title"),
            ("level 3 yet another", 3, "yet another"),
            ("no level", None, "no level"),
        ],
    )
    def test_trackers_parser_parse_explicit_level(
        self, parser, message, expected_level, expected_remaining
    ):
        """Test the _parse_explicit_level method."""
        level, remaining_message = parser._parse_explicit_level(message)
        assert level == expected_level
        assert remaining_message == expected_remaining

    @pytest.mark.parametrize(
        "message, expected_type, expected_remaining",
        [
            ("Feature Request title", "F", "title"),
            ("bug another title", "B", "another title"),
            ("CT yet another", "CT", "yet another"),
            ("no type", None, "no type"),
        ],
    )
    def test_trackers_parser_parse_explicit_type(
        self, parser, message, expected_type, expected_remaining
    ):
        """Test the _parse_explicit_type method."""
        parsed_type, remaining_message = parser._parse_explicit_type(message)
        assert parsed_type == expected_type
        assert remaining_message == expected_remaining

    @pytest.mark.parametrize(
        "message, expected_title",
        [
            ("title: this is a title", "this is a title"),
            ("subject: another title", "another title"),
            ("s: yet another", "yet another"),
            ("this is an implicit title", "this is an implicit title"),
        ],
    )
    def test_trackers_parser_parse_title(self, parser, message, expected_title):
        """Test the _parse_title method."""
        assert parser._parse_title(message) == expected_title

    @pytest.mark.parametrize(
        "message,arg,result",
        [
            (
                "@myhandle type:Feature level:1 title:This is something I want you to know about",
                "@myhandle",
                {
                    "type": "[F] Feature Request",
                    "level": 1,
                    "comment": "This is something I want you to know about",
                },
            ),
            (
                "type:Feature Request @myhandle level:1 title:This is something I want you to know about",
                "@myhandle",
                {
                    "type": "[F] Feature Request",
                    "level": 1,
                    "comment": "This is something I want you to know about",
                },
            ),
            (
                "type:Feature Request level:1 title:This is something I want you to know about @myhandle",
                "@myhandle",
                {
                    "type": "[F] Feature Request",
                    "level": 1,
                    "comment": "This is something I want you to know about",
                },
            ),
            (
                "type:Feature Request level:1 title:This is something I want you to know about @myhandle",
                "@myhandle",
                {
                    "type": "[F] Feature Request",
                    "level": 1,
                    "comment": "This is something I want you to know about",
                },
            ),
            (
                "Feature1 This is something I want you to know about u/handle",
                "u/handle",
                {
                    "type": "[F] Feature Request",
                    "level": 1,
                    "comment": "This is something I want you to know about",
                },
            ),
            (
                "This is something I want you to know about u/handle F1",
                "u/handle",
                {
                    "type": "[F] Feature Request",
                    "level": 1,
                    "comment": "This is something I want you to know about",
                },
            ),
            (
                "This is something u/handle F",
                "u/handle",
                {
                    "type": "[F] Feature Request",
                    "level": 1,  # notice default of 1
                    "comment": "This is something",
                },
            ),
            (
                "Request l2 subject:This is something I want you to know about @myhandle",
                "@myhandle",
                {
                    "type": "[F] Feature Request",
                    "level": 2,
                    "comment": "This is something I want you to know about",
                },
            ),
            (
                "This is something u/handle bug",
                "u/handle",
                {
                    "type": "[B] Bug Report",
                    "level": 1,
                    "comment": "This is something",
                },
            ),
            (
                "t:F l:2 subject:This is something I want you to know about @myhandle",
                "@myhandle",
                {
                    "type": "[F] Feature Request",
                    "level": 2,
                    "comment": "This is something I want you to know about",
                },
            ),
            (
                "t:F l:2 s:This is something I want you to know about @myhandle",
                "@myhandle",
                {
                    "type": "[F] Feature Request",
                    "level": 2,
                    "comment": "This is something I want you to know about",
                },
            ),
            (
                "CT2 This is also @myhandle",
                "@myhandle",
                {
                    "type": "[CT] Content Task",
                    "level": 2,
                    "comment": "This is also",
                },
            ),
            (
                "This is a research @myhandle research",
                "@myhandle",
                {
                    "type": "[ER] Ecosystem Research",
                    "level": 1,
                    "comment": "This is a research",
                },
            ),
            (
                "@myhandle Hello there",
                "@myhandle",
                {
                    "type": "[F] Feature Request",
                    "level": 1,
                    "comment": "Hello there",
                },
            ),
            (
                "Just a title @myhandle",
                "@myhandle",
                {
                    "type": "[F] Feature Request",
                    "level": 1,
                    "comment": "Just a title",
                },
            ),
            (
                "l3 another title with only level @myhandle",
                "@myhandle",
                {
                    "type": "[F] Feature Request",
                    "level": 3,
                    "comment": "another title with only level",
                },
            ),
            (
                "development a title with only type @myhandle",
                "@myhandle",
                {
                    "type": "[D] Development",
                    "level": 1,
                    "comment": "a title with only type",
                },
            ),
        ],
    )
    def test_trackers_parser_social_media_message_parser_functionality(
        self, parser, message, arg, result
    ):
        """Test the social_media_message_parser for various message formats."""
        assert parser.parse(message, arg) == result
