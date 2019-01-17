import unittest
import headless
import logging
from headless import RepeatingTimer


class HeadlessTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.timer_callback_count = 0

    def test_is_logger(self):
        print("Testing is_logger")
        log = logging.getLogger()
        self.assertTrue(headless.is_logger(log))

    def test_get_caller_name(self):
        caller_name = headless.get_caller_name(depth=1, mod=True, cls=True, mth=True)
        print("Testing get_caller_name, called by: {}".format(caller_name))
        self.assertTrue(caller_name != '')

    def test_get_wrapping_logger(self):
        print("Testing get_wrapping_logger")
        log = headless.get_wrapping_logger()
        self.assertTrue(headless.is_logger(log))

    def test_RepeatingTimer_auto_start(self):
        CALLBACK_COUNT = 3
        TIMER_INTERVAL = 3
        print("Testing RepeatingTimer auto_start")
        timer_thread = RepeatingTimer(seconds=TIMER_INTERVAL, callback=self.cb_repeating_simple, name='test',
                                      defer=False, tick_log=True, **{'key1': 1, 'key2': 2})
        timer_thread.start_timer()
        while self.timer_callback_count < CALLBACK_COUNT:
            pass
        self.assertTrue(self.timer_callback_count == CALLBACK_COUNT)
        timer_thread.terminate()

    def cb_repeating_simple(self, **kwargs):
        self.timer_callback_count += 1
        print("Callback called {} times.  This time with kwargs:{}".format(self.timer_callback_count, kwargs))

    def test_RepeatingTimer_change_interval(self):
        CALLBACK_COUNT = 2
        TIMER_INTERVAL = 3
        print("Testing RepeatingTimer change_interval")
        timer_thread = RepeatingTimer(callback=self.cb_repeating_simple, seconds=TIMER_INTERVAL, name='test',
                                      defer=False, tick_log=True)
        timer_thread.start_timer()
        while self.timer_callback_count < CALLBACK_COUNT:
            pass
        print("\nChanging timer interval")
        self.timer_callback_count = 0
        timer_thread.change_interval(seconds=TIMER_INTERVAL*2)
        while self.timer_callback_count < CALLBACK_COUNT:
            pass
        self.assertTrue(self.timer_callback_count == CALLBACK_COUNT)
        timer_thread.terminate()

    def test_get_serial_ports_validate(self):
        print("Testing get_serial_ports")
        ports = headless.get_serial_ports()
        if len(ports) > 0:
            print("Serial ports found: {}".format(ports))
            port = ports[0]
            is_valid = headless.validate_serial_port(port)
            print("Validating serial port {} is {}"
                  .format(port, "valid" if is_valid else "invalid"))
            self.assertTrue(headless.validate_serial_port(ports[0])[0])
        else:
            print("No serial ports on this platform")

    def test_get_ip_address(self):
        print("Testing get_ip_address")
        netifs = headless.get_net_interfaces()
        if len(netifs) > 0:
            print("Network interfaces found: {}".format(netifs))
            netif = netifs[0]
            ip_addr = headless.get_ip_address(netif)
            print("Getting IP address of {}={}".format(netif, ip_addr))
            self.assertTrue(len(ip_addr) > 0)
        else:
            print("No network interfaces found")


def suite():
    suite = unittest.TestSuite()
    available_tests = unittest.defaultTestLoader.getTestCaseNames(HeadlessTestCase)
    tests = []
    if len(tests) > 0:
        for test in tests:
            for available_test in available_tests:
                if test in available_test:
                    suite.addTest(HeadlessTestCase(available_test))
    else:
        for available_test in available_tests:
            suite.addTest(HeadlessTestCase(available_test))
    return suite


if __name__ == '__main__':
    runner = unittest.TextTestRunner()
    runner.run(suite())
