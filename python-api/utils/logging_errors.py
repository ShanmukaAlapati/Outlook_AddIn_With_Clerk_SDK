import os
from datetime import datetime, timedelta
from typing import Optional, Literal
from pathlib import Path
import threading

LOG_DIR = "logs"

# Thread lock for safe concurrent writes
_log_lock = threading.Lock()


class TimeSlotLogger:
    """
    Enterprise logger with 3-hour time slot rotation.
    Creates new log files every 3 hours automatically.
    """
    
    def __init__(self, log_dir: str = LOG_DIR):
        """
        Initialize the TimeSlotLogger.
        
        What it does:
        - Creates the logs directory if it doesn't exist
        - Initializes tracking dictionaries for separate info and browser log files
        - Sets up slot tracking to manage when to rotate to new files
        
        Args:
            log_dir: Directory path where log files will be stored
        """
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        # Separate tracking for each log type
        self._current_slot_files: dict[str, Optional[str]] = {
            "info": None,
            "browser": None
        }
        self._current_slot_starts: dict[str, Optional[datetime]] = {
            "info": None,
            "browser": None
        }
    
    def _get_time_slot(self, now: datetime) -> tuple[datetime, datetime]:
        """
        Calculate the 3-hour time slot for a given datetime.
        
        What it does:
        - Takes any datetime and rounds it down to the nearest 3-hour boundary
        - Calculates the start and end times of the current 3-hour slot
        - Example: 13:45 becomes slot 12:00-15:00, 08:30 becomes 06:00-09:00
        
        Slots: 00-03, 03-06, 06-09, 09-12, 12-15, 15-18, 18-21, 21-24
        
        Args:
            now: The datetime to calculate the slot for
        
        Returns:
            (slot_start, slot_end) tuple of datetime objects
        """
        hour = now.hour
        slot_start_hour = (hour // 3) * 3  # Round down to nearest 3-hour boundary
        
        slot_start = now.replace(hour=slot_start_hour, minute=0, second=0, microsecond=0)
        slot_end = slot_start + timedelta(hours=3)
        
        return slot_start, slot_end
    
    def _get_slot_filename(
        self, 
        now: datetime, 
        log_type: Literal["info", "browser"] = "info"
    ) -> str:
        """
        Generate filename in format: logging_info_16-02-2026_00hr-03hr.txt
        
        What it does:
        - Calculates the current 3-hour time slot for the given datetime
        - Formats date as DD-MM-YYYY
        - Formats time slot as HHhr-HHhr (e.g., 12hr-15hr)
        - Combines log_type, date, and time slot into standardized filename
        - Returns full path including logs directory
        
        Args:
            now: Current datetime to generate filename for
            log_type: Type of log file - "info" for application logs, "browser" for console logs
        
        Returns:
            Full path string to the log file (e.g., "logs/logging_info_16-02-2026_00hr-03hr.txt")
        """
        slot_start, slot_end = self._get_time_slot(now)
        
        date_str = slot_start.strftime("%d-%m-%Y")
        start_hour = slot_start.strftime("%H")
        end_hour = slot_end.strftime("%H")
        
        filename = f"logging_{log_type}_{date_str}_{start_hour}hr-{end_hour}hr.txt"
        return str(self.log_dir / filename)
    
    def _should_rotate(self, now: datetime, log_type: str) -> bool:
        """
        Check if we need to rotate to a new log file.
        
        What it does:
        - Returns True if this is the first log (no current slot start time)
        - Calculates if the current time has moved past the end of the 3-hour slot
        - Triggers rotation when moving from one 3-hour slot to the next
        - Each log_type (info/browser) is tracked independently
        
        Args:
            now: Current datetime to check
            log_type: Which log type to check rotation for ("info" or "browser")
        
        Returns:
            True if a new log file should be created, False if current file is still valid
        """
        if self._current_slot_starts[log_type] is None:
            return True
        
        _, slot_end = self._get_time_slot(self._current_slot_starts[log_type])
        return now >= slot_end
    
    def write_log(
        self, 
        message: str, 
        level: Literal["INFO", "WARNING", "ERROR", "DEBUG"] = "INFO",
        log_type: Literal["info", "browser"] = "info"
    ) -> None:
        """
        Write a timestamped log message to the appropriate 3-hour slot file.
        
        What it does:
        - Checks if log file needs rotation (new 3-hour slot)
        - Creates new log file with appropriate filename if rotation needed
        - Formats log message with timestamp and severity level
        - Appends log entry to the correct file in thread-safe manner
        - Handles both "info" (application) and "browser" (console) logs separately
        
        Args:
            message: The actual log message content to write
            level: Severity level - INFO, WARNING, ERROR, or DEBUG
            log_type: Destination file type - "info" for app logs, "browser" for console logs
        """
        now = datetime.now()
        
        with _log_lock:  # Thread-safe file operations
            # Check if we need to rotate to new file
            if self._should_rotate(now, log_type):
                self._current_slot_starts[log_type] = now
                self._current_slot_files[log_type] = self._get_slot_filename(now, log_type)
            
            # Format log line
            timestamp = now.strftime("%Y-%m-%d %H:%M:%S")
            line = f"[{timestamp}] [{level}] {message}\n"
            
            # Append to current slot file
            with open(self._current_slot_files[log_type], "a", encoding="utf-8") as f:
                f.write(line)
    
    def write_console_log(self, line: str, level: str = "INFO") -> None:
        """
        Write browser console log to dedicated browser log file.
        
        What it does:
        - Wrapper function for browser console logs
        - Automatically routes log to "browser" log file type
        - Calls write_log() with log_type="browser" parameter
        - Maintains separate logging_browser_*.txt files
        
        Args:
            line: Browser console log message content
            level: Log severity level (default INFO)
        """
        self.write_log(line, level=level, log_type="browser")
    
    # ============= COMMENTED OUT: AUTOMATIC CLEANUP =============
    # def cleanup_old_logs(self, days_to_keep: int = 7) -> int:
    #     """
    #     Delete log files older than specified days.
    #     
    #     What it does:
    #     - Scans the logs directory for all logging_*.txt files
    #     - Checks each file's modification timestamp
    #     - Deletes files older than the retention period (days_to_keep)
    #     - Returns count of deleted files for reporting
    #     
    #     Args:
    #         days_to_keep: Number of days to retain logs (default 7)
    #     
    #     Returns:
    #         Number of files deleted
    #     """
    #     cutoff_date = datetime.now() - timedelta(days=days_to_keep)
    #     deleted_count = 0
    #     
    #     for log_file in self.log_dir.glob("logging_*.txt"):
    #         # Check file modification time
    #         if log_file.stat().st_mtime < cutoff_date.timestamp():
    #             log_file.unlink()
    #             deleted_count += 1
    #             print(f"Deleted old log: {log_file.name}")
    #     
    #     return deleted_count
    
    # ============= COMMENTED OUT: QUERY CAPABILITY =============
    # def get_logs_for_date(self, date: datetime, log_type: str = "info") -> list[str]:
    #     """
    #     Retrieve all log files for a specific date.
    #     
    #     What it does:
    #     - Formats the target date as DD-MM-YYYY
    #     - Searches for all log files matching that date pattern
    #     - Returns sorted list of file paths for that specific date
    #     - Useful for retrieving all 3-hour slot files from a given day
    #     
    #     Args:
    #         date: Target date to retrieve logs for
    #         log_type: Type of logs to retrieve ("info" or "browser")
    #     
    #     Returns:
    #         List of matching log file paths (sorted chronologically)
    #     """
    #     date_str = date.strftime("%d-%m-%Y")
    #     pattern = f"logging_{log_type}_{date_str}_*.txt"
    #     
    #     matching_files = list(self.log_dir.glob(pattern))
    #     return [str(f) for f in sorted(matching_files)]


# Global logger instance (singleton pattern)
_logger_instance: Optional[TimeSlotLogger] = None


def get_logger() -> TimeSlotLogger:
    """
    Get or create the global logger instance.
    
    What it does:
    - Implements singleton pattern - ensures only one logger instance exists
    - Creates new TimeSlotLogger on first call
    - Returns existing instance on subsequent calls
    - Prevents multiple logger instances from conflicting
    
    Returns:
        The shared TimeSlotLogger instance
    """
    global _logger_instance
    if _logger_instance is None:
        _logger_instance = TimeSlotLogger()
    return _logger_instance


# Convenience functions (backward compatible with your old code)
def write_log(message: str, level: str = "INFO") -> None:
    """
    Append a timestamped message to the current 3-hour slot log file.
    
    What it does:
    - Simple wrapper function for application logging
    - Gets the global logger instance
    - Writes to logging_info_DD-MM-YYYY_HHhr-HHhr.txt files
    - Automatically handles 3-hour slot rotation
    - Thread-safe for concurrent logging
    
    Usage:
        write_log("User logged in successfully")
        write_log("Database connection failed", level="ERROR")
    
    Args:
        message: Log message content
        level: Log severity (INFO, WARNING, ERROR, DEBUG) - default is INFO
    """
    logger = get_logger()
    logger.write_log(message, level=level, log_type="info")


def write_console_log(line: str, level: str = "INFO") -> None:
    """
    Append browser console log to separate browser log file.
    
    What it does:
    - Simple wrapper function for browser console logging
    - Gets the global logger instance
    - Writes to logging_browser_DD-MM-YYYY_HHhr-HHhr.txt files (separate from app logs)
    - Automatically handles 3-hour slot rotation
    - Thread-safe for concurrent logging
    
    Usage:
        write_console_log("Page loaded successfully")
        write_console_log("JavaScript error occurred", level="ERROR")
    
    Args:
        line: Browser console message content
        level: Log severity (INFO, WARNING, ERROR, DEBUG) - default is INFO
    """
    logger = get_logger()
    logger.write_console_log(line, level=level)


# ============= COMMENTED OUT: CLEANUP FUNCTION =============
# def cleanup_old_logs(days: int = 7) -> int:
#     """
#     Remove log files older than specified days.
#     
#     What it does:
#     - Convenience function for cleaning up old log files
#     - Calls the cleanup_old_logs method on the global logger instance
#     - Deletes both info and browser log files older than retention period
#     - Helps manage disk space by removing outdated logs
#     
#     Usage:
#         deleted_count = cleanup_old_logs(days=30)  # Keep last 30 days
#         print(f"Removed {deleted_count} old log files")
#     
#     Args:
#         days: Number of days to keep logs (default 7)
#     
#     Returns:
#         Count of deleted files
#     """
#     logger = get_logger()
#     return logger.cleanup_old_logs(days_to_keep=days)


# ============= USAGE EXAMPLES =============

if __name__ == "__main__":
    # Example 1: Application logs -> logging_info_16-02-2026_00hr-03hr.txt
    write_log("Application started successfully")
    write_log("User authentication completed", level="INFO")
    write_log("Database connection timeout", level="WARNING")
    write_log("Critical: Payment processing failed", level="ERROR")
    
    # Example 2: Browser console logs -> logging_browser_16-02-2026_00hr-03hr.txt
    write_console_log("Page loaded in 2.3 seconds")
    write_console_log("Warning: Deprecated API used", level="WARNING")
    write_console_log("Error: Failed to fetch user data", level="ERROR")
    
    # Example 3: Mixed logging - goes to separate files
    write_log("Processing email attachment", level="INFO")
    write_console_log("Button clicked: Submit")
    write_log("Email attachment saved", level="INFO")
    write_console_log("Upload progress: 75%")
    
    # Example 4: Simulate logging across time slots
    print("\n=== Simulating 3-hour slot rotation ===")
    logger = get_logger()
    for hour in [0, 3, 6, 9, 12, 15, 18, 21]:
        test_time = datetime.now().replace(hour=hour, minute=0)
        info_file = logger._get_slot_filename(test_time, "info")
        browser_file = logger._get_slot_filename(test_time, "browser")
        print(f"Hour {hour:02d}:00 ->")
        print(f"  Info: {Path(info_file).name}")
        print(f"  Browser: {Path(browser_file).name}")






# import os
# from datetime import datetime

# LOG_DIR = "logs"
# LOG_FILE = "logs.txt"

# os.makedirs(LOG_DIR, exist_ok=True)

# def write_log(message: str) -> None:
#     """
#     Append a timestamped message to logs/logs.txt.
#     Creates the file if it does not exist.
#     """
#     log_path = os.path.join(LOG_DIR, LOG_FILE)
#     timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
#     line = f"[{timestamp}] {message}\n"
#     with open(log_path, "a", encoding="utf-8") as f:
#         f.write(line)


# BROWSER_LOG_FILE = os.path.join(LOG_DIR, "browser_console.txt")

# def write_console_log(line: str) -> None:
#   timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
#   with open(BROWSER_LOG_FILE, "a", encoding="utf-8") as f:
#     f.write(f"[{timestamp}] {line}\n")