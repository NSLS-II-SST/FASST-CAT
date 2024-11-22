#!/usr/bin/env python3


import time
from datetime import datetime
from pyModbusTCP.client import ModbusClient

HOST = "10.68.42.3"
PORT = 502


class EuroTCP:

    def __init__(
        self,
        host: str = HOST,
        port: int = PORT,
    ) -> None:

        self.host = host
        self.port = port
        self.modbustcp = ModbusClient(host, port)

    def get_temp_wsp(self, verbose=False):
        """Return the process value (PV) for loop1."""
        self.modbustcp.open()
        try:
            regs_list_1 = f"{self.modbustcp.read_holding_registers(2)[0]*0.1: .1f}"
        except:
            regs_list_1 = None
        if verbose:
            print(regs_list_1)
            print(f"WSP Temp = {regs_list_1} degC")
        self.modbustcp.close()
        return regs_list_1

    def get_temp_tc(self, verbose=False):
        """Return the process value (PV) for loop1."""
        self.modbustcp.open()
        try:
            regs_list_1 = f"{self.modbustcp.read_holding_registers(1)[0]*0.1: .1f}"
        except:
            regs_list_1 = None
        if verbose:
            print(regs_list_1)
            print(f"TC Temp = {regs_list_1} degC")
        self.modbustcp.close()
        return regs_list_1

    def get_temp_prog(self, verbose=False):
        """Return the process value (PV) for loop1."""
        self.modbustcp.open()
        try:
            regs_list_1 = f"{self.modbustcp.read_holding_registers(5)[0]*0.1: .1f}"
        except:
            regs_list_1 = None
        if verbose:
            print(regs_list_1)
            print(f"Prog Temp = {regs_list_1} degC")
        self.modbustcp.close()
        return regs_list_1

    def get_pw_prog(self, verbose=False):
        """Return the process value (PV) for loop1."""
        self.modbustcp.open()
        try:
            regs_list_1 = f"{self.modbustcp.read_holding_registers(85)[0]*0.1: .1f}"
        except:
            regs_list_1 = None
        if verbose:
            print(regs_list_1)
            print(f"Prog Power = {regs_list_1}%")
        self.modbustcp.close()
        return regs_list_1

    def get_heating_rate(self, verbose=False):
        """Return the process value (PV) for loop1."""
        self.modbustcp.open()
        try:
            regs_list_1 = f"{self.modbustcp.read_holding_registers(35)[0]*0.1: .1f}"
        except:
            regs_list_1 = None
        if verbose:
            print(regs_list_1)
            print(f"Heating rate = {regs_list_1} degC/min")
        self.modbustcp.close()
        return regs_list_1

    def write_wsp(self, sp):
        """Return the process value (PV) for loop1."""
        self.modbustcp.open()
        try:
            sp = int(sp * 10)
            if not self.retry_write(2, sp, "setpoint"):
                sp = None
        except Exception as e:
            print(f"Error writing setpoint: {e}")
            sp = None
        self.modbustcp.close()
        return True

    def write_heating_rate(self, rate):
        """Return the process value (PV) for loop1."""
        self.modbustcp.open()
        try:
            rate = int(rate * 10)
            if not self.retry_write(35, rate, "rate"):
                rate = None
        except Exception as e:
            print(f"Error writing setpoint: {e}")
            rate = None
        self.modbustcp.close()
        return True

    def retry_write(self, register, value, description, max_retries=5, retry_delay=1):
        """Tries writing to the Modbus register with retries"""
        retries = 0
        while retries < max_retries:
            write_response = self.modbustcp.write_single_register(register, value)
            if write_response is not None:
                # print(f"Successfully wrote {description} to register {register}")
                return True
            else:
                retries += 1
                print(
                    f"Failed to write {description} to register {register}, retrying ({retries}/{max_retries})..."
                )
                time.sleep(retry_delay)
        print(
            f"Failed to write {description} to register {register} after {max_retries} attempts"
        )
        return False

    # @pressure_alarm()
    def heating_event(self, rate_sp=None, sp=None, max_duration=600):
        """Loops over actual temperature in a heating event until setpoint is reached, or max duration exceeded."""
        self.modbustcp.open()

        # Write heating rate to register 35
        try:
            rate_sp_value = int(rate_sp * 10)
            if not self.retry_write(35, rate_sp_value, "heating rate"):
                rate_sp = None
        except Exception as e:
            print(f"Error writing heating rate: {e}")
            rate_sp = None

        # Write setpoint to register 2
        try:
            sp_value = int(sp * 10)
            if not self.retry_write(2, sp_value, "setpoint"):
                sp = None
        except Exception as e:
            print(f"Error writing setpoint: {e}")
            sp = None

        # Loop until setpoint is reached or max duration is exceeded
        start_time = time.time()
        while True:
            try:
                # Read only the necessary registers (1 for temp_tc, 5 for temp_programmer, 85 for power_out, and 2 for sp)
                registers = self.modbustcp.read_holding_registers(
                    0, 86
                )  # Read only needed registers (1-6)
                temp_tc = registers[1] * 0.1  # Reactor temperature (register 1)
                temp_programmer = (
                    registers[5] * 0.1
                )  # Programmer temperature (register 5)
                power_out = registers[85] * 0.1  # Power output (register 85)
                current_sp = registers[2] * 0.1  # Setpoint (register 2)

            except (IOError, None, ValueError, TypeError):
                continue  # You can log these for debugging purposes if necessary

            # Compare temperature with setpoint
            if temp_tc >= current_sp:
                print(f"{current_sp} C setpoint reached!")
                break

            self.p_a, self.p_b = self.pressure_report()

            print(
                "-----------------------------------------------------------------------------------------------------\n",
                f"Setpoint Temp: {current_sp: .1f} C | Programmer Temp: {temp_programmer: .1f} C | "
                f"Reactor Temp: {temp_tc: .1f} C | Power out: {power_out: .1f}% | \n"
                "-----------------------------------------------------------------------------------------------------\n",
                f"Pressure Line A: {self.p_a: .2f} psia | Pressure Line B: {self.p_b: .2f} psia\n",
                "-----------------------------------------------------------------------------------------------------",
            )
            print("\033[F\033[F\033[F\033[F\033[F", end="")  # Move cursor up 5 lines
            print("\033[K", end="")  # Clear the current line

            # Calculate elapsed time and check against max duration
            elapsed_time = time.time() - start_time
            if elapsed_time > max_duration:
                print(
                    f"Max duration of {max_duration} seconds exceeded. Ending heating event."
                )
                break

            time.sleep(1)  # Sleep for 1 second (can be adjusted dynamically if desired)

        self.modbustcp.close()

    # @pressure_alarm()
    def cooling_event(self, rate_sp=None, sp=None, max_duration=600):
        """Loops over actual temperature in a heating event until setpoint is reached, or max duration exceeded."""
        self.modbustcp.open()

        # Write heating rate to register 35
        try:
            rate_sp_value = int(rate_sp * 10)
            if not self.retry_write(35, rate_sp_value, "heating rate"):
                rate_sp = None
        except Exception as e:
            print(f"Error writing heating rate: {e}")
            rate_sp = None

        # Write setpoint to register 2
        try:
            sp_value = int(sp * 10)
            if not self.retry_write(2, sp_value, "setpoint"):
                sp = None
        except Exception as e:
            print(f"Error writing setpoint: {e}")
            sp = None

        # Loop until setpoint is reached or max duration is exceeded
        start_time = time.time()
        while True:
            try:
                # Read only the necessary registers (1 for temp_tc, 5 for temp_programmer, 85 for power_out, and 2 for sp)
                registers = self.modbustcp.read_holding_registers(
                    0, 86
                )  # Read only needed registers (1-6)
                temp_tc = registers[1] * 0.1  # Reactor temperature (register 1)
                temp_programmer = (
                    registers[5] * 0.1
                )  # Programmer temperature (register 5)
                power_out = registers[85] * 0.1  # Power output (register 85)
                current_sp = registers[2] * 0.1  # Setpoint (register 2)

            except (None, IOError, ValueError, TypeError):
                continue  # You can log these for debugging purposes if necessary

            # Compare temperature with setpoint
            if temp_tc <= current_sp:
                print(f"{current_sp} C setpoint reached!")
                break

            self.p_a, self.p_b = self.pressure_report()

            print(
                "-----------------------------------------------------------------------------------------------------\n",
                f"Setpoint Temp: {current_sp: .1f} C | Programmer Temp: {temp_programmer: .1f} C | "
                f"Reactor Temp: {temp_tc: .1f} C | Power out: {power_out: .1f}% | \n"
                "-----------------------------------------------------------------------------------------------------\n",
                f"Pressure Line A: {self.p_a: .2f} psia | Pressure Line B: {self.p_b: .2f} psia\n",
                "-----------------------------------------------------------------------------------------------------",
            )
            print("\033[F\033[F\033[F\033[F\033[F", end="")  # Move cursor up 5 lines
            print("\033[K", end="")  # Clear the current line

            # Calculate elapsed time and check against max duration
            elapsed_time = time.time() - start_time
            if elapsed_time > max_duration:
                print(
                    f"Max duration of {max_duration} seconds exceeded. Ending heating event."
                )
                break

            time.sleep(1)  # Sleep for 1 second (can be adjusted dynamically if desired)

        self.modbustcp.close()

    def temperature_ramping_event(self, rate_sp=None, sp=None):
        while True:
            try:
                temp_tc = f"{self.modbustcp.read_holding_registers(1)[0]*0.1: .1f}"
            except (None, IOError, ValueError, TypeError):
                continue
                # print("Instrument response is invalid")
            try:
                result = float(temp_tc) > float(sp)
                if result:
                    self.cooling_event(rate_sp, sp)
                    print("Starting cooling event")
                    break
                else:
                    self.heating_event(rate_sp, sp)
                    print("Starting heating event")
                    break
            except TypeError:
                continue

    def setpoint_finish_experiment(self):
        """Loops over actual temperature in an cooling event until setpoint is reached"""
        rate = 10
        sp = 20

        self.modbustcp.open()
        try:
            sp = int(sp * 10)
            if not self.retry_write(2, sp, "setpoint"):
                sp = None
        except Exception as e:
            print(f"Error writing setpoint: {e}")
            sp = None

        try:
            rate = int(rate * 10)
            if not self.retry_write(35, rate, "rate"):
                rate = None
        except Exception as e:
            print(f"Error writing setpoint: {e}")
            rate = None

        print("Adjust temperature set point to 20C:")
        print(f"Cooling rate: {rate*0.1} C/min")
        print(f"Setpoint: {sp*0.1} C")

    # @pressure_alarm()
    def time_event(self, time_in_seconds: int, argument: str):
        """Waits for a specified time while printing the elapsed time on the terminal.

        Args:
            time_in_seconds (int): The time to wait in seconds.
        """
        start_time = time.time()
        while True:
            elapsed_time = time.time() - start_time
            if elapsed_time < time_in_seconds:
                try:
                    temp_tc = self.modbustcp.read_holding_registers(1)[0] * 0.1
                except:
                    temp_tc = None
                self.p_a, self.p_b = self.pressure_report()
                print(
                    "-----------------------------------------------------------------------------------------------------\n",
                    f"Elapsed time for {str(argument)}: {int(elapsed_time)} seconds at {temp_tc: .1f} degC\n",
                    "-----------------------------------------------------------------------------------------------------\n",
                    f"Pressure Line A: {self.p_a: .2f} psia | Pressure Line B: {self.p_b: .2f} psia\n",
                    "-----------------------------------------------------------------------------------------------------",
                )
                print(
                    "\033[F\033[F\033[F\033[F\033[F", end=""
                )  # Move cursor up 5 lines
                print("\033[K", end="")  # Clear the current line
                time.sleep(1)
            else:
                print(
                    "-----------------------------------------------------------------------------------------------------\n",
                    f"Wait time of {time_in_seconds} seconds at {temp_tc: .1f} degC completed.",
                    "-------------------------------------------------------------------\n",
                    "-----------------------------------------------------------------------------------------------------",
                    end="\r",
                )
                break

    def drift_mantis_pid(self):
        self.modbustcp.open()
        try:
            self.modbustcp.write_multiple_registers(6, [869, 0, 96, 16])
            regs_list_2 = self.modbustcp.read_holding_registers(6, 4)
        except:
            regs_list_2 = None
        p = regs_list_2[0] * 0.1
        i = regs_list_2[2]
        d = regs_list_2[3]
        print(
            f"PID for Harrick Mantis DRIFTS cell is:\nProportional band = {p}\nIntegral time = {i}\nDerivative time = {d}\nPlease switch power output to LOCAL"
        )
        self.modbustcp.close()

    def clausen_coil_local_pid(self):
        self.modbustcp.open()
        try:
            self.modbustcp.write_multiple_registers(6, [9876, 0, 96, 16])
            regs_list_2 = self.modbustcp.read_holding_registers(6, 4)
        except:
            regs_list_2 = None
        p = regs_list_2[0] * 0.1
        i = regs_list_2[2]
        d = regs_list_2[3]
        print(
            f"PID for clausen cell with coil heating elements and REMOTE power supply is:\nProportional band = {p}\nIntegral time = {i}\nDerivative time = {d}\nPlease switch power output to LOCAL"
        )
        self.modbustcp.close()

    def clausen_coil_remote_pid(self):
        self.modbustcp.open()
        try:
            self.modbustcp.write_multiple_registers(6, [6000, 0, 20, 4])
            regs_list_2 = self.modbustcp.read_holding_registers(6, 4)
        except:
            regs_list_2 = None
        p = regs_list_2[0] * 0.1
        i = regs_list_2[2]
        d = regs_list_2[3]
        print(
            f"PID for clausen cell with coil heating elements and REMOTE power supply is:\nProportional band = {p}\nIntegral time = {i}\nDerivative time = {d}\nPlease switch power output to REMOTE"
        )
        self.modbustcp.close()

    def MS_ON(self):
        """Sends a logic value (0 or 1) to perform remote MS digital triggering to RlyAA"""
        self.modbustcp.open()
        try:
            ms_on = 1
            if not self.retry_write(363, ms_on, "setpoint"):
                ms_on = None
        except Exception as e:
            print(f"Error writing setpoint: {e}")
            ms_on = None
        print("MS recipe started")
        self.modbustcp.close()

    def MS_OFF(self):
        """Sends a logic value (0 or 1) to perform remote MS digital triggering to RlyAA"""
        self.modbustcp.open()
        try:
            ms_on = 0
            if not self.retry_write(363, ms_on, "setpoint"):
                ms_on = None
        except Exception as e:
            print(f"Error writing setpoint: {e}")
            ms_on = None
        print("MS recipe finished")
        self.modbustcp.close()

    def IR_ON(self):
        """Sends 5V pulse to perform remote IR triggering to logic A"""
        self.modbustcp.write_single_register(376, 5)
        # value_high = self.modbustcp.read_holding_registers(376)[0]
        time.sleep(1)
        # print(value_high)
        self.modbustcp.write_single_register(376, 0)
        # value_low = self.modbustcp.read_holding_registers(376)[0]
        # print(value_low)
        print("IR data acquisition started")
        now = datetime.now()
        dt_start = now.strftime("%m/%d/%Y %H:%M:%S")
        print("\ndate and time =", dt_start)

    def pulse_ON(self):
        """Sends 3V to perform remote triggering to logic A"""
        self.modbustcp.write_single_register(376, 3)
        # sleep(1)
        # self.write_register(376, 0)
        print("Pulse ON")
        now = datetime.now()
        dt_start = now.strftime("%m/%d/%Y %H:%M:%S")
        print("\ndate and time =", dt_start)

    def pulse_OFF(self):
        """Sends 0V to perform remote triggering to logic A"""
        self.modbustcp.write_single_register(376, 0)
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
                result = self.modbustcp.read_holding_registers(361)[0]
                # print(result)
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


if __name__ == "__main__":

    eurotcp = EuroTCP()

    eurotcp.pid_clausen_coiled()
    eurotcp.get_temp_wsp()
    eurotcp.get_temp_tc()
    eurotcp.get_temp_prog()
    eurotcp.get_pw_prog()
    eurotcp.get_heating_rate()
