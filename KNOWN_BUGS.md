# Known Bugs and Replication Steps
## DONE
## 1. filter_data returns None on error instead of raising
- **How to replicate:**
  - Call `filter_data` with a non-existent file path.
  - Instead of raising an exception, it prints the error and returns None.
  - This makes error handling inconsistent with the rest of the codebase which uses exceptions.
## DONE
## 2. No check for file encoding
- **How to replicate:**
  - Try to analyze a log file with non-UTF-8 encoding (e.g., ISO-8859-1, Windows-1252).
  - The code opens files without specifying encoding, defaulting to UTF-8.
  - May crash with a `UnicodeDecodeError` when encountering non-UTF-8 characters.

## 3. Type inconsistency in get_date_filter function
- **How to replicate:**
  - Call `get_date_filter()` with `minute='*'` or `hour='*'` as strings.
  - The function accepts `'*'` as a string for wildcards, but default parameters are integers (`datetime.now().minute`, `datetime.now().hour`).
  - This creates a type mismatch where defaults can never be `'*'`, but the function logic expects it can be.
  - The function will raise an exception when using defaults with wildcard logic.

## 4. get_requests returns None on file errors but empty list for empty data
- **How to replicate:**
  - Call `get_requests()` with a non-existent file path.
  - Returns `None` on file errors.
  - Call `get_requests()` with an empty file or filtered data.
  - Returns `[]` for empty data.
  - This inconsistent return type (None vs empty list) can cause issues if code checks for one but not the other.

## 5. IPv4_REGEX incorrectly matches invalid IP addresses
- **How to replicate:**
  - The regex pattern `r'(\d+.\d+.\d+.\d+)'` uses `.` instead of `\.` to match dots.
  - Since `.` matches any character in regex, this will match invalid patterns like "123a456b789c012" or "192.168.1.1.2.3".
  - Test with `analyze_auth_request("invalid user test from 123a456b789c012")` - it will incorrectly extract "123a456b789c012" as an IP.

## 6. check_match uses re.match instead of re.search for regex patterns
- **How to replicate:**
  - Call `filter_data` with `is_regex=True` and a pattern that should match in the middle of a line.
  - For example: `filter_data(r'\d+', data="abc123def", is_regex=True)`.
  - The function uses `re.match()` which only matches at the start of the string, so it will fail to match.
  - The docstring says "contains/matches" which suggests it should use `re.search()` instead.

## 7. _get_auth_year() has flawed year detection logic
- **How to replicate:**
  - The function only checks if the current date is January 1st at midnight to determine if auth logs might be from the previous year.
  - This logic is too narrow - auth logs from the previous year on any date (not just Jan 1) will be incorrectly assigned the current year.
  - For example, if today is March 15, 2024, and an auth log entry is from December 20, 2023, it will be incorrectly parsed as December 20, 2024.
  - The function should use more sophisticated logic (e.g., checking if the log date is more than X days in the future, suggesting it's from last year).
