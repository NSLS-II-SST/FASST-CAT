import platform
import threading
import time
from pathlib import Path


def get_config_files(config, gases):
    # Get the project root directory (parent of fasstcat package)
    project_root = Path(__file__).parent.parent
    config_dir = project_root / "config"
    examples_dir = project_root / "examples"

    def find_config_file(filename, search_paths):
        """Find a configuration file in the given search paths."""
        for path in search_paths:
            file_path = path / filename
            if file_path.exists():
                return file_path
        return None

    # Check if custom paths are provided and exist
    config_path_abs = Path(config)
    gases_path_abs = Path(gases)

    if config_path_abs.exists() and gases_path_abs.exists():
        # Both files exist as specified
        config_path = config_path_abs
        gases_path = gases_path_abs
    else:
        # Determine search paths for config files
        if config == "config.json" and gases == "gases.toml":
            # Use default search order: config/ -> examples/
            config_search_paths = [config_dir, examples_dir]
            gases_search_paths = [config_dir, examples_dir]
        else:
            # Try to find them in the project directories
            config_search_paths = [project_root, config_dir, examples_dir]
            gases_search_paths = [project_root, config_dir, examples_dir]

        # Find configuration files
        config_path = find_config_file(config, config_search_paths)
        gases_path = find_config_file(gases, gases_search_paths)

    if config_path is None:
        print(f"Error: Configuration file '{config}' not found.")
        print("Searched in:")
        for path in config_search_paths:
            print(f"  - {path}")
        print(f"\nPlease copy example files from {examples_dir} to {config_dir}")
        print("or provide a valid path to your config.json file.")
        return None, None

    if gases_path is None:
        print(f"Error: Gases file '{gases}' not found.")
        print("Searched in:")
        for path in gases_search_paths:
            print(f"  - {path}")
        print(f"\nPlease copy example files from {examples_dir} to {config_dir}")
        print("or provide a valid path to your gases.toml file.")
        return None, None
    return config_path, gases_path


def make_gas_line_dict(config):

    gas_line_dict = {}
    gas_assignments = config.get("gas_assignments", {})

    for input, assignment in gas_assignments.items():
        input_config = config["inputs"].get(input, {})
        has_line_a = input_config.get("mfc_a", "") != ""
        has_line_b = input_config.get("mfc_b", "") != ""

        for valve_position, gas in assignment.items():
            if gas not in gas_line_dict:
                gas_line_dict[gas] = {}
                if has_line_a:
                    gas_line_dict[gas]["A"] = {}
                    gas_line_dict[gas]["A"][input] = valve_position
                if has_line_b:
                    gas_line_dict[gas]["B"] = {}
                    gas_line_dict[gas]["B"][input] = valve_position
            else:
                if has_line_a:
                    if "A" not in gas_line_dict[gas]:
                        gas_line_dict[gas]["A"] = {}
                    gas_line_dict[gas]["A"][input] = valve_position
                if has_line_b:
                    if "B" not in gas_line_dict[gas]:
                        gas_line_dict[gas]["B"] = {}
                    gas_line_dict[gas]["B"][input] = valve_position
    return gas_line_dict


def translate_gas_config(config):
    """
    Read the new gas configuration format and generate a dictionary equivalent
    to the old gases.toml format, but only including connected gases.

    Parameters
    ----------
    config_file : str
        Path to the new gas configuration file

    Returns
    -------
    dict
        Dictionary in the old gases.toml format with only connected gases
    """

    # Get the hardware configuration and gas assignments
    inputs = config.get("inputs", {})
    gas_assignments = config.get("gas_assignments", {})
    gas_config = config.get("gas_config", {})

    # Dictionary to hold the generated gas flows (old format)
    gas_flows = {}

    # Process each input and its gas assignments
    for input_id, assignment in gas_assignments.items():
        input_id = str(input_id)
        input_config = inputs.get(input_id, {})

        # Get MFC node IDs for this input
        mfc_a = input_config.get("mfc_a", "")
        mfc_b = input_config.get("mfc_b", "")
        valve = input_config.get("valve", "")

        # Handle empty strings as None
        if mfc_a == "":
            mfc_a = None
        if mfc_b == "":
            mfc_b = None
        if valve == "":
            valve = None

        # Process each gas assignment for this input
        for valve_key, gas in assignment.items():
            if not gas:  # Skip empty assignments
                continue

            # Determine valve position
            if valve_key == "valve_off":
                valve_position = "OFF"
            elif valve_key == "valve_on":
                valve_position = "ON"
            elif valve_key == "valve_null":
                valve_position = None
            else:
                continue  # Skip unknown valve keys

            # Get gas configuration
            gas_cfg = gas_config.get(gas, {})

            # Check if gas has multiple flow rates
            if "high" in gas_cfg and "low" in gas_cfg:
                # Gas has high and low flow rates
                for flow_type in ["high", "low"]:
                    flow_cfg = gas_cfg[flow_type]

                    # Create entries for both lines A and B if MFCs are available
                    if mfc_a is not None:
                        key_a = f"{gas}_A{flow_type[0].upper()}"
                        gas_flows[key_a] = {
                            "node_id": mfc_a,
                            "cal_id": flow_cfg["cal_id"],
                            "flow_range": flow_cfg["flow_range"],
                            "cal_factor": flow_cfg["cal_factor"],
                            "float_to_int_factor": (flow_cfg["float_to_int_factor"]),
                        }
                        if valve and valve_position is not None:
                            gas_flows[key_a]["valve_settings"] = [valve, valve_position]

                    if mfc_b is not None:
                        key_b = f"{gas}_B{flow_type[0].upper()}"
                        gas_flows[key_b] = {
                            "node_id": mfc_b,
                            "cal_id": flow_cfg["cal_id"],
                            "flow_range": flow_cfg["flow_range"],
                            "cal_factor": flow_cfg["cal_factor"],
                            "float_to_int_factor": (flow_cfg["float_to_int_factor"]),
                        }
                        if valve and valve_position is not None:
                            gas_flows[key_b]["valve_settings"] = [valve, valve_position]
            else:
                # Gas has standard flow rate
                if mfc_a is not None:
                    key_a = f"{gas}_A"
                    gas_flows[key_a] = {
                        "node_id": mfc_a,
                        "cal_id": gas_cfg["cal_id"],
                        "flow_range": gas_cfg["flow_range"],
                        "cal_factor": gas_cfg["cal_factor"],
                        "float_to_int_factor": (gas_cfg["float_to_int_factor"]),
                    }
                    if valve and valve_position is not None:
                        gas_flows[key_a]["valve_settings"] = [valve, valve_position]

                if mfc_b is not None:
                    key_b = f"{gas}_B"
                    gas_flows[key_b] = {
                        "node_id": mfc_b,
                        "cal_id": gas_cfg["cal_id"],
                        "flow_range": gas_cfg["flow_range"],
                        "cal_factor": gas_cfg["cal_factor"],
                        "float_to_int_factor": (gas_cfg["float_to_int_factor"]),
                    }
                    if valve and valve_position is not None:
                        gas_flows[key_b]["valve_settings"] = [valve, valve_position]

    return gas_flows


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
                        try:
                            print(
                                "!!!!!!!!!!!!!!HIGH PRESSURE ALARM!!!!!!!!!!!!!!\n!!!!!!!!!!!!!!HIGH PRESSURE ALARM!!!!!!!!!!!!!!\n",
                                "!!!!!!!!!!!!!!HIGH PRESSURE ALARM!!!!!!!!!!!!!!\n!!!!!!!!!!!!!!HIGH PRESSURE ALARM!!!!!!!!!!!!!!\n",
                                f"PRESSURE IN LINE A = {p_a} psia, PRESSURE IN LINE B = {p_b} psia.\n",
                                "CLOSING ALL SHUTOFF VALVES AND TAKING SYSTEM TO ROOM TEMPERATURE",
                            )
                            finished.set()  # Stop monitoring if alarm is triggered
                            self.setpoint_finish_experiment()
                            return
                        except (ValueError, TypeError):
                            continue
                    elif p_a < low_threshold or p_b < low_threshold:
                        self.flowSMS.setpoints()  # Trigger adjustment if above threshold
                        try:
                            print(
                                "!!!!!!!!!!!!!!LOW PRESSURE ALARM!!!!!!!!!!!!!!\n!!!!!!!!!!!!!!LOW PRESSURE ALARM!!!!!!!!!!!!!!\n",
                                "!!!!!!!!!!!!!!LOW PRESSURE ALARM!!!!!!!!!!!!!!\n!!!!!!!!!!!!!!LOW PRESSURE ALARM!!!!!!!!!!!!!!\n",
                                f"PRESSURE IN LINE A = {p_a} psia, PRESSURE IN LINE B = {p_b} psia.\n",
                                "CLOSING ALL SHUTOFF VALVES AND TAKING SYSTEM TO ROOM TEMPERATURE",
                            )
                            finished.set()  # Stop monitoring if alarm is triggered
                            self.setpoint_finish_experiment()
                            return
                        except (ValueError, TypeError):
                            continue
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
