"""__author__ = 'Igorg'
"""

import logging
import logging.handlers
import os


class TestLogger(object):

    def __init__(self, file_name, level=logging.DEBUG, max_file_size=1*1024*1024, backup_count=50):
        """Constructor.
            level -- one of the predefined levels, theirs descending order is:'CRITICAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG'.
            Records with level not less than defined will be added to the log file.
            max_file_size -- max File size in bytes, the file will be renamed if it size over maxFileSize. Type:float
            backup_count -- max files number per project to roll. Type:int
        """
        self.logger = logging.getLogger(file_name)
        dir = r'/var/tmp/CloudLog'
        if not os.path.exists(dir):
            os.makedirs(dir)

        file_ext = '.log.csv'
        file_path = os.path.join(dir, file_name + file_ext)
        self.hdlr = None
        try:
            self.hdlr = logging.handlers.RotatingFileHandler(file_path, maxBytes=max_file_size, backupCount=backup_count)
        except IOError, err:
            print err
            raise

        formatter = logging.Formatter('%(asctime)s, %(message)s', '%d/%m/%Y, %H:%M:%S')
        self.hdlr.setFormatter(formatter)
        self.logger.addHandler(self.hdlr)
        self.logger.setLevel(level)

    def __enter__(self):
        return self

    def __del__(self):
        """Destructor.
        """
        self.logger.removeHandler(self.hdlr)

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.logger.removeHandler(self.hdlr)

    def set_level(self, level):
        """
        Set logging level
        :param level: one of the predefined levels, theirs descending order is:'CRITICAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG'.
        """
        self.logger.setLevel(level)

    def remove_handler(self):
        self.logger.removeHandler(self.hdlr)

    def debug(self, msg, *args, **kwargs):
        """Add record the object's when the level is 'DEBUG'.
        """
        self.logger.debug(msg, *args, **kwargs)

    def info(self, msg, *args, **kwargs):
        """Add record when the object's level is 'INFO' or lower.
        """
        self.logger.info(msg, *args, **kwargs)

    def warning(self, msg, *args, **kwargs):
        """Add record when the object's level is 'WARNING' or lower.
        """
        self.logger.warning(msg, *args, **kwargs)

    def error(self, msg, *args, **kwargs):
        """Add record when the object's level is 'ERROR' or lower.
        """
        self.logger.error(msg, *args, **kwargs)

    def critical(self, msg, *args, **kwargs):
        """Add record when the object's level is 'CRITICAL' or lower.
        """
        self.logger.critical(msg, *args, **kwargs)
