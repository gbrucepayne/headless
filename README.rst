headless
========

A set of functions and Classes useful for headless operation on IoT gateways such as:

   * ``get_wrapping_logger``: creates a log that outputs to console as well as an optional wrapping file of fixed size and backup count.
   * ``RepeatingTimer``: a thread that periodically calls back to a defined function on a repeating interval and can be started, stopped, restarted and changed.
   * ``validate_serial_port``: confirms the presence of a specified COM/TTY port resource
   * ``get_ip_address``: returns the IP address of a particular network interface on the host
