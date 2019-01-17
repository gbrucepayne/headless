#!/usr/bin/env python
"""
Functions and classes useful for operating a headless device e.g. Raspberry Pi or Intelligent Edge Gateway
"""
__version__ = "1.0.0"

import time
import inspect
import logging
from logging.handlers import RotatingFileHandler
import threading
import serial.tools.list_ports


def is_logger(log):
    """Returns True if the object is a Logger"""
    return isinstance(log, logging.Logger)


def is_log_handler(logger, handler):
    """
    Determines if a given (named) Handler is assigned to a Logger.

    :param logging.Logger logger: a logger object
    :param logging.Handler handler: a handler object
    :returns: result
    :rtype: bool
    """
    found = False
    if handler.name is None:
        logger.warning("Request to validate Handler with no name assigned to Logger may result in duplicate Handlers")
    for h in logger.handlers:
        if h.name == handler.name:
            found = True
            break
    return found


def get_caller_name(depth=2, mod=True, cls=False, mth=False):
    """
    Gets the name of the calling module/class/method with format [module][.class][.method]

    :param int depth: the depth of the caller if passing through multiple methods (optional)
    :param bool mod: include module in name (optional)
    :param bool cls: include class in name (optional)
    :param bool mth: include method in name (optional)
    :return: caller name as [module][.class][.method]
    :rtype: str
    """
    stack = inspect.stack()
    start = 0 + depth
    if len(stack) < start + 1:
        return ''
    parent_frame = stack[start][0]
    name = []
    module = inspect.getmodule(parent_frame)
    if module and mod:
        name.append(module.__name__)
    if cls and 'self' in parent_frame.f_locals:
        name.append(parent_frame.f_locals['self'].__class__.__name__)
    if mth:
        codename = parent_frame.f_code.co_name
        if codename != '<module>':
            name.append(codename)
    del parent_frame, stack
    return '.'.join(name)


def get_wrapping_logger(name=None, filename=None, file_size=5, debug=False):
    """
    Initializes logging to console, and optionally a wrapping CSV formatted file of defined size.
    Default logging level is INFO.
    Timestamps are GMT/UTC/Zulu.

    :param str name: name of the logger (optional, if None will use name of calling module)
    :param str filename: the name of the file if writing to a file (optional, no file created if not specified)
    :param int file_size: the max size of the file in megabytes, before wrapping occurs (optional)
    :param bool debug: enable DEBUG logging (default INFO)
    :return: a configured Logger
    :rtype: logging.Logger
    """
    FORMAT = ('%(asctime)s.%(msecs)03dZ,[%(levelname)s],(%(threadName)-10s),'
              '%(module)s.%(funcName)s:%(lineno)d,%(message)s')
    log_formatter = logging.Formatter(fmt=FORMAT,
                                      datefmt='%Y-%m-%dT%H:%M:%S')
    log_formatter.converter = time.gmtime

    if name is None:
        name = get_caller_name()
    logger = logging.getLogger(name)

    if debug or logger.getEffectiveLevel() == logging.DEBUG:
        log_lvl = logging.DEBUG
    else:
        log_lvl = logging.INFO
    logger.setLevel(log_lvl)

    if filename is not None:
        # TODO: validate that logfile is a valid path/filename
        file_handler = RotatingFileHandler(filename=filename, mode='a', maxBytes=file_size * 1024 * 1024,
                                           backupCount=2, encoding=None, delay=0)
        file_handler.name = name + '_file_handler'
        file_handler.setFormatter(log_formatter)
        file_handler.setLevel(log_lvl)
        if not is_log_handler(logger, file_handler):
            logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.name = name + '_console_handler'
    console_handler.setFormatter(log_formatter)
    console_handler.setLevel(log_lvl)
    if not is_log_handler(logger, console_handler):
        logger.addHandler(console_handler)
    return logger


class RepeatingTimer(threading.Thread):
    """
    A Thread class that repeats function calls like a Timer but can be stopped, restarted and change interval.
    Thread can be automatically started on initialization, but timer must be started explicitly with ``start_timer()``.
    Uses ``logging`` which is set up based on the name of the calling module.
    """

    def __init__(self, seconds, callback, name=None, sleep_chunk=0.25, auto_start=True, defer=True, tick_log=False,
                 **kwargs):
        """
        :param function callback: the callback to execute each timer expiry
        :param int seconds: interval for timer repeat
        :param str name: used to identify the thread
        :param float sleep_chunk: tick cycle in seconds between state checks
        :param bool auto_start: automatically start the thread on initialization
        :param bool defer: wait until the first timer expiry before calling back
        :param bool tick_log: optional verbose debug logging of tick count (watch countdown)
        :param dict kwargs: optional keyword/value arguments to pass into the callback
        """
        threading.Thread.__init__(self)
        self.log = get_wrapping_logger(name=get_caller_name(), debug=tick_log)
        if name is not None:
            self.name = name
        else:
            self.name = str(callback) + "_timer_thread"
        self.interval = seconds
        if callback is None:
            error = "No callback specified for RepeatingTimer {}".format(self.name)
            raise ValueError("{}".format(error))
        self.callback = callback
        self.callback_kwargs = kwargs
        self.sleep_chunk = sleep_chunk
        self.defer = defer
        self.tick_log = tick_log
        self.terminate_event = threading.Event()
        self.start_event = threading.Event()
        self.reset_event = threading.Event()
        self.count = self.interval / self.sleep_chunk
        if auto_start:
            self.start()

    def run(self):
        """Counts down the interval, checking every ``sleep_chunk`` the desired state."""
        while not self.terminate_event.is_set():
            while self.count > 0 and self.start_event.is_set() and self.interval > 0:
                if self.tick_log:
                    if (self.count * self.sleep_chunk - int(self.count * self.sleep_chunk)) == 0.0:
                        self.log.debug("{name} countdown: {tick} ({interval}s @ step {step:.2f}s)"
                                       .format(name=self.name, tick=self.count,
                                               interval=self.interval, step=self.sleep_chunk))
                if self.reset_event.wait(self.sleep_chunk):
                    self.reset_event.clear()
                    self.count = self.interval / self.sleep_chunk
                self.count -= 1
                if self.count <= 0:
                    self._callback()
                    self.count = self.interval / self.sleep_chunk

    def _callback(self):
        # TODO: add positional args handling
        self.callback(**self.callback_kwargs)

    def start_timer(self):
        """Initially start the repeating timer, or continue from where stopped."""
        self.log.info("{} timer started ({} seconds)".format(self.name, self.interval))
        if not self.defer and self.interval > 0:
            self._callback()
        self.start_event.set()

    def stop_timer(self):
        """Stop the repeating timer."""
        self.log.info("{} timer stopped ({} seconds)".format(self.name, self.interval))
        self.start_event.clear()
        # self.count = self.interval / self.sleep_chunk

    def restart_timer(self):
        """Restart the repeating timer (e.g. after an interval change)."""
        self.log.info("{} timer restarted ({} seconds)".format(self.name, self.interval))
        self.count = self.interval / self.sleep_chunk
        if not self.defer and self.interval > 0:
            self._callback()
        if self.start_event.is_set():
            self.reset_event.set()
        else:
            self.start_event.set()

    def change_interval(self, seconds):
        """
        Change the timer interval and restart it.

        :param int seconds: new timer value
        """
        if isinstance(seconds, int) and seconds > 0:
            self.log.info("{} timer interval changed (old:{} s new:{} s)".format(self.name, self.interval, seconds))
            self.interval = seconds
            self.restart_timer()
        else:
            self.log.error("Invalid interval requested...must be integer > 0")

    def terminate(self):
        """Terminate the timer. (Cannot be restarted)"""
        self.stop_timer()
        self.terminate_event.set()
        self.log.info(self.name + " timer terminated")


def get_serial_ports():
    """Returns a list of serial ports found on the system."""
    ports_detailed = [tuple(port) for port in list(serial.tools.list_ports.comports())]
    ports = []
    for port in ports_detailed:
        ports.append(port[0])
    return ports


def validate_serial_port(target):
    """
    Validates a given serial port as available on the host.

    :param target: (str) the target port name e.g. '/dev/ttyUSB0'
    :returns: result, details
    :rtype: bool, str
    """
    found = False
    detail = ""
    ser_ports = [tuple(port) for port in list(serial.tools.list_ports.comports())]
    for port in ser_ports:
        if target == port[0]:
            found = True
            if 'USB VID:PID=0403:6001' in port[2] and target == port[0]:
                detail = "Serial FTDI FT232 (RS485/RS422/RS232) on {port}".format(port=port[0])
            elif 'USB VID:PID=067B:2303' in port[2] and target == port[0]:
                detail = "Serial Prolific PL2303 (RS232) on {port}".format(port=port[0])
            elif target == port[0]:
                usb_id = str(port[2])
                detail = "Serial vendor/device {id} on {port}".format(id=usb_id, port=port[0])
    if not found and len(ser_ports) > 0:
        for port in ser_ports:
            detail += ", {}".format(port[0]) if len(detail) > 0 else " {}".format(port[0])
        detail = "Available ports:" + detail
    return found, detail


def get_net_interfaces():
    """
    Returns a list of available network interfaces found on the system.

    :returns: list of interfaces
    :rtype: list
    """
    import netifaces
    return netifaces.interfaces()


def get_ip_address(interface):
    """
    Gets the IP address of a particular interface, e.g. eth0 or wlan0 or ppp0

    :param str interface: name of the interface e.g. eth0
    :return: IPv4 address
    :rtype: str
    """
    try:
        import netifaces
        detail = netifaces.ifaddresses(interface)
        if netifaces.AF_INET in detail:
            ip = detail[netifaces.AF_INET][0]['addr']
        else:
            ip = 'unavailable'
    except ImportError:
        import socket
        import fcntl
        import struct
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        ip = socket.inet_ntoa(fcntl.ioctl(s.fileno(), 0x8915, struct.pack('256s', interface[:15]))[20:24])
    return ip
