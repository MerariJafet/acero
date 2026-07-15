"""Unified Research Portal (Sprint 15).

A functional local web app to operate ACERO from one place. Deliberately a zero-dependency,
no-build vanilla-JS single-page app served by FastAPI (a documented scope decision vs. a
React/Vitest/Playwright toolchain — kept offline and dependency-light; see the Sprint 15
report). It talks to the REAL API/services (no central mocks), never exposes secrets or a
shell, serves static files safely, sets a strict CSP, and surfaces gate blocks honestly.
"""
