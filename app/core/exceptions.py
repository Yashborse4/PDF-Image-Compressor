"""Domain-specific exceptions for DocuTools."""

from __future__ import annotations


class DocuToolsError(Exception):
    """Base exception for all DocuTools operational errors."""

    def __init__(self, message: str, details: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or ""


class CorruptedFileError(DocuToolsError):
    """Raised when an input document or image is damaged or unreadable."""


class PasswordRequiredError(DocuToolsError):
    """Raised when an encrypted PDF requires a password to open or edit."""


class InvalidPasswordError(DocuToolsError):
    """Raised when the supplied password is incorrect."""


class UnsupportedFormatError(DocuToolsError):
    """Raised when a file type is not supported by the processing engine."""


class DiskSpaceError(DocuToolsError):
    """Raised when the destination drive lacks sufficient space."""


class TaskCancelledError(DocuToolsError):
    """Raised when a processing task is actively cancelled by the user."""


class ConversionError(DocuToolsError):
    """Raised when file format conversion fails."""


class ValidationError(DocuToolsError):
    """Raised when file parameters, page ranges, or dimensions fail validation."""
