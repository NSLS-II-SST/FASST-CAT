import minimalmodbus
import time
from datetime import datetime


class EuroSerial:
    """Class for controlling Eurotherm temperature controllers via serial communication."""

    def __init__(self, com_port, sub):
        """Initialize the temperature controller connection.

        Args:
            config (dict): Configuration dictionary containing connection settings
        """
        try:
            self.tmp_master = minimalmodbus.Instrument(com_port, sub)
        except Exception as e:
            print(f"Failed to initialize temperature controller: {e}")
            self.tmp_master = None

    def heating_event(self, rate_sp=None, sp=None):
        """Loops over actual temperature in an heating event until setpoint is reached"""
        print("Starting heating event:")
        try:
            print(f"Heating rate: {rate_sp} C/min")
            rate_sp = float(rate_sp)
            self.tmp_master.write_register(35, rate_sp, 1)
        except:
            rate_sp = None
        try:
            print(f"Setpoint: {sp} C")
            sp = float(sp)
            self.tmp_master.write_register(24, sp, 1)
        except:
            sp = None
        while True:
            try:
                temp_tc = self.tmp_master.read_register(1, 1)
                temp_programmer = self.tmp_master.read_register(5, 1)
                power_out = self.tmp_master.read_register(85, 1)
            except IOError:
                continue
                # print("Failed to read from instrument")
            except ValueError:
                continue
                # print("Instrument response is invalid")
            try:
                result = float(temp_tc) < float(sp)
                if result == True:
                    temp_tc = float(temp_tc)
                    sp = float(sp)
                    self.pressure_report()
                    print(
                        "-----------------------------------------------------------------------------------------------------\n",
                        f"Setpoint Temp: {sp} C | Programmer Temp: {temp_programmer} C | Reactor Temp: {temp_tc} C | Power out: {power_out}% ---\n",
                        "-----------------------------------------------------------------------------------------------------",
                    )
                    print("\033[F\033[F\033[F\033[F\033[F\033[F", end="")
                    time.sleep(1)
                else:
                    print(f"{sp} C setpoint reached!")
                    break
            except TypeError:
                continue

    def cooling_event(self, rate_sp=None, sp=None):
        """Loops over actual temperature in an cooling event until setpoint is reached"""

        print("Starting cooling event:")
        try:
            print(f"Heating rate: {rate_sp} C/min")
            rate_sp = float(rate_sp)
            self.tmp_master.write_register(35, rate_sp, 1)
        except:
            rate_sp = None
        try:
            print(f"Setpoint: {sp} C")
            sp = float(sp)
            self.tmp_master.write_register(2, sp, 1)
        except:
            sp = None
        while True:
            try:
                temp_tc = self.tmp_master.read_register(1, 1)
                temp_programmer = self.tmp_master.read_register(5, 1)
                power_out = self.tmp_master.read_register(85, 1)
            except IOError:
                continue
                # print("Failed to read from instrument")
            except ValueError:
                continue
                # print("Instrument response is invalid")
            try:
                result = float(temp_tc) > float(sp)
                if result == True:
                    temp_tc = float(temp_tc)
                    sp = float(sp)
                    self.pressure_report()
                    print(
                        "-----------------------------------------------------------------------------------------------------\n",
                        f"Setpoint Temp: {sp} C | Programmer Temp: {temp_programmer} C | Reactor Temp: {temp_tc} C | Power out: {power_out}% ---\n",
                        "-----------------------------------------------------------------------------------------------------",
                    )
                    print("\033[F\033[F\033[F\033[F\033[F\033[F", end="")
                    time.sleep(1)
                else:
                    print(f"{sp} C setpoint reached!")
                    break
            except TypeError:
                continue

    def temperature_ramping_event(self, rate_sp=None, sp=None):
        while True:
            try:
                temp_pv = self.tmp_master.read_register(1, 1)
            except IOError:
                continue
                # print("Failed to read from instrument")
            except ValueError:
                continue
                # print("Instrument response is invalid")
            try:
                result = float(temp_pv) > float(sp)
                if result == True:
                    self.cooling_event(rate_sp, sp)
                    print("Start of cooling event")
                    break
                else:
                    self.heating_event(rate_sp, sp)
                    print("Start of heating event")
                    break
            except TypeError:
                continue

    def setpoint_finish_experiment(self):
        """Loops over actual temperature in an cooling event until setpoint is reached"""
        rate_sp = 10
        sp = 18

        print("adjust temperature set point to 18C:")
        try:
            print(f"cooling rate: {rate_sp} C/min")
            rate_sp = float(rate_sp)
            self.tmp_master.write_register(35, rate_sp, 1)
        except:
            rate_sp = None

        try:
            print(f"Setpoint: {sp} C")
            sp = float(sp)
            self.tmp_master.write_register(24, sp, 1)
        except:
            sp = None

    def time_event(self, time_in_seconds: int, argument: str):
        """Waits for a specified time while printing the elapsed time on the terminal.

        Args:
            time_in_seconds (int): The time to wait in seconds.
        """
        start_time = time.time()
        while True:
            elapsed_time = time.time() - start_time
            if elapsed_time < time_in_seconds:
                temp_tc = self.tmp_master.read_register(1, 1)
                self.pressure_report()
                print(
                    "-----------------------------------------------------------------------------------------------------\n",
                    f"Elapsed time for {str(argument)}: {int(elapsed_time)} seconds at {temp_tc} degC\n",
                    "-----------------------------------------------------------------------------------------------------",
                )
                print("\033[F\033[F\033[F\033[F\033[F\033[F", end="")
                time.sleep(1)
            else:
                print(
                    "-----------------------------------------------------------------------------------------------------\n",
                    f"Wait time of {time_in_seconds} seconds at {temp_tc} degC completed.",
                    "-------------------------------------------------------------------\n",
                    "-----------------------------------------------------------------------------------------------------",
                    end="\r",
                )
                break

    ## Remote Triggering
    #
    # The slave register can hold integer values in the range 0 to 65535
    def drift_mantis_pid(self):
        self.tmp_master.write_register(6, 86.9, 1)
        self.tmp_master.write_register(8, 96)
        self.tmp_master.write_register(9, 16)
        p = self.tmp_master.read_register(6, 1)
        i = self.tmp_master.read_register(8)
        d = self.tmp_master.read_register(9)
        print(
            f"PID for DRIFTS cell is:\nProportional band = {p}\nIntegral time = {i}\nDerivative time = {d}\nPlease switch power output to LOCAL"
        )

    def clausen_coil_local_pid(self):
        self.tmp_master.write_register(6, 987.6, 1)
        self.tmp_master.write_register(8, 96)
        self.tmp_master.write_register(9, 16)
        p = self.tmp_master.read_register(6, 1)
        i = self.tmp_master.read_register(8)
        d = self.tmp_master.read_register(9)
        print(
            f"PID for clausen cell with coil heating elements and LOCAL power supply is:\nProportional band = {p}\nIntegral time = {i}\nDerivative time = {d}\nPlease switch power output to LOCAL"
        )

    def clausen_coil_remote_pid(self):
        self.tmp_master.write_register(6, 600)
        self.tmp_master.write_register(8, 20)
        self.tmp_master.write_register(9, 4)
        p = self.tmp_master.read_register(6)
        i = self.tmp_master.read_register(8)
        d = self.tmp_master.read_register(9)
        print(
            f"PID for clausen cell with coil heating elements and REMOTE power supply is:\nProportional band = {p}\nIntegral time = {i}\nDerivative time = {d}\nPlease switch power output to REMOTE"
        )

    def MS_ON(self):
        """Sends a logic value (0 or 1) to perform remote digital triggering to RlyAA"""
        self.tmp_master.write_register(363, 1)
        time.sleep(10)
        print("MS sequence started")

    def MS_OFF(self):
        """Sends a logic value (0 or 1) to perform remote digital triggering to RlyAA"""
        self.tmp_master.write_register(363, 0)
        time.sleep(10)
        print("MS sequence stopped")

    def IR_ON(self):
        """Sends 5V to perform remote triggering to logic A"""
        self.tmp_master.write_register(376, 5)
        time.sleep(1)
        self.tmp_master.write_register(376, 0)
        print("IR data acquisition started")
        now = datetime.now()
        dt_start = now.strftime("%m/%d/%Y %H:%M:%S")
        print("\ndate and time =", dt_start)

    def pulse_ON(self):
        """Sends 5V to perform remote triggering to logic A"""
        self.tmp_master.write_register(376, 3)
        # sleep(1)
        # self.write_register(376, 0)
        print("Pulse ON")
        now = datetime.now()
        dt_start = now.strftime("%m/%d/%Y %H:%M:%S")
        print("\ndate and time =", dt_start)

    def pulse_OFF(self):
        """Sends 5V to perform remote triggering to logic A"""
        self.tmp_master.write_register(376, 0)
        # sleep(1)
        # self.write_register(376, 0)
        print("Pulse OFF")
        now = datetime.now()
        dt_start = now.strftime("%m/%d/%Y %H:%M:%S")
        print("\ndate and time =", dt_start)

    def IR_STATUS(self):
        """Sends 5V to perform remote triggering to logic A"""
        while True:
            try:
                result = self.tmp_master.read_register(361)
            except IOError:
                continue
                # print("Failed to read from instrument")
            except ValueError:
                continue
                # print("Instrument response is invalid")
            if result == 1:
                break
            elif result == 0:
                time.sleep(0.1)
                continue
