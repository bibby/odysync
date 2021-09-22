import os
import logging

log = logging.getLogger('odysync')
log.addHandler(logging.StreamHandler())
log.setLevel(os.environ.get('LOG_LEVEL', logging.DEBUG))
