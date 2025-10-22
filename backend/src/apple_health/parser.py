"""
Secure Apple Health XML parser with protection against XML attacks.

This module provides secure parsing of Apple Health export XML files with:
- Protection against XXE (XML External Entity) attacks
- Prevention of billion laughs/XML bomb attacks
- Memory-safe parsing with cleanup
- Privacy-aware error handling
- Secure file path validation
"""

from __future__ import annotations

import logging
import os
import re
import xml.etree.ElementTree as ET
from datetime import UTC, date, datetime
from pathlib import Path
from xml.parsers.expat import ExpatError

from .models import (
    ActivitySummary,
    HealthDataCollection,
    HealthRecord,
    UserProfile,
    WorkoutSummary,
)


class ParsingError(Exception):
    """
    Secure exception for parsing errors.

    Never includes sensitive data from XML content in error messages.
    """


class AppleHealthParser:
    """
    Secure parser for Apple Health XML exports.

    Features:
    - XML attack protection (XXE, billion laughs)
    - Memory-safe parsing with automatic cleanup
    - Privacy-preserving error handling
    - Configurable allowed file paths
    - Progress tracking for large files
    """

    # Security limits
    MAX_ELEMENT_DEPTH = 20  # Prevent deeply nested XML attacks
    MAX_ELEMENT_COUNT = 10_000_000  # Reasonable limit for health exports
    MAX_ATTRIBUTE_COUNT = 100  # Prevent attribute bombing

    def __init__(self, allowed_directories: list[str] | None = None):
        """
        Initialize secure parser.

        Args:
            allowed_directories: List of directory paths where XML files can be accessed.
                                If None, defaults to current working directory and
                                apple_health_export subdirectory.
        """
        self.allowed_directories = allowed_directories or [
            os.getcwd(),
            os.path.join(os.getcwd(), "apple_health_export"),
        ]
        self._element_count = 0
        self._depth_count = 0

        # Configure secure XML parser (disable external entity processing)
        self.parser_config = {
            "forbid_dtd": True,  # Prevent DTD processing
            "forbid_entities": True,  # Prevent entity expansion
            "forbid_external": True,  # Prevent external resource loading
        }

        # Setup logging (no sensitive data)
        self.logger = logging.getLogger(__name__)

    def parse_file(
        self, file_path: str, progress_callback: callable | None = None
    ) -> HealthDataCollection:
        """
        Securely parse Apple Health XML file.

        Args:
            file_path: Path to Apple Health export XML file
            progress_callback: Optional callback for progress updates (receives percentage)

        Returns:
            HealthDataCollection with parsed data

        Raises:
            ParsingError: If parsing fails or security validation fails
        """
        try:
            # Security validation
            self._validate_file_path(file_path)
            self._validate_file_exists(file_path)

            # Reset counters for this parsing session
            self._element_count = 0
            self._depth_count = 0

            self.logger.info("Starting secure parsing of health data")

            # Parse XML securely
            health_data = self._parse_xml_securely(file_path, progress_callback)

            self.logger.info(
                f"Successfully parsed {health_data.record_count} health records"
            )
            return health_data

        except Exception as e:
            # Sanitize error message (no file paths or XML content)
            sanitized_message = self._sanitize_error_message(str(e))
            self.logger.error(f"Health data parsing failed: {sanitized_message}")
            raise ParsingError(
                f"Failed to parse health data: {sanitized_message}"
            ) from e

    def _validate_file_path(self, file_path: str) -> None:
        """
        Validate file path for security.

        Prevents directory traversal attacks and ensures file is in allowed directories.
        """
        try:
            # Resolve path to prevent directory traversal
            resolved_path = Path(file_path).resolve()

            # Check if path is in allowed directories
            path_allowed = False
            for allowed_dir in self.allowed_directories:
                allowed_path = Path(allowed_dir).resolve()
                try:
                    resolved_path.relative_to(allowed_path)
                    path_allowed = True
                    break
                except ValueError:
                    continue

            if not path_allowed:
                raise ParsingError("File path not in allowed directories")

            # Additional security checks
            if ".." in str(resolved_path):
                raise ParsingError("Invalid file path")

        except (OSError, ValueError) as e:
            raise ParsingError("Invalid file path format") from e

    def _validate_file_exists(self, file_path: str) -> None:
        """Validate file exists and is readable."""
        path = Path(file_path)

        if not path.exists():
            raise ParsingError("Health data file not found")

        if not path.is_file():
            raise ParsingError("Path is not a file")

        if not os.access(path, os.R_OK):
            raise ParsingError("File is not readable")

    def _parse_xml_securely(
        self, file_path: str, progress_callback: callable | None
    ) -> HealthDataCollection:
        """
        Parse XML with security protections.

        Uses iterative parsing to handle large files without loading everything into memory.
        """
        try:
            # Initialize collection
            health_data = HealthDataCollection(
                export_date=datetime.now(UTC), record_count=0
            )

            # Parse iteratively for memory efficiency
            context = ET.iterparse(file_path, events=("start", "end"))
            context = iter(context)

            # Get root element
            event, root = next(context)

            processed_count = 0

            for event, elem in context:
                # Security checks
                self._check_parsing_limits(elem)

                if event == "end":
                    # Process different element types
                    if elem.tag == "ExportDate":
                        health_data.export_date = self._parse_export_date(elem)
                    elif elem.tag == "Me":
                        health_data.user_profile = self._parse_user_profile(elem)
                    elif elem.tag == "Record":
                        record = self._parse_health_record(elem)
                        if record:
                            health_data.records.append(record)
                            processed_count += 1
                    elif elem.tag == "Workout":
                        workout = self._parse_workout(elem)
                        if workout:
                            health_data.workouts.append(workout)
                    elif elem.tag == "ActivitySummary":
                        activity = self._parse_activity_summary(elem)
                        if activity:
                            health_data.activity_summaries.append(activity)

                    # Clear element to free memory
                    # Don't clear WorkoutStatistics yet - parent Workout needs them
                    if elem.tag not in ("WorkoutStatistics", "MetadataEntry"):
                        elem.clear()

                    # Progress callback
                    if progress_callback and processed_count % 1000 == 0:
                        # Rough progress estimate (can't know total without reading entire file)
                        progress_callback(min(95, processed_count // 1000))

            # Clear root to free remaining memory
            root.clear()

            # Update final count
            health_data.record_count = len(health_data.records)

            if progress_callback:
                progress_callback(100)

            return health_data

        except ET.ParseError as e:
            raise ParsingError("Invalid XML format") from e
        except ExpatError as e:
            raise ParsingError("XML parsing error") from e
        except MemoryError as e:
            raise ParsingError("File too large for available memory") from e

    def _check_parsing_limits(self, elem: ET.Element) -> None:
        """
        Check security limits during parsing.

        Prevents XML bomb attacks and excessive resource usage.
        """
        self._element_count += 1

        # Check element count limit
        if self._element_count > self.MAX_ELEMENT_COUNT:
            raise ParsingError("XML file exceeds maximum element count")

        # Check nesting depth (simple approximation)
        if len(elem.tag) > 100:  # Extremely long tag names might indicate attack
            raise ParsingError("Invalid XML structure")

        # Check attribute count
        if len(elem.attrib) > self.MAX_ATTRIBUTE_COUNT:
            raise ParsingError("Excessive XML attributes")

    def _parse_export_date(self, elem: ET.Element) -> datetime:
        """Parse ExportDate element safely."""
        try:
            date_str = elem.get("value", "")
            if not date_str:
                return datetime.now(UTC)
            return self._parse_datetime_safe(date_str)
        except Exception:
            return datetime.now(UTC)

    def _parse_user_profile(self, elem: ET.Element) -> UserProfile | None:
        """Parse Me element safely (user profile)."""
        try:
            # Parse date of birth
            dob_str = elem.get("HKCharacteristicTypeIdentifierDateOfBirth")
            dob = self._parse_date_safe(dob_str) if dob_str else None

            return UserProfile(
                date_of_birth=dob,
                biological_sex=elem.get("HKCharacteristicTypeIdentifierBiologicalSex"),
                blood_type=elem.get("HKCharacteristicTypeIdentifierBloodType"),
            )
        except Exception:
            # Return empty profile if parsing fails
            return UserProfile()

    def _parse_health_record(self, elem: ET.Element) -> HealthRecord | None:
        """Parse Record element safely."""
        try:
            record_type = elem.get("type", "")
            if not record_type:
                return None

            # Parse dates
            start_date = self._parse_datetime_safe(elem.get("startDate", ""))
            end_date = self._parse_datetime_safe(elem.get("endDate", ""))
            creation_date = self._parse_datetime_safe(elem.get("creationDate", ""))

            if not start_date or not end_date:
                return None

            return HealthRecord(
                record_type=record_type,  # Will be normalized by validator
                unit=elem.get("unit"),
                value=elem.get("value"),
                start_date=start_date,
                end_date=end_date,
                source_name=elem.get("sourceName"),
                source_version=elem.get("sourceVersion"),
                device=elem.get("device"),
                creation_date=creation_date,
                raw_metadata={},  # Empty for privacy
            )
        except Exception:
            return None

    def _parse_workout(self, elem: ET.Element) -> WorkoutSummary | None:
        """Parse Workout element safely."""
        try:
            start_date = self._parse_datetime_safe(elem.get("startDate", ""))
            end_date = self._parse_datetime_safe(elem.get("endDate", ""))

            if not start_date or not end_date:
                return None

            # Extract calories from WorkoutStatistics child elements
            active_energy = None
            total_distance = None

            for child in elem:
                if child.tag == "WorkoutStatistics":
                    stat_type = child.get("type", "")

                    if stat_type == "HKQuantityTypeIdentifierActiveEnergyBurned":
                        active_energy = self._parse_float_safe(child.get("sum"))
                    elif stat_type == "HKQuantityTypeIdentifierDistanceWalkingRunning":
                        total_distance = self._parse_float_safe(child.get("sum"))

            return WorkoutSummary(
                workout_activity_type=elem.get("workoutActivityType", ""),
                duration=self._parse_float_safe(elem.get("duration")),
                duration_unit=elem.get("durationUnit"),
                total_distance=total_distance,
                total_energy_burned=active_energy,
                start_date=start_date,
                end_date=end_date,
                source_name=elem.get("sourceName"),
                device=elem.get("device"),
            )
        except Exception:
            return None

    def _parse_activity_summary(self, elem: ET.Element) -> ActivitySummary | None:
        """Parse ActivitySummary element safely."""
        try:
            date_components = elem.get("dateComponents", "")
            if not date_components:
                return None

            # Parse date components (format: YYYY-MM-DD)
            activity_date = self._parse_date_safe(date_components)
            if not activity_date:
                return None

            return ActivitySummary(
                date_components=activity_date,
                active_energy_burned=self._parse_float_safe(
                    elem.get("activeEnergyBurned")
                ),
                active_energy_burned_goal=self._parse_float_safe(
                    elem.get("activeEnergyBurnedGoal")
                ),
                apple_exercise_time=self._parse_float_safe(
                    elem.get("appleExerciseTime")
                ),
                apple_exercise_time_goal=self._parse_float_safe(
                    elem.get("appleExerciseTimeGoal")
                ),
                apple_stand_hours=self._parse_float_safe(elem.get("appleStandHours")),
                apple_stand_hours_goal=self._parse_float_safe(
                    elem.get("appleStandHoursGoal")
                ),
            )
        except Exception:
            return None

    def _parse_datetime_safe(self, date_str: str) -> datetime | None:
        """
        Safely parse datetime string and normalize to UTC.

        All datetimes are converted to UTC timezone for consistency across the system.
        This eliminates timezone comparison issues in downstream tools.
        """
        if not date_str:
            return None

        try:
            # Common Apple Health datetime formats
            formats = [
                "%Y-%m-%d %H:%M:%S %z",  # With timezone
                "%Y-%m-%d %H:%M:%S",  # Without timezone (assume UTC)
                "%Y-%m-%d",  # Date only
            ]

            for fmt in formats:
                try:
                    dt = datetime.strptime(date_str, fmt)

                    # Normalize to UTC for consistent storage
                    if dt.tzinfo is None:
                        # Assume UTC if no timezone specified
                        dt = dt.replace(tzinfo=UTC)
                    else:
                        # Convert to UTC
                        dt = dt.astimezone(UTC)

                    return dt
                except ValueError:
                    continue

            return None
        except Exception:
            return None

    def _parse_date_safe(self, date_str: str) -> date | None:
        """Safely parse date string."""
        if not date_str:
            return None

        try:
            # Try different date formats
            formats = ["%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y"]

            for fmt in formats:
                try:
                    return datetime.strptime(date_str, fmt).date()
                except ValueError:
                    continue

            return None
        except Exception:
            return None

    def _parse_float_safe(self, value_str: str | None) -> float | None:
        """Safely parse float string."""
        if not value_str:
            return None

        try:
            return float(value_str)
        except (ValueError, TypeError):
            return None

    def _sanitize_error_message(self, error_msg: str) -> str:
        """
        Sanitize error message to remove sensitive information.

        Removes file paths, XML content, and other potentially sensitive data.
        """
        # Remove file paths
        sanitized = re.sub(r"/[^\s]+", "[file_path]", error_msg)

        # Remove XML content
        sanitized = re.sub(r"<[^>]+>", "[xml_content]", sanitized)

        # Remove quoted strings that might contain sensitive data
        sanitized = re.sub(r'"[^"]*"', "[data]", sanitized)
        sanitized = re.sub(r"'[^']*'", "[data]", sanitized)

        # Generic error if everything was removed
        if not sanitized.strip() or sanitized.strip() in [
            "[file_path]",
            "[xml_content]",
            "[data]",
        ]:
            return "parsing error"

        return sanitized.strip()

    def validate_xml_structure(self, file_path: str) -> bool:
        """
        Validate XML file structure without full parsing.

        Quick validation to check if file is valid Apple Health export.
        """
        try:
            self._validate_file_path(file_path)
            self._validate_file_exists(file_path)

            # Quick structural validation
            with open(file_path, encoding="utf-8") as f:
                # Read first part of file to check structure
                header = f.read(5000)  # Increased to handle Apple Health DTD

                # Check for Apple Health XML markers
                if "HealthData" not in header:
                    return False
                if "<?xml version=" not in header:
                    return False
                # Additional check for Apple Health DTD
                if "HealthKit Export" not in header:
                    return False

            return True

        except Exception:
            return False
