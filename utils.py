import platform
import threading
import time


def convert_com_port(com_port):
    """Convert between Windows and Linux style serial ports.

    Args:
        com_port (str): Windows-style COM port (e.g. 'COM1')

    Returns:
        str: Appropriate port name for current platform
    """
    if platform.system() != "Windows":
        # Convert Windows-style COM port to Linux-style
        return f"/dev/ttyS{int(com_port[-1]) - 1}"
    return com_port


def pressure_alarm(low_threshold=10, high_threshold=30):
    """
    Decorator function that keeps track of pressure for safe operation. It will trigger
    an alarm if low or high pressure thresholds are exceeded. In the event of a trigger
    all shutoff valves will be closed and the process temperature will be taken down to 20C

    Args:
    low_threshold (int): lower pressure limit trigger value in case of working under vacuum
    high_theshold (int): higher pressure limit trigger value in case of a serious flow restriction event
    """

    def decorator(func):
        def wrapper(self, *args, **kwargs):
            # Flag to signal when the monitored method has finished
            finished = threading.Event()

            # Define a background function to monitor the pressure
            def monitor_pressure():
                while not finished.is_set():
                    # Read the pressure values
                    p_a, p_b = self.flowSMS.pressure_report()
                    # Check if either pressure exceeds the threshold
                    if p_a > high_threshold or p_b > high_threshold:
                        self.flowSMS.setpoints()  # Trigger adjustment if above threshold
                        print(
                            "!!!!!!!!!!!!!!HIGH PRESSURE ALARM!!!!!!!!!!!!!!\n!!!!!!!!!!!!!!HIGH PRESSURE ALARM!!!!!!!!!!!!!!\n",
                            "!!!!!!!!!!!!!!HIGH PRESSURE ALARM!!!!!!!!!!!!!!\n!!!!!!!!!!!!!!HIGH PRESSURE ALARM!!!!!!!!!!!!!!\n",
                            f"PRESSURE IN LINE A = {p_a} psia, PRESSURE IN LINE B = {p_b} psia.\n",
                            "CLOSING ALL SHUTOFF VALVES AND TAKING SYSTEM TO ROOM TEMPERATURE",
                        )
                        finished.set()  # Stop monitoring if alarm is triggered
                        self.setpoint_finish_experiment()
                        return
                    elif p_a < low_threshold or p_b < low_threshold:
                        self.flowSMS.setpoints()  # Trigger adjustment if above threshold
                        print(
                            "!!!!!!!!!!!!!!LOW PRESSURE ALARM!!!!!!!!!!!!!!\n!!!!!!!!!!!!!!LOW PRESSURE ALARM!!!!!!!!!!!!!!\n",
                            "!!!!!!!!!!!!!!LOW PRESSURE ALARM!!!!!!!!!!!!!!\n!!!!!!!!!!!!!!LOW PRESSURE ALARM!!!!!!!!!!!!!!\n",
                            f"PRESSURE IN LINE A = {p_a} psia, PRESSURE IN LINE B = {p_b} psia.\n",
                            "CLOSING ALL SHUTOFF VALVES AND TAKING SYSTEM TO ROOM TEMPERATURE",
                        )
                        finished.set()  # Stop monitoring if alarm is triggered
                        self.setpoint_finish_experiment()
                        return
                    time.sleep(1)  # Check every second

            # Start monitoring in a separate thread
            monitor_thread = threading.Thread(target=monitor_pressure)
            monitor_thread.start()

            try:
                # Execute the main function while monitoring continues in the background
                result = func(self, *args, **kwargs)
            finally:
                # Signal the monitor thread to stop after the function completes
                finished.set()
                monitor_thread.join()  # Ensure the monitor thread completes

            return result

        return wrapper

    return decorator
