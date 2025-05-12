#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  This file provides utilities like
#  logging and configuration options.
#  It now uses the config_manager singleton instead of a JSON file.
#

import logging
from utils.config_manager import config_manager

# For backward compatibility, provide CONF as a reference to config_manager
CONF = config_manager.get_config()
LOG = None


#
#   CONFIG
#
def init_config():
    """
    Initialize configuration from the config_manager singleton.
    This is kept for backward compatibility.

    :returns: None
    :rtype: None
    """
    global CONF
    # CONF is already initialized at the module level


def get_logger(name):
    """
    Retrieves a logger.

    :param name: The name of the logger
    :returns: The requested logger
    :rtype: logging.getLogger instance
    """
    logging.basicConfig(level=logging.ERROR)
    log = logging.getLogger(name)

    return log


def set_verbose(log):
    """
    Sets the logger logging level to INFO

    :param log: logging.getLogger instance
    :returns: None
    :rtype: None
    """
    log.setLevel(logging.INFO)


#
#   global initialization
#
init_config()
LOG = get_logger('VacuumCleanerSim')

# Get debug config from config_manager
debug_config = config_manager.get_debug_config()
if debug_config.get('verbose', False):
    set_verbose(LOG)
