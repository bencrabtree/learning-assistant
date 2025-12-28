"""
Research Radar - Background paper monitoring system.

Continuously scans for noteworthy papers and sends notifications.
"""

from src.radar.daemon import ResearchRadar, run_radar, run_radar_once

__all__ = ["ResearchRadar", "run_radar", "run_radar_once"]
