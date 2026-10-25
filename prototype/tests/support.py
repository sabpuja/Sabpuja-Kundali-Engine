"""Shared helpers for the prototype tests.

Tests that compute charts need SABPUJA_TEST_EPHE_PATH (the pinned .se1
directory). When it is unset they are skipped and reported as unavailable.
"""
import os
import unittest

EPHE = os.environ.get("SABPUJA_TEST_EPHE_PATH")
requires_data = unittest.skipUnless(EPHE, "SABPUJA_TEST_EPHE_PATH unset: real Swiss data unavailable")

# Approved synthetic inputs only (no real person's birth data).
SYNTHETIC = [
    ("in-new-delhi", "1990-05-15", "10:30"),
    ("in-mumbai", "1984-11-02", "23:59:59"),
    ("in-kolkata", "1970-01-01", "00:00"),
    ("in-chennai", "2000-02-29", "05:45:30"),
    ("in-bengaluru", "2012-12-21", "12:00"),
    ("in-hyderabad", "1999-12-31", "23:30"),
    ("in-jaipur", "2024-08-15", "06:05"),
    ("in-lucknow", "1975-06-25", "18:20:10"),
    ("in-varanasi", "2100-12-31", "23:59:59"),
    ("in-guwahati", "2070-10-04", "06:00"),
    ("gb-london", "2020-06-21", "12:00"),
]
