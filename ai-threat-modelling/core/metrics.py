"""
Metrics collection and monitoring for threat modeling pipeline.
Tracks latency, tokens, errors, and exports reports.
"""

import json
import csv
import logging
import time
from typing import Dict, Any, List
from datetime import datetime
import os

logger = logging.getLogger(__name__)

METRICS_DIR = "outputs/metrics"


class MetricsCollector:
    """Collects and manages metrics for threat modeling runs."""
    
    def __init__(self):
        """Initialize metrics collector."""
        self.metrics: Dict[str, Any] = {
            "timestamp": datetime.now().isoformat(),
            "phases": {}
        }
        self._phase_start_time = {}
    
    def start_phase(self, phase_name: str) -> None:
        """
        Start timing a phase.
        
        Args:
            phase_name: Name of the phase (e.g., "STRIDE Generation")
        """
        self._phase_start_time[phase_name] = time.time()
        logger.info(f"[METRICS] Starting phase: {phase_name}")
    
    def end_phase(self, phase_name: str, **extra_metrics) -> None:
        """
        End timing a phase and record elapsed time.
        
        Args:
            phase_name: Name of the phase
            **extra_metrics: Additional metrics to record (tokens, items, etc.)
        """
        if phase_name not in self._phase_start_time:
            logger.warning(f"Phase '{phase_name}' was not started")
            return
        
        elapsed = time.time() - self._phase_start_time[phase_name]
        
        self.metrics["phases"][phase_name] = {
            "elapsed_seconds": round(elapsed, 2),
            **extra_metrics
        }
        
        logger.info(f"[METRICS] Completed {phase_name}: {elapsed:.2f}s")
    
    def record_metric(self, key: str, value: Any) -> None:
        """
        Record a single metric.
        
        Args:
            key: Metric name
            value: Metric value
        """
        self.metrics[key] = value
        logger.info(f"[METRICS] {key}: {value}")
    
    def record_error(self, error_type: str, error_msg: str = "") -> None:
        """
        Record an error occurrence.
        
        Args:
            error_type: Type of error (e.g., "JSON_PARSE_ERROR")
            error_msg: Error message
        """
        if "errors" not in self.metrics:
            self.metrics["errors"] = []
        
        self.metrics["errors"].append({
            "type": error_type,
            "message": error_msg,
            "timestamp": datetime.now().isoformat()
        })
        
        logger.warning(f"[METRICS] Error recorded: {error_type}")
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get collected metrics."""
        return self.metrics
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Get summary of metrics.
        
        Returns:
            Summary dict with key statistics
        """
        total_time = sum(
            p.get("elapsed_seconds", 0) 
            for p in self.metrics.get("phases", {}).values()
        )
        
        error_count = len(self.metrics.get("errors", []))
        
        return {
            "total_runtime_seconds": round(total_time, 2),
            "phases_completed": len(self.metrics.get("phases", {})),
            "errors": error_count,
            "threat_count": self.metrics.get("threat_count", 0),
            "timestamp": self.metrics.get("timestamp")
        }


def _ensure_metrics_dir():
    """Create metrics directory if needed."""
    os.makedirs(METRICS_DIR, exist_ok=True)


def export_metrics_json(metrics: Dict[str, Any], run_id: str = None) -> str:
    """
    Export metrics to JSON file.
    
    Args:
        metrics: Metrics dictionary
        run_id: Optional run ID for filename
    
    Returns:
        Path to exported file
    """
    _ensure_metrics_dir()
    
    if not run_id:
        run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    filepath = os.path.join(METRICS_DIR, f"metrics_{run_id}.json")
    
    try:
        with open(filepath, "w") as f:
            json.dump(metrics, f, indent=2)
        logger.info(f"Metrics exported to {filepath}")
        return filepath
    except Exception as e:
        logger.error(f"Failed to export metrics: {e}")
        return None


def export_metrics_csv(metrics: Dict[str, Any], run_id: str = None) -> str:
    """
    Export metrics summary to CSV file.
    
    Args:
        metrics: Metrics dictionary
        run_id: Optional run ID
    
    Returns:
        Path to exported file
    """
    _ensure_metrics_dir()
    
    if not run_id:
        run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    filepath = os.path.join(METRICS_DIR, f"metrics_{run_id}.csv")
    
    try:
        # Flatten metrics for CSV
        rows = []
        
        # Summary row
        summary = {
            "timestamp": metrics.get("timestamp"),
            "metric_type": "summary"
        }
        summary.update({k: v for k, v in metrics.items() if k not in ["phases", "errors"]})
        rows.append(summary)
        
        # Phase rows
        for phase_name, phase_data in metrics.get("phases", {}).items():
            row = {
                "timestamp": metrics.get("timestamp"),
                "metric_type": "phase",
                "phase": phase_name,
                **phase_data
            }
            rows.append(row)
        
        # Error rows
        for error in metrics.get("errors", []):
            row = {
                "timestamp": error.get("timestamp"),
                "metric_type": "error",
                "error_type": error.get("type"),
                "error_message": error.get("message")
            }
            rows.append(row)
        
        # Write CSV
        if rows:
            keys = set()
            for row in rows:
                keys.update(row.keys())
            keys = sorted(list(keys))
            
            with open(filepath, "w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=keys)
                writer.writeheader()
                writer.writerows(rows)
            
            logger.info(f"CSV metrics exported to {filepath}")
            return filepath
    
    except Exception as e:
        logger.error(f"Failed to export CSV metrics: {e}")
        return None


def get_metrics_summary() -> Dict[str, Any]:
    """
    Get summary of all collected metrics across all runs.
    
    Returns:
        Summary statistics
    """
    _ensure_metrics_dir()
    
    json_files = [f for f in os.listdir(METRICS_DIR) if f.startswith("metrics_") and f.endswith(".json")]
    
    if not json_files:
        return {"total_runs": 0}
    
    total_runtime = 0
    total_errors = 0
    total_threats = 0
    run_count = len(json_files)
    
    for filename in json_files:
        try:
            with open(os.path.join(METRICS_DIR, filename), "r") as f:
                metrics = json.load(f)
                
                for phase in metrics.get("phases", {}).values():
                    total_runtime += phase.get("elapsed_seconds", 0)
                
                total_errors += len(metrics.get("errors", []))
                total_threats += metrics.get("threat_count", 0)
        except Exception as e:
            logger.warning(f"Failed to read {filename}: {e}")
    
    return {
        "total_runs": run_count,
        "total_runtime_seconds": round(total_runtime, 2),
        "average_runtime_seconds": round(total_runtime / run_count, 2) if run_count > 0 else 0,
        "total_errors": total_errors,
        "total_threats_generated": total_threats
    }
