"""
Test for All Known Bugs (1-7)

This file contains tests for all known bugs documented in KNOWN_BUGS.md.
Each test demonstrates the bug and documents the required fix.
"""
import os
import sys
import tempfile
import re
import inspect
from unittest import TestCase
from datetime import datetime, timedelta
from unittest.mock import patch

# Add parent directory to path to import insightlog
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from insightlog import (
    filter_data, get_date_filter, get_service_settings, get_requests,
    analyze_auth_request, IPv4_REGEX, check_match, _get_auth_year, _get_iso_datetime
)


class TestKnownBugs(TestCase):
    """Test cases for all known bugs (1-7)"""

    # ========================================================================
    # BUG #1: filter_data returns None on error instead of raising
    # ========================================================================

    def test_bug1_filter_data_returns_none_on_error(self):
        """
        BUG #1: filter_data returns None on error instead of raising exception.
        
        Current behavior: Returns None and prints error
        Expected behavior: Should raise exception for consistency
        """
        nonexistent_file = '/nonexistent/path/to/file.log'
        
        # BUG: Currently returns None instead of raising exception
        result = filter_data('test', filepath=nonexistent_file)
        
        self.assertIsNone(result, "BUG: Currently returns None on file error")
        
        # FIX: After fix, this should raise an exception:
        # with self.assertRaises((IOError, EnvironmentError)):
        #     filter_data('test', filepath=nonexistent_file)

    # ========================================================================
    # BUG #2: No check for file encoding
    # ========================================================================

    def test_bug2_no_file_encoding_check(self):
        """
        BUG #2: Files opened without specifying encoding, defaulting to UTF-8.
        May crash with UnicodeDecodeError when encountering non-UTF-8 characters.
        
        Current behavior: Opens files without encoding parameter
        Expected behavior: Should specify encoding or handle encoding errors gracefully
        """
        # Create a file with non-UTF-8 encoding (Windows-1252)
        with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.log') as f:
            # Write some Windows-1252 encoded text (e.g., é character)
            f.write(b'\xe9')  # é in Windows-1252
            temp_file = f.name
        
        try:
            # BUG: Currently may raise UnicodeDecodeError
            try:
                result = filter_data('test', filepath=temp_file)
                # If it doesn't crash, that's also a bug (should handle encoding)
            except UnicodeDecodeError:
                # This is expected with current buggy behavior
                pass
            
            # FIX: After fix, should either:
            # 1. Specify encoding when opening: open(filepath, 'r', encoding='utf-8', errors='replace')
            # 2. Or detect encoding and handle appropriately
        finally:
            if os.path.exists(temp_file):
                os.unlink(temp_file)

    # ========================================================================
    # BUG #3: Type inconsistency in get_date_filter function
    # ========================================================================

    def test_bug3_hour_wildcard_with_default_minute(self):
        """
        BUG #3: hour='*' with default minute (int) raises an exception.
        
        Current behavior: Raises Exception("Date elements aren't valid")
        Expected behavior: Should return a date filter using datedays_format
        """
        nginx_settings = get_service_settings('nginx')
        
        # This currently fails with the bug
        with self.assertRaises(Exception) as context:
            result = get_date_filter(nginx_settings, hour='*')
        
        self.assertIn("Date elements aren't valid", str(context.exception))
        
        # FIX: After fix, this should work:
        # result = get_date_filter(nginx_settings, hour='*')
        # expected = datetime.now().strftime("[%d/%b/%Y")
        # self.assertEqual(result, expected, "hour='*' with default minute should use datedays_format")

    def test_bug3_hour_wildcard_with_explicit_minute(self):
        """BUG #3: hour='*' with explicit minute (int) raises an exception."""
        nginx_settings = get_service_settings('nginx')
        
        with self.assertRaises(Exception) as context:
            result = get_date_filter(nginx_settings, minute=30, hour='*', day=16, month=1, year=1989)
        
        self.assertIn("Date elements aren't valid", str(context.exception))
        
        # FIX: After fix, this should work:
        # result = get_date_filter(nginx_settings, minute=30, hour='*', day=16, month=1, year=1989)
        # expected = '[16/Jan/1989'  # Should use datedays_format, ignoring minute
        # self.assertEqual(result, expected, "hour='*' with explicit minute should use datedays_format")

    def test_bug3_minute_wildcard_works_correctly(self):
        """This test shows that minute='*' works correctly (not a bug case)."""
        nginx_settings = get_service_settings('nginx')
        result = get_date_filter(nginx_settings, minute='*')
        expected = datetime.now().strftime("[%d/%b/%Y:%H")
        self.assertEqual(result, expected, "minute='*' with default hour should work")

    # ========================================================================
    # BUG #4: get_requests returns None on file errors but empty list for empty data
    # ========================================================================

    def test_bug4_nonexistent_file_returns_none(self):
        """
        BUG #4: get_requests returns None for non-existent files.
        
        Current behavior: Returns None
        Expected behavior: Should return [] for consistency
        """
        nonexistent_file = '/nonexistent/path/to/file.log'
        result = get_requests('nginx', filepath=nonexistent_file)
        
        # BUG: Currently returns None
        self.assertIsNone(result, "BUG: Currently returns None for file errors")
        
        # FIX: After fix, this should return []:
        # self.assertEqual(result, [], "Should return empty list for file errors")

    def test_bug4_empty_file_returns_empty_list(self):
        """This test shows that empty files return [] (correct behavior)."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.log') as f:
            temp_file = f.name
        
        try:
            result = get_requests('nginx', filepath=temp_file)
            self.assertEqual(result, [], "Empty file should return empty list")
        finally:
            if os.path.exists(temp_file):
                os.unlink(temp_file)

    def test_bug4_inconsistent_return_types(self):
        """BUG #4: Demonstrates the inconsistency issue."""
        nonexistent_file = '/nonexistent/path/to/file.log'
        result_error = get_requests('nginx', filepath=nonexistent_file)
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.log') as f:
            temp_file = f.name
        
        try:
            result_empty = get_requests('nginx', filepath=temp_file)
            
            # BUG: Inconsistent return types
            self.assertIsNone(result_error, "File error returns None")
            self.assertEqual(result_empty, [], "Empty file returns []")
            
            # FIX: After fix, both should return []:
            # self.assertEqual(result_error, [], "File error should return []")
            # self.assertEqual(result_empty, [], "Empty file should return []")
        finally:
            if os.path.exists(temp_file):
                os.unlink(temp_file)

    # ========================================================================
    # BUG #5: IPv4_REGEX incorrectly matches invalid IP addresses
    # ========================================================================

    def test_bug5_invalid_ip_matched(self):
        """
        BUG #5: Invalid IP patterns are incorrectly matched.
        
        Current behavior: Matches "123a456b789c012" as an IP
        Expected behavior: Should not match invalid IPs
        """
        request_info = "invalid user test from 123a456b789c012"
        result = analyze_auth_request(request_info)
        
        # BUG: Currently incorrectly extracts "123a456b789c012" as IP
        self.assertIsNotNone(result['IP'], "BUG: Currently matches invalid pattern as IP")
        self.assertEqual(result['IP'], "123a456b789c012", "BUG: Matches invalid pattern")
        
        # FIX: After fix, this should return None:
        # self.assertIsNone(result['IP'], "Should not match invalid IP patterns")

    def test_bug5_regex_matches_invalid_patterns(self):
        """BUG #5: Direct test of the regex pattern showing it matches invalid patterns."""
        invalid_patterns = [
            "123a456b789c012",  # Letters instead of dots
            "192.168.1.1.2.3",  # Too many octets
            "192x168y1z1",     # Wrong separators
        ]
        
        for pattern in invalid_patterns:
            matches = re.findall(IPv4_REGEX, pattern)
            # BUG: Currently matches invalid patterns
            self.assertGreater(len(matches), 0, f"BUG: Regex incorrectly matches '{pattern}'")
            
            # FIX: After fix, these should not match:
            # self.assertEqual(len(matches), 0, f"Should not match invalid pattern '{pattern}'")

    def test_bug5_valid_ip_still_works(self):
        """This test ensures valid IPs still work correctly after the fix."""
        request_info = "invalid user test from 192.168.1.1"
        result = analyze_auth_request(request_info)
        self.assertIsNotNone(result['IP'], "Should extract valid IP")
        self.assertEqual(result['IP'], "192.168.1.1", "Should extract correct IP")

    # ========================================================================
    # BUG #6: check_match uses re.match instead of re.search for regex patterns
    # ========================================================================

    def test_bug6_regex_pattern_in_middle_fails(self):
        """
        BUG #6: Regex patterns in the middle of a line fail to match.
        
        Current behavior: Returns False (doesn't match)
        Expected behavior: Should return True (matches)
        """
        line = "abc123def"
        pattern = r'\d+'
        
        # BUG: Currently fails to match because re.match() only matches at start
        result = check_match(line, pattern, is_regex=True)
        self.assertFalse(result, "BUG: Currently fails to match pattern in middle of line")
        
        # FIX: After fix, this should work:
        # self.assertTrue(result, "Should match pattern anywhere in line")

    def test_bug6_filter_data_with_regex_in_middle(self):
        """BUG #6: Demonstrates the bug using filter_data with regex."""
        data = "line1\nabc123def\nline3\n"
        pattern = r'\d+'
        
        # BUG: Currently doesn't match because re.match() only matches at start
        result = filter_data(pattern, data=data, is_regex=True)
        self.assertEqual(result, "", "BUG: Currently returns empty (no match)")
        
        # FIX: After fix, this should match:
        # self.assertIn("abc123def", result, "Should match and return the line")

    def test_bug6_regex_at_start_works(self):
        """This test shows that regex patterns at the start of a line work."""
        line = "123abc"
        pattern = r'\d+'
        result = check_match(line, pattern, is_regex=True)
        self.assertTrue(result, "Should match pattern at start of line")

    def test_bug6_docstring_expects_search_behavior(self):
        """This test verifies that the docstring says 'contains/matches'."""
        docstring = inspect.getdoc(check_match)
        self.assertIn("contains", docstring.lower() or "matches",
                     "Docstring suggests 'contains' behavior (re.search), not 'starts with' (re.match)")

    # ========================================================================
    # BUG #7: _get_auth_year() has flawed year detection logic
    # ========================================================================

    def test_bug7_only_jan_1_midnight_detects_previous_year(self):
        """
        BUG #7: Only Jan 1 at midnight triggers previous year detection.
        
        Current behavior: Only returns previous year on Jan 1 at midnight
        Expected behavior: Should detect previous year for dates that are "too far in the future"
        """
        # Test on Jan 1 at midnight - currently works
        with patch('insightlog.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2024, 1, 1, 0, 0, 0)
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
            year = _get_auth_year()
            self.assertEqual(year, 2023, "Should return previous year on Jan 1 at midnight")
        
        # Test on Jan 1 at 1 AM - currently fails
        with patch('insightlog.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2024, 1, 1, 1, 0, 0)
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
            year = _get_auth_year()
            # BUG: Currently returns 2024 instead of 2023
            self.assertEqual(year, 2024, "BUG: Currently returns current year even on Jan 1 at 1 AM")
            
            # FIX: After fix, should still return 2023:
            # self.assertEqual(year, 2023, "Should return previous year on Jan 1")

    def test_bug7_december_log_in_march_incorrectly_assigned_current_year(self):
        """
        BUG #7: December logs in March are incorrectly assigned current year.
        """
        auth_settings = get_service_settings('auth')
        
        # Simulate current date as March 15, 2024
        with patch('insightlog.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2024, 3, 15, 12, 0, 0)
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
            
            # Parse a December 20 log entry (no year in auth logs)
            log_date = "Dec 20 22:00:32"
            date_pattern = auth_settings['date_pattern']
            date_keys = auth_settings['date_keys']
            
            result = _get_iso_datetime(log_date, date_pattern, date_keys)
            
            # BUG: Currently parses as 2024 instead of 2023
            self.assertIn("2024", result, "BUG: Currently assigns current year (2024)")
            self.assertNotIn("2023", result, "BUG: Should be 2023 but isn't")
            
            # FIX: After fix, should parse as 2023:
            # self.assertIn("2023", result, "Should assign previous year (2023)")
            # self.assertNotIn("2024", result, "Should not assign current year")

    def test_bug7_future_date_detection_logic(self):
        """BUG #7: Current logic doesn't detect 'future' dates from previous year."""
        test_cases = [
            (datetime(2024, 3, 15), datetime(2023, 12, 20)),  # Dec 20 in March
            (datetime(2024, 6, 1), datetime(2023, 11, 15)),  # Nov 15 in June
            (datetime(2024, 1, 15), datetime(2023, 12, 31)),  # Dec 31 in mid-January
        ]
        
        for current_date, log_date in test_cases:
            with patch('insightlog.datetime') as mock_datetime:
                mock_datetime.now.return_value = current_date
                mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
                year = _get_auth_year()
                
                # BUG: Currently returns current year for all cases except Jan 1 midnight
                expected_previous_year = log_date.year
                self.assertEqual(year, current_date.year,
                               f"BUG: Currently returns current year ({current_date.year}) instead of {expected_previous_year}")

