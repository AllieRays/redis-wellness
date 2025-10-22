"""
Health Records Search Tool - LangChain tool for querying health metrics.

Provides the search_health_records_by_metric tool which allows searching
for specific health metrics within a time period.
"""

import json
import logging
from typing import Any

from langchain_core.tools import tool

from ...services.redis_apple_health_manager import redis_manager
from ...utils.conversion_utils import convert_weight_to_lbs as _convert_weight_to_lbs
from ...utils.time_utils import (
    parse_health_record_date as _parse_health_record_date,
)
from ...utils.time_utils import (
    parse_time_period as _parse_time_period,
)
from ...utils.user_config import get_user_health_data_key

logger = logging.getLogger(__name__)


def create_search_health_records_tool(user_id: str):
    """
    Create search_health_records_by_metric tool bound to a specific user.

    Args:
        user_id: The user identifier to bind to this tool

    Returns:
        LangChain tool instance
    """

    @tool
    def search_health_records_by_metric(
        metric_types: list[str], time_period: str = "recent"
    ) -> dict[str, Any]:
        """
        Search for specific health metrics within a time period.

        Use this when the user asks about specific health metrics like:
        - BMI, weight, steps, heart rate, active energy
        - Recent values or trends
        - Historical data ("what was my weight in September?")

        Args:
            metric_types: List of metric types (e.g., ["BodyMassIndex", "BodyMass"])
            time_period: Natural language time description (default: "recent")
                Examples:
                - "September" → all of September in current year
                - "September 2024" → all of September 2024
                - "early September" → first 10 days of September
                - "late August" → last 10 days of August
                - "last 2 weeks" → past 14 days
                - "this month" → current month so far
                - "recent" → last 30 days (default)

        Examples:
            - "What was my weight in September?" → time_period="September"
            - "What's my current weight?" → time_period="recent"
            - "Show my BMI in early August" → time_period="early August"
            - "Weight trend last 2 weeks" → time_period="last 2 weeks"

        Returns:
            Dict with matching records and metadata
        """
        logger.info(
            f"🔧 search_health_records_by_metric called: metrics={metric_types}, time_period='{time_period}', user_id={user_id}"
        )

        try:
            # Parse time period into date range
            filter_start, filter_end, time_range_desc = _parse_time_period(time_period)
            logger.info(
                f"📅 Parsed '{time_period}' → {filter_start.strftime('%Y-%m-%d')} to {filter_end.strftime('%Y-%m-%d')} ({time_range_desc})"
            )

            with redis_manager.redis_manager.get_connection() as redis_client:
                main_key = get_user_health_data_key()
                health_data_json = redis_client.get(main_key)

                if not health_data_json:
                    return {"error": "No health data found for user", "records": []}

                health_data = json.loads(health_data_json)
                metrics_records = health_data.get("metrics_records", {})
                metrics_summary = health_data.get("metrics_summary", {})

                results = []
                for metric_type in metric_types:
                    # Try to get historical records first
                    if metric_type in metrics_records:
                        all_records = metrics_records[metric_type]
                        logger.info(
                            f"📊 Found {len(all_records)} total {metric_type} records"
                        )

                        # Filter by date range and limit
                        filtered_records = []
                        for record in all_records:  # Keep chronological order
                            # Use centralized date parsing utility
                            record_date = _parse_health_record_date(record["date"])

                            # Check if record is within date range
                            if filter_start <= record_date <= filter_end:
                                value = record["value"]
                                unit = record["unit"]

                                # Convert weight from kg/lb to lbs
                                if metric_type == "BodyMass":
                                    value = _convert_weight_to_lbs(value, unit)
                                elif unit:
                                    value = f"{value} {unit}"

                                filtered_records.append(
                                    {
                                        "value": value,
                                        "date": record["date"][:10],  # Just YYYY-MM-DD
                                    }
                                )

                        logger.info(
                            f"✅ Filtered to {len(filtered_records)} {metric_type} records ({time_range_desc})"
                        )

                        results.append(
                            {
                                "metric_type": metric_type,
                                "records": filtered_records,
                                "total_found": len(filtered_records),
                                "time_range": time_range_desc,
                            }
                        )

                    # Fall back to summary if no detailed records
                    elif metric_type in metrics_summary:
                        metric_info = metrics_summary[metric_type]
                        latest_value = metric_info.get("latest_value", "N/A")
                        unit = metric_info.get("unit", "")

                        if metric_type == "BodyMass" and latest_value != "N/A":
                            latest_value = _convert_weight_to_lbs(latest_value, unit)
                        elif latest_value != "N/A" and unit:
                            latest_value = f"{latest_value} {unit}"

                        results.append(
                            {
                                "metric_type": metric_type,
                                "latest_value": latest_value,
                                "latest_date": metric_info.get("latest_date", "N/A"),
                                "total_records": metric_info.get("count", 0),
                                "time_range": time_range_desc,
                            }
                        )

                logger.info(f"📤 Returning {len(results)} metric types")
                return {
                    "results": results,
                    "total_metrics": len(results),
                    "searched_metrics": metric_types,
                }
        except Exception as e:
            logger.error(
                f"❌ Error in search_health_records_by_metric: {type(e).__name__}: {e}",
                exc_info=True,
            )
            return {
                "error": f"Failed to search health records: {str(e)}",
                "error_type": type(e).__name__,
                "results": [],
            }

    return search_health_records_by_metric
