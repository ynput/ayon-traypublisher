import io
import json
import logging
import os
import pprint
import re
import sys
import threading
import time
import traceback
from functools import wraps
from logging.handlers import RotatingFileHandler

# ================================================
# Set up logger
# ================================================

# Dynamically determine addon name
try:
    # Get addon name from the module path
    module_path = os.path.dirname(__file__)
    ADDON_NAME = os.path.basename(module_path)
except Exception:
    logging.error(traceback.format_exc())
    raise Exception(
        "Failed to determine addon's name, is this logger in the addon root?"
    )

# Use the env var by default if its defined.
AYON_LOCAL_SANDBOX = os.environ.get("AYON_LOCAL_SANDBOX")
if AYON_LOCAL_SANDBOX:
    # Create a dedicated logs directory
    log_dir = os.path.expanduser(
        os.path.expandvars(f"{AYON_LOCAL_SANDBOX}/logs")
    ).replace("\\", "/")
else:
    # Fallback to default
    log_dir = os.path.expanduser("~/.ayon/logs").replace("\\", "/")

# Create log directory if it doesn't exist
try:
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
except Exception:
    pass  # Continue even if directory creation fails

# ================================================
# Log rotation settings
# ================================================

LOG_ROTATE_MAX_BYTES = 25 * 1024 * 1024  # Rotate at session start only when file >= this
LOG_RETENTION_DAYS = 62
LOG_ROTATE_BACKUP_DIGITS = 3
# Handler maxBytes set high so we never rotate mid-session; we only roll at startup when size >= LOG_ROTATE_MAX_BYTES
LOG_HANDLER_MAX_BYTES = 2**30  # 1 GiB


# Get a logger with a unique name
def get_logger(name):
    return logging.getLogger(f"ayon.{name}")


# The main logger, used for all logging
log = logging.getLogger(f"ayon.{ADDON_NAME}")

# Determine log level
log_level = os.getenv("AYON_LOG_LEVEL")
ayon_debug = os.getenv("AYON_DEBUG", False)
if ayon_debug:
    log.setLevel(logging.DEBUG)
else:
    if log_level:
        log.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    else:
        log.setLevel(logging.INFO)

# Clear existing handlers
for handler in log.handlers[:]:
    log.removeHandler(handler)

# Prevent interference from parent loggers
log.propagate = False


# Rotating file handler: numbered files before extension (e.g. ayon_harmony_debug001.log)
class NumberedRotatingFileHandler(RotatingFileHandler):
    def doRollover(self):
        if self.stream:
            self.stream.close()
            self.stream = None
        dname, fname = os.path.split(self.baseFilename)
        base_no_ext, ext = os.path.splitext(fname)
        pad = LOG_ROTATE_BACKUP_DIGITS
        pattern = re.compile(
            r"^" + re.escape(base_no_ext) + r"(\d+)" + re.escape(ext) + r"$"
        )
        numbered = []
        for name in os.listdir(dname):
            m = pattern.match(name)
            if m:
                numbered.append((int(m.group(1)), name))
        numbered.sort(key=lambda x: x[0], reverse=True)
        for num, name in numbered:
            if num >= 10**pad - 1:
                continue
            src = os.path.join(dname, name)
            dst = os.path.join(
                dname, f"{base_no_ext}{str(num + 1).zfill(pad)}{ext}"
            )
            if os.path.exists(dst):
                os.remove(dst)
            os.rename(src, dst)
        current = os.path.join(dname, fname)
        if os.path.exists(current):
            first_rotated = os.path.join(dname, f"{base_no_ext}{'1'.zfill(pad)}{ext}")
            if os.path.exists(first_rotated):
                os.remove(first_rotated)
            os.rename(current, first_rotated)
        if not self.delay:
            self.stream = self._open()


# Define a safe handler class that won't crash on None streams
class SafeStreamHandler(logging.StreamHandler):
    """
    A logging handler that safely handles None streams by using a StringIO fallback.
    """

    def __init__(self, stream=None):
        """
        Initialize the handler with a stream or a StringIO fallback.
        Args:
            stream (io.TextIOBase, optional): The stream to write logs to.
                If None, a StringIO fallback will be used.
        """
        self.fallback_stream = io.StringIO()
        super().__init__(stream or self.fallback_stream)

    def emit(self, record):
        """
        Emit a record to the stream, ensuring the stream is valid.
        Args:
            record (logging.LogRecord): The log record to emit.
        """
        try:
            if self.stream is None or not hasattr(self.stream, "write"):
                self.stream = self.fallback_stream
            super().emit(record)
            self.flush()
        except Exception:
            pass


# Add file handler only if AYON_DEBUG is enabled
if ayon_debug:
    try:
        file_path = os.path.join(log_dir, f"{ADDON_NAME}_debug.log")
        log_prefix = f"{ADDON_NAME}_debug"  # matches .log and 001.log, 002.log, ...

        def _delete_old_logs():
            try:
                cutoff = time.time() - (LOG_RETENTION_DAYS * 86400)
                for name in os.listdir(log_dir):
                    if name.startswith(log_prefix):
                        path = os.path.join(log_dir, name)
                        if (
                            os.path.isfile(path)
                            and os.path.getmtime(path) < cutoff
                        ):
                            os.remove(path)
            except Exception:
                pass

        threading.Thread(target=_delete_old_logs, daemon=True).start()

        file_handler = NumberedRotatingFileHandler(
            file_path,
            maxBytes=LOG_HANDLER_MAX_BYTES,
            backupCount=999,
        )
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.DEBUG)
        if os.path.exists(file_path) and os.path.getsize(file_path) >= LOG_ROTATE_MAX_BYTES:
            file_handler.doRollover()
        log.addHandler(file_handler)
    except Exception:
        print(f"Failed to create log file in {log_dir}")

# Add console handler with explicit stream and error handling
try:
    stream_handler = SafeStreamHandler(stream=sys.stderr)
    stream_handler.setFormatter(
        logging.Formatter("%(name)s - %(levelname)s - %(message)s")
    )
    stream_handler.setLevel(logging.DEBUG if ayon_debug else log.level)
    log.addHandler(stream_handler)
except Exception:
    print("Failed to create console log handler")

# ================================================
# Apply safe wrappers to all logging methods
# ================================================


# Create safe logging methods that won't crash
def safe_log(func):
    @wraps(func)
    def wrapper(msg, *args, **kwargs):
        try:
            return func(msg, *args, **kwargs)
        except Exception:
            # Last resort - print directly to console
            print(f"SAFE LOG: {msg}")

    return wrapper


log.debug = safe_log(log.debug)
log.info = safe_log(log.info)
log.warning = safe_log(log.warning)
log.error = safe_log(log.error)
log.critical = safe_log(log.critical)

# Print confirmation that logger is initialized
print(f"AYON {ADDON_NAME} logger initialized successfully")

# ================================================
# Log formatting functions
# ================================================


# format log function to handle large data structures in debug logs
def format_log(data, max_length=5000):
    """
    Format data for logging, truncating if necessary.
    Args:
        data (any): The data to format.
        max_length (int): Maximum length of the formatted string.
    Returns:
        str: Formatted string representation of the data.
    """
    if not isinstance(data, (dict, list)):
        return str(data)

    try:
        # Try JSON formatting first (for JS/JSON data)

        formatted = json.dumps(data, indent=2, sort_keys=True)
    except (TypeError, ValueError):
        # Fall back to pprint for Python objects that aren't JSON serializable

        formatted = pprint.pformat(data, indent=2, width=100)

    if len(formatted) > max_length:
        return (
            formatted[:max_length]
            + f"... (truncated, {len(formatted)} bytes total)"
        )
    return formatted
