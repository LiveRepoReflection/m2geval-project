import logging
import os
import datetime
import sys

def setup_logger(model_name, log_level=logging.INFO):
    """
    Sets up a logger that writes to a file and the console.

    The log file will be created in a directory structure based on the project root:
    <project_root>/log/<model_name>/<timestamp>/inference.log
    """
    # Create a logger for the given model name
    if log_level == logging.INFO:
        log_name = "info"
    elif log_level == logging.ERROR:
        log_name = "error"
    elif log_level == logging.DEBUG:
        log_name = "debug"
    else:
        log_name = "unknown"
    logger_name = f"{model_name}_{log_name}"
    logger = logging.getLogger(logger_name)
    logger.setLevel(log_level)

    # Prevent adding multiple handlers to the same logger
    if logger.hasHandlers():
        return logger

    # --- File Handler ---
    # Determine project root to make path creation robust.
    # This assumes logger.py is in <project_root>/src/utils/
    # project_root=./LLM-codegen
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    

    # Create a unique log directory for each run
    current_time = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    log_dir = os.path.join(project_root, 'log', model_name)
    os.makedirs(log_dir, exist_ok=True)
    
    # Create a file handler to write logs to a file
    log_file = os.path.join(log_dir, f"{current_time}-{log_name}.log")
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(log_level)

    # --- Console Handler ---
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)

    # --- Formatter ---
    # Create a formatter and set it for both handlers
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    # Add handlers to the logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger