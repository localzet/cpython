"""Experimental compatibility analysis for Python data-model schemas."""

from .metadata import FieldMeta, MetadataProvider, SchemaMeta, UnsupportedSchema, inspect_schema
from .migration import MigrationIssue, MigrationReport, analyze_migration

__all__ = [
    "FieldMeta", "MetadataProvider", "SchemaMeta", "UnsupportedSchema",
    "inspect_schema", "MigrationIssue", "MigrationReport", "analyze_migration",
]
