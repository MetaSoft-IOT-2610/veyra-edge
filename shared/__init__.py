"""Shared kernel package for the Veyra Edge Service.

Contains cross-cutting infrastructure components that are shared across
all bounded contexts (IAM, Monitoring, etc.), such as the database connection
singleton, runtime configuration, and initialization helpers.

This package intentionally has no domain logic; it only provides
technical plumbing required by the application.
"""
