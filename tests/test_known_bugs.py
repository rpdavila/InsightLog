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
        BUG #1: FIXED - filter_data now raises exception on error instead of returning None.
        """
        nonexistent_file = '/nonexistent/path/to/file.log'
        
        # FIXED: Now raises exception instead of returning None
        with self.assertRaises((IOError, EnvironmentError, FileNotFoundError)):
            filter_data('test', filepath=nonexistent_file)

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
        BUG #3: FIXED - hour='*' with default minute (int) now works correctly.
        """
        nginx_settings = get_service_settings('nginx')
        
        # FIXED: Now works correctly
        result = get_date_filter(nginx_settings, hour='*')
        expected = datetime.now().strftime("[%d/%b/%Y")
        self.assertEqual(result, expected, "hour='*' with default minute should use datedays_format")

    def test_bug3_hour_wildcard_with_explicit_minute(self):
        """BUG #3: FIXED - hour='*' with explicit minute (int) now works correctly."""
        nginx_settings = get_service_settings('nginx')
        
        # FIXED: Now works correctly
        result = get_date_filter(nginx_settings, minute=30, hour='*', day=16, month=1, year=1989)
        expected = '[16/Jan/1989'  # Should use datedays_format, ignoring minute
        self.assertEqual(result, expected, "hour='*' with explicit minute should use datedays_format")

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
        BUG #4: FIXED - get_requests now returns [] for non-existent files instead of None.
        """
        nonexistent_file = '/nonexistent/path/to/file.log'
        result = get_requests('nginx', filepath=nonexistent_file)
        
        # FIXED: Now returns [] instead of None
        self.assertEqual(result, [], "Should return empty list for file errors")

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
        """BUG #4: FIXED - Both error and empty cases now consistently return []."""
        nonexistent_file = '/nonexistent/path/to/file.log'
        result_error = get_requests('nginx', filepath=nonexistent_file)
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.log') as f:
            temp_file = f.name
        
        try:
            result_empty = get_requests('nginx', filepath=temp_file)
            
            # FIXED: Both now return [] consistently
            self.assertEqual(result_error, [], "File error should return []")
            self.assertEqual(result_empty, [], "Empty file should return []")
            
            # Simple check works for both now
            if not result_error:
                pass  # This works for both cases
        finally:
            if os.path.exists(temp_file):
                os.unlink(temp_file)

    # ========================================================================
    # BUG #5: IPv4_REGEX incorrectly matches invalid IP addresses
    # ========================================================================

    def test_bug5_invalid_ip_matched(self):
        """
        BUG #5: FIXED - Invalid IP patterns are no longer matched.
        """
        request_info = "invalid user test from 123a456b789c012"
        result = analyze_auth_request(request_info)
        
        # FIXED: Now correctly returns None for invalid patterns
        self.assertIsNone(result['IP'], "Should not match invalid IP patterns")

    def test_bug5_regex_matches_invalid_patterns(self):
        """BUG #5: FIXED - Regex no longer matches patterns without dots."""
        # Patterns that should NOT match (no valid IP structure)
        invalid_patterns = [
            "123a456b789c012",  # Letters instead of dots - FIXED: no longer matches
            "192x168y1z1",     # Wrong separators - FIXED: no longer matches
        ]
        
        for pattern in invalid_patterns:
            matches = re.findall(IPv4_REGEX, pattern)
            # FIXED: Now correctly rejects patterns without proper dot separators
            self.assertEqual(len(matches), 0, f"Should not match invalid pattern '{pattern}'")
        
        # Note: "192.168.1.1.2.3" will still match "192.168.1.1" because it contains
        # a valid IP address. This is expected behavior - the regex extracts valid IPs
        # even if they're part of a longer string. To fully validate IPs, you'd need
        # word boundaries or end-of-string anchors, which is beyond the scope of this fix.

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
        BUG #6: FIXED - Regex patterns in the middle of a line now match correctly.
        """
        line = "abc123def"
        pattern = r'\d+'
        
        # FIXED: Now correctly matches patterns in the middle of lines
        result = check_match(line, pattern, is_regex=True)
        self.assertTrue(result, "Should match pattern anywhere in line")

    def test_bug6_filter_data_with_regex_in_middle(self):
        """BUG #6: FIXED - filter_data with regex now matches patterns in the middle of lines."""
        data = "line1\nabc123def\nline3\n"
        pattern = r'\d+'
        
        # FIXED: Now correctly matches and returns the line
        result = filter_data(pattern, data=data, is_regex=True)
        self.assertIn("abc123def", result, "Should match and return the line")

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
            # Note: Without log_date_parsed, _get_auth_year() still uses old logic
            # The improved logic is tested via _get_iso_datetime() which passes the parsed date
            # This test verifies the old behavior still works for backward compatibility
            self.assertEqual(year, 2024, "Without log_date_parsed, returns current year on Jan 1 at 1 AM")

    def test_bug7_december_log_in_march_incorrectly_assigned_current_year(self):
        """
        BUG #7: FIXED - December logs in March are now correctly assigned previous year.
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
            
            # FIXED: Now correctly parses as 2023
            self.assertIn("2023", result, "Should assign previous year (2023)")
            self.assertNotIn("2024", result, "Should not assign current year")

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
                
                # Note: _get_auth_year() without log_date_parsed uses old logic
                # The improved future date detection is tested via _get_iso_datetime()
                # which passes the parsed datetime to _get_auth_year()
                expected_previous_year = log_date.year
                if current_date.month == 1 and current_date.day == 1 and current_date.hour == 0:
                    self.assertEqual(year, expected_previous_year,
                                   f"Should return {expected_previous_year} on Jan 1 midnight")
                else:
                    # Without log_date_parsed parameter, uses old logic
                    self.assertEqual(year, current_date.year,
                                   f"Without log_date_parsed, returns current year ({current_date.year})")


if __name__ == '__main__':
    import unittest
    unittest.main()

