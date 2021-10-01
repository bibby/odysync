import os
import logging


default_log_level = logging.INFO
log_level = default_log_level
user_log_level = os.environ.get('LOG_LEVEL', None)
if user_log_level:
    if not isinstance(user_log_level, int):
        level = getattr(logging, str(user_log_level).upper(), None)
        if isinstance(level, int):
            log_level = level


log = logging.getLogger('odysync')
handler = logging.StreamHandler()
handler.setLevel(log_level)
log.setLevel(log_level)
log.addHandler(handler)
print("Log Level: " + str(log_level))

