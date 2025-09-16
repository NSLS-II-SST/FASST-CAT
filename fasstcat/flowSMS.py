import propar
from .serialTCP import SerialTCP
from .utils import convert_com_port
import time


# ███████╗██╗      ██████╗ ██╗    ██╗      ███████╗███╗   ███╗███████╗
# ██╔════╝██║     ██╔═══██╗██║    ██║      ██╔════╝████╗ ████║██╔════╝
# █████╗  ██║     ██║   ██║██║ █╗ ██║█████╗███████╗██╔████╔██║███████╗
# ██╔══╝  ██║     ██║   ██║██║███╗██║╚════╝╚════██║██║╚██╔╝██║╚════██║
# ██║     ███████╗╚██████╔╝╚███╔███╔╝      ███████║██║ ╚═╝ ██║███████║
# ╚═╝     ╚══════╝ ╚═════╝  ╚══╝╚══╝       ╚══════╝╚═╝     ╚═╝╚══════╝


class FlowSMS:

    def __init__(self, config, gas_config, valves):
        """Initialize Flow-SMS mass flow controllers.

        Args:
            config (dict): Configuration dictionary containing connection settings
            valves: Valve controller instance
        """

        # Initialize connection
        if "HOST_MOXA" in config and "PORT_MFC" in config:
            self.mfc_master = propar.master(
                config["HOST_MOXA"], config["PORT_MFC"], serial_class=SerialTCP
            )
        else:
            mfc_comport = convert_com_port(config["COM_MFC"])
            self.mfc_master = propar.master(mfc_comport, 38400)

        self.valves = valves

        # Load gas list
        self.load_gas_config(gas_config)

    def load_gas_config(self, gas_config):
        """Load gas configuration into lookup dictionaries.

        Args:
            gas_config (dict): Gas configuration dictionary
        """
        self.gas_list = list(gas_config.keys())

        # Create lookup dictionaries from gas configurations
        self.gas_ID = {gas: config["node_id"] for gas, config in gas_config.items()}
        self.gas_cal = {gas: config["cal_id"] for gas, config in gas_config.items()}
        self.gas_flow_range = {
            gas: config["flow_range"] for gas, config in gas_config.items()
        }
        self.calibration_factor = {
            gas: config["cal_factor"] for gas, config in gas_config.items()
        }
        self.gas_float_to_int_factor = {
            gas: config["float_to_int_factor"] for gas, config in gas_config.items()
        }

    def set_flowrate(
        self,
        gas: str,
        flow: float,
    ):
        """Function that sets the flow rate of a gas in the Flow-SMS mass flow controllers

        Args:
            gas (str): Gas for which the flow rate will be set
            flow (float): Flow rate in sccm
        """
        if gas not in self.gas_list:
            raise ValueError("Gas not in list of available gases")

        while True:
            if (flow is None) or (flow == 0.0):
                flow_conv = 0.0
                break

            flow_conv = flow / self.calibration_factor[gas]

            if flow_conv < self.gas_flow_range[gas][0]:
                print(
                    f"{gas} flow lower than minimum {self.gas_flow_range[gas][0]} sccm"
                )
                interval = input(
                    'Write "Yes" for setting a new flow or "No" for quiting the program: '
                )
                if interval == "Yes":
                    flow = float(input("Enter new flow: "))
                elif interval == "No":
                    raise SystemExit
                else:
                    break

            elif flow_conv > self.gas_flow_range[gas][1]:
                print(
                    f"{gas} flow higher than maximum {self.gas_flow_range[gas][1]} sccm"
                )
                interval = input(
                    'Write "Yes" for setting a new flow or "No" for quiting the program: '
                )
                if interval == "Yes":
                    flow = float(input("Enter new flow: "))
                elif interval == "No":
                    raise SystemExit
                else:
                    break
            else:
                break

        if flow_conv > 0.0:
            self.valves.feed_gas(gas)

        flow_data = int(flow_conv * 32000 / self.gas_float_to_int_factor[gas])

        param = []

        if self.gas_cal[gas] is not None:
            param.append(
                {
                    "node": self.gas_ID[gas],
                    "proc_nr": 1,
                    "parm_nr": 16,
                    "parm_type": propar.PP_TYPE_INT8,
                    "data": self.gas_cal[gas],
                }
            )

        param.append(
            {
                "node": self.gas_ID[gas],
                "proc_nr": 1,
                "parm_nr": 1,
                "parm_type": propar.PP_TYPE_INT16,
                "data": flow_data,
            }
        )

        status = self.mfc_master.write_parameters(param)
        return status

    def setpoints_old(
        self,
        H2_A: float = None,
        D2_A: float = None,
        O2_A: float = None,
        CO_AH: float = None,
        CO2_AH: float = None,
        CO_AL: float = None,
        CO2_AL: float = None,
        CH4_A: float = None,
        C2H6_A: float = None,
        C3H8_A: float = None,
        He_A: float = None,
        Ar_A: float = None,
        N2_A: float = None,
        He_B: float = None,
        Ar_B: float = None,
        N2_B: float = None,
        CH4_B: float = None,
        C2H6_B: float = None,
        C3H8_B: float = None,
        CO_BH: float = None,
        CO2_BH: float = None,
        CO_BL: float = None,
        CO2_BL: float = None,
        O2_B: float = None,
        H2_B: float = None,
        D2_B: float = None,
    ):
        """Function that sets the flow rates of the gases in the Flow-SMS mass flow controllers

        Args:
            H2_A (float): Flow rate of H2 in sccm for gas line A [default: None]
            H2_B (float): Flow rate of H2 in sccm for gas line B [default: None]
            D2_A (float): Flow rate of D2 in sccm for gas line A [default: None]
            D2_B (float): Flow rate of D2 in sccm for gas line B [default: None]
            O2_A (float): Flow rate of O2 in sccm for gas line A [default: None]
            O2_B (float): Flow rate of O2 in sccm for gas line B [default: None]
            CO_AH (float): Flow rate of CO in sccm for gas line A with high flow calibration curve [default: None]
            CO_AL (float): Flow rate of CO in sccm for gas line A with low flow calibration curve [default: None]
            CO_BH (float): Flow rate of CO in sccm for gas line B with high flow calibration curve [default: None]
            CO_BL (float): Flow rate of CO in sccm for gas line B with low flow calibration curve [default: None]
            CO2_AH (float): Flow rate of CO2 in sccm for gas line A with high flow calibration curve [default: None]
            CO2_AL (float): Flow rate of CO2 in sccm for gas line A with low flow calibration curve [default: None]
            CO2_BH (float): Flow rate of CO2 in sccm for gas line B with high flow calibration curve [default: None]
            CO2_BL (float): Flow rate of CO2 in sccm for gas line B with low flow calibration curve [default: None]
            CH4_A (float): Flow rate of CH4 in sccm for gas line A [default: None]
            CH4_B (float): Flow rate of CH4 in sccm for gas line B [default: None]
            C2H6_A (float): Flow rate of C2H6 in sccm for gas line A [default: None]
            C2H46_B (float): Flow rate of C2H6 in sccm for gas line B [default: None]
            He_A (float): Flow rate of He in sccm for gas line A [default: None]
            He_B (float): Flow rate of He in sccm for gas line B [default: None]
            Ar_A (float): Flow rate of Ar in sccm for gas line A [default: None]
            Ar_B (float): Flow rate of Ar in sccm for gas line B [default: None]
            N2_A (float): Flow rate of N2 in sccm for gas line A [default: None]
            N2_B (float): Flow rate of N2 in sccm for gas line B [default: None]
        """
        if CO_AH is not None and CO_AH > 0.0:
            self.set_flowrate("CO_AH", CO_AH)
        elif CO_AL is not None and CO_AL > 0.0:
            self.set_flowrate("CO_AL", CO_AL)
        elif CO2_AH is not None and CO2_AH > 0.0:
            self.set_flowrate("CO2_AH", CO2_AH)
        else:
            self.set_flowrate("CO2_AL", CO2_AL)

        if CO_BH is not None and CO_BH > 0.0:
            self.set_flowrate("CO_BH", CO_BH)
        elif CO_BL is not None and CO_BL > 0.0:
            self.set_flowrate("CO_BL", CO_BL)
        elif CO2_BH is not None and CO2_BH > 0.0:
            self.set_flowrate("CO2_BH", CO2_BH)
        else:
            self.set_flowrate("CO2_BL", CO2_BL)

        if CH4_A is not None and CH4_A > 0.0:
            self.set_flowrate("CH4_A", CH4_A)
        elif C2H6_A is not None and C2H6_A > 0.0:
            self.set_flowrate("C2H6_A", C2H6_A)
        else:
            self.set_flowrate("C3H8_A", C3H8_A)

        if CH4_B is not None and CH4_B > 0.0:
            self.set_flowrate("CH4_B", CH4_B)
        elif C2H6_B is not None and C2H6_B > 0.0:
            self.set_flowrate("C2H6_B", C2H6_B)
        else:
            self.set_flowrate("C3H8_B", C3H8_B)

        if H2_A is not None and H2_A > 0.0:
            self.set_flowrate("H2_A", H2_A)
        else:
            self.set_flowrate("D2_A", D2_A)

        if H2_B is not None and H2_B > 0.0:
            self.set_flowrate("H2_B", H2_B)
        else:
            self.set_flowrate("D2_B", D2_B)

        if He_A is not None and He_A > 0.0:
            self.set_flowrate("He_A", He_A)
        elif Ar_A is not None and Ar_A > 0.0:
            self.set_flowrate("Ar_A", Ar_A)
        else:
            self.set_flowrate("N2_A", N2_A)

        if He_B is not None and He_B > 0.0:
            self.set_flowrate("He_B", He_B)
        elif Ar_B is not None and Ar_B > 0.0:
            self.set_flowrate("Ar_B", Ar_B)
        else:
            self.set_flowrate("N2_B", N2_B)

        self.set_flowrate("O2_A", O2_A)

        self.set_flowrate("O2_B", O2_B)

    def setpoints(self, **kwargs):
        """Function to set flow rates for gases with any unspecified gases defaulting to zero."""

        gas_params = {
            "H2_A": ("H2_A", "D2_A"),
            "H2_B": ("H2_B", "D2_B"),
            "O2_A": ("O2_A",),
            "O2_B": ("O2_B",),
            "CH4_A": ("CH4_A", "C2H6_A", "C3H8_A"),
            "CH4_B": ("CH4_B", "C2H6_B", "C3H8_B"),
            "CO_AH": ("CO_AH", "CO2_AH", "CO_AL", "CO2_AL"),
            "CO_BH": ("CO_BH", "CO2_BH", "CO_BL", "CO2_BL"),
            "He_A": ("He_A", "Ar_A", "N2_A"),
            "He_B": ("He_B", "Ar_B", "N2_B"),
        }

        # Loop to set each specified flow from kwargs
        for gas_key, options in gas_params.items():
            # Set flow for the specified gas, defaulting to the primary option if no specific choice
            for option in options:
                if option in kwargs and kwargs[option] is not None:
                    self.set_flowrate(option, kwargs[option])
                    break
            else:
                # No specified flowrate, set primary option to zero
                self.set_flowrate(options[0], 0.0)

    def generate_params(self, node_id):
        """Helper function that creates the dictionary with the values to pull from devices

        Args:
            node ID (int): MODBUS address for each device
        """
        return [
            {
                "node": node_id,
                "proc_nr": 33,
                "parm_nr": 0,
                "parm_type": propar.PP_TYPE_FLOAT,
            },
            {
                "node": node_id,
                "proc_nr": 33,
                "parm_nr": 3,
                "parm_type": propar.PP_TYPE_FLOAT,
            },
            {
                "node": node_id,
                "proc_nr": 1,
                "parm_nr": 16,
                "parm_type": propar.PP_TYPE_INT8,
            },
        ]

    def status_old(self, delay=0.0, verbose=True):
        """Function that reads the flow rates of the gases in the Flow-SMS mass flow controllers

        Args:
            delay (float): Delay time in seconds before reading the flow rates [default: 0.0]
        """

        time.sleep(delay)

        # Parameters to be read from the Flow-SMS mass flow controllers
        params_h2_d2_a = self.generate_params(self.gas_ID["H2_A"])
        params_h2_d2_b = self.generate_params(self.gas_ID["H2_B"])
        params_o2_a = self.generate_params(self.gas_ID["O2_A"])
        params_o2_b = self.generate_params(self.gas_ID["O2_B"])
        params_hc_a = self.generate_params(self.gas_ID["CH4_A"])
        params_hc_b = self.generate_params(self.gas_ID["CH4_B"])
        params_co_co2_a = self.generate_params(self.gas_ID["CO_AH"])
        params_co_co2_b = self.generate_params(self.gas_ID["CO_BH"])
        params_carrier_a = self.generate_params(self.gas_ID["He_A"])
        params_carrier_b = self.generate_params(self.gas_ID["He_B"])
        params_p_a = [
            {"node": 3, "proc_nr": 33, "parm_nr": 0, "parm_type": propar.PP_TYPE_FLOAT}
        ]
        params_p_b = [
            {"node": 14, "proc_nr": 33, "parm_nr": 0, "parm_type": propar.PP_TYPE_FLOAT}
        ]

        # Sending the specified parameters to the Flow-SMS
        values_h2_d2_a = self.mfc_master.read_parameters(params_h2_d2_a)
        values_h2_d2_b = self.mfc_master.read_parameters(params_h2_d2_b)
        values_o2_a = self.mfc_master.read_parameters(params_o2_a)
        values_o2_b = self.mfc_master.read_parameters(params_o2_b)
        values_co_co2_a = self.mfc_master.read_parameters(params_co_co2_a)
        values_co_co2_b = self.mfc_master.read_parameters(params_co_co2_b)
        values_hc_a = self.mfc_master.read_parameters(params_hc_a)
        values_hc_b = self.mfc_master.read_parameters(params_hc_b)
        values_carrier_a = self.mfc_master.read_parameters(params_carrier_a)
        values_carrier_b = self.mfc_master.read_parameters(params_carrier_b)
        values_p_a = self.mfc_master.read_parameters(params_p_a)
        values_p_b = self.mfc_master.read_parameters(params_p_b)

        # Creating induviduals lists for the read values from each MFC
        lst_h2_d2_a = []
        for value in values_h2_d2_a:
            if "data" in value:
                flow = value.get("data")
            lst_h2_d2_a.append(f"{flow: .2f}")
        fluid_h2_d2_a = float(lst_h2_d2_a[2])
        if fluid_h2_d2_a == 0:
            fluid_h2_d2_a = "H2_A"
        elif fluid_h2_d2_a == 1:
            fluid_h2_d2_a = "D2_A"

        lst_h2_d2_b = []
        for value in values_h2_d2_b:
            if "data" in value:
                flow = value.get("data")
            lst_h2_d2_b.append(f"{flow: .2f}")
        fluid_h2_d2_b = float(lst_h2_d2_b[2])
        if fluid_h2_d2_b == 0:
            fluid_h2_d2_b = "H2_B"
        elif fluid_h2_d2_b == 1:
            fluid_h2_d2_b = "D2_B"

        lst_o2_a = []
        for value in values_o2_a:
            if "data" in value:
                flow = value.get("data")
            lst_o2_a.append(f"{flow: .2f}")

        lst_o2_b = []
        for value in values_o2_b:
            if "data" in value:
                flow = value.get("data")
            lst_o2_b.append(f"{flow: .2f}")

        lst_co_co2_a = []
        for value in values_co_co2_a:
            if "data" in value:
                flow = value.get("data")
            lst_co_co2_a.append(f"{flow: .2f}")
        fluid_co_co2_a = float(lst_co_co2_a[2])
        if fluid_co_co2_a == 0:
            fluid_co_co2_a = "CO_AH"
        elif fluid_co_co2_a == 1:
            fluid_co_co2_a = "CO2_AH"
        elif fluid_co_co2_a == 2:
            fluid_co_co2_a = "CO2_AL"
        elif fluid_co_co2_a == 3:
            fluid_co_co2_a = "CO_AL"

        lst_co_co2_b = []
        for value in values_co_co2_b:
            if "data" in value:
                flow = value.get("data")
            lst_co_co2_b.append(f"{flow: .2f}")
        fluid_co_co2_b = float(lst_co_co2_b[2])
        if fluid_co_co2_b == 0:
            fluid_co_co2_b = "CO_BH"
        elif fluid_co_co2_b == 1:
            fluid_co_co2_b = "CO2_BH"
        elif fluid_co_co2_b == 2:
            fluid_co_co2_b = "CO2_BL"
        elif fluid_co_co2_b == 3:
            fluid_co_co2_b = "CO_BL"

        lst_hc_a = []
        for value in values_hc_a:
            if "data" in value:
                flow = value.get("data")
            lst_hc_a.append(f"{flow: .2f}")
        fluid_hc_a = float(lst_hc_a[2])
        if fluid_hc_a == 0:
            fluid_hc_a = "CH4_A"
        elif fluid_hc_a == 1:
            fluid_hc_a = "C2H6_A"
        elif fluid_hc_a == 2:
            fluid_hc_a = "C3H8_A"

        lst_hc_b = []
        for value in values_hc_b:
            if "data" in value:
                flow = value.get("data")
            lst_hc_b.append(f"{flow: .2f}")
        fluid_hc_b = float(lst_hc_b[2])
        if fluid_hc_b == 0:
            fluid_hc_b = "CH4_B"
        elif fluid_hc_b == 1:
            fluid_hc_b = "C2H6_B"
        elif fluid_hc_b == 2:
            fluid_hc_b = "C3H8_B"

        lst_carrier_a = []
        for value in values_carrier_a:
            if "data" in value:
                flow = value.get("data")
            lst_carrier_a.append(f"{flow: .2f}")
        fluid_carrier_a = float(lst_carrier_a[2])
        if fluid_carrier_a == 0:
            fluid_carrier_a = "He"
        elif fluid_carrier_a == 1:
            fluid_carrier_a = "Ar"
        elif fluid_carrier_a == 2:
            fluid_carrier_a = "N2"

        lst_carrier_b = []
        for value in values_carrier_b:
            if "data" in value:
                flow = value.get("data")
            lst_carrier_b.append(f"{flow: .2f}")
        fluid_carrier_b = float(lst_carrier_b[2])
        if fluid_carrier_b == 0:
            fluid_carrier_b = "He"
        elif fluid_carrier_b == 1:
            fluid_carrier_b = "Ar"
        elif fluid_carrier_b == 2:
            fluid_carrier_b = "N2"

        lst_p_a = []
        p_a_dict = values_p_a[0]
        p_a = f"{p_a_dict.get('data'): .2f}"
        lst_p_a.append(p_a)

        lst_p_b = []
        p_b_dict = values_p_b[0]
        p_b = f"{p_b_dict.get('data'): .2f}"
        lst_p_b.append(p_b)

        # Calculating percentage values for the actual flows

        total_flow_a = float(
            f"{(float(lst_h2_d2_a[0]) + float(lst_o2_a[0]) + float(lst_co_co2_a[0]) + float(lst_hc_a[0]) + float(lst_carrier_a[0])): .2f}"
        )
        if total_flow_a != 0:
            H2_D2_percent_a = f"{(float(lst_h2_d2_a[0]) / total_flow_a) * 100: .1f}"
            O2_percent_a = f"{(float(lst_o2_a[0]) / total_flow_a) * 100: .1f}"
            CO_CO2_percent_a = f"{(float(lst_co_co2_a[0]) / total_flow_a) * 100: .1f}"
            HC_percent_a = f"{(float(lst_hc_a[0]) / total_flow_a) * 100: .1f}"
            # carrier_a_percent = f"{(float(lst_carrier_a[0])/total_flow_a)*100: .1f}"

        total_flow_b = float(
            f"{(float(lst_h2_d2_b[0]) + float(lst_o2_b[0]) + float(lst_co_co2_b[0]) + float(lst_hc_b[0]) + float(lst_carrier_b[0])): .2f}"
        )
        if total_flow_b != 0:
            H2_D2_percent_b = f"{(float(lst_h2_d2_b[0]) / total_flow_b) * 100: .1f}"
            O2_percent_b = f"{(float(lst_o2_b[0]) / total_flow_b) * 100: .1f}"
            CO_CO2_percent_b = f"{(float(lst_co_co2_b[0]) / total_flow_b) * 100: .1f}"
            HC_percent_b = f"{(float(lst_hc_b[0]) / total_flow_b) * 100: .1f}"
            # carrier_b_percent = f"{(float(lst_carrier_b[0])/total_flow_b)*100: .1f}"

        # Creating and printing table with the actual and set flows, and line pressures

        if verbose:

            print(" ")
            print("------------------------------------------------------------")
            print("-------------------")
            print("--- Flow Report ---")
            print("-------------------")

            if float(lst_h2_d2_a[1]) == 0:
                pass
            else:
                print(
                    f"{fluid_h2_d2_a}_A: measured flow is {lst_h2_d2_a[0]} sccm. Flow setpoint is {lst_h2_d2_a[1]} sccm. Concentration is {H2_D2_percent_a}%"
                )

            if float(lst_h2_d2_b[1]) == 0:
                pass
            else:
                print(
                    f"{fluid_h2_d2_b}_B: measured flow is {lst_h2_d2_b[0]} sccm. Flow setpoint is {lst_h2_d2_b[1]} sccm. Concentration is {H2_D2_percent_b}%"
                )

            if float(lst_o2_a[1]) == 0:
                pass
            else:
                print(
                    f"O2_A: measured flow is {lst_o2_a[0]} sccm. Flow setpoint is {lst_o2_a[1]} sccm. Concentration is {O2_percent_a}%"
                )

            if float(lst_o2_b[1]) == 0:
                pass
            else:
                print(
                    f"O2_B: measured flow is {lst_o2_b[0]} sccm. Flow setpoint is {lst_o2_b[1]} sccm. Concentration is {O2_percent_b}%"
                )

            if float(lst_co_co2_a[1]) == 0:
                pass
            else:
                print(
                    f"{fluid_co_co2_a}_A: measured flow is {lst_co_co2_a[0]} sccm. Flow setpoint is {lst_co_co2_a[1]} sccm. Concentration is {CO_CO2_percent_a}%"
                )

            if float(lst_co_co2_b[1]) == 0:
                pass
            else:
                print(
                    f"{fluid_co_co2_b}_B: measured flow is {lst_co_co2_b[0]} sccm. Flow setpoint is {lst_co_co2_b[1]} sccm. Concentration is {CO_CO2_percent_b}%"
                )

            if float(lst_hc_a[1]) == 0:
                pass
            else:
                print(
                    f"{fluid_hc_a}_A: measured flow is {lst_hc_a[0]} sccm. Flow setpoint is {lst_hc_a[1]} sccm. Concentration is {HC_percent_a}%"
                )

            if float(lst_hc_b[1]) == 0:
                pass
            else:
                print(
                    f"{fluid_hc_b}_B: measured flow is {lst_hc_b[0]} sccm. Flow setpoint is {lst_hc_b[1]} sccm. Concentration is {HC_percent_b}%"
                )

            if float(lst_carrier_a[1]) == 0:
                pass
            else:
                print(
                    f"{fluid_carrier_a}_A: measured flow is {lst_carrier_a[0]} sccm. Flow setpoint is {lst_carrier_a[1]} sccm"
                )

            if float(lst_carrier_b[1]) == 0:
                pass
            else:
                print(
                    f"{fluid_carrier_b}_B: measured flow is {lst_carrier_b[0]} sccm. Flow setpoint is {lst_carrier_b[1]} sccm"
                )

            print(f"Total flow line A: {total_flow_a} sccm")

            print(f"Total flow line B: {total_flow_b} sccm")

            print("-----------------------")
            print("--- Pressure Report ---")
            print("-----------------------")

            print(f"Pressure in line A: {lst_p_a[0]} psia")

            print(f"Pressure in line B: {lst_p_b[0]} psia")

            print("------------------------------------------------------------")

    def status(self, delay=0.0, verbose=True):
        """Function that reads the flow rates of the gases in the Flow-SMS mass flow controllers

        Args:
            delay (float): Delay time in seconds before reading the flow rates [default: 0.0]
        """
        time.sleep(delay)

        # Define gas parameters with respective gas IDs and names
        gas_params = {
            "H2_A": ("H2_A", "D2_A"),
            "H2_B": ("H2_B", "D2_B"),
            "O2_A": ("O2_A",),
            "O2_B": ("O2_B",),
            "CH4_A": ("CH4_A", "C2H6_A", "C3H8_A"),
            "CH4_B": ("CH4_B", "C2H6_B", "C3H8_B"),
            "CO_AH": ("CO_AH", "CO2_AH", "CO2_AL", "CO_AL"),
            "CO_BH": ("CO_BH", "CO2_BH", "CO2_BL", "CO_BL"),
            "He_A": ("He_A", "Ar_A", "N2_A"),
            "He_B": ("He_B", "Ar_B", "N2_B"),
        }

        # Initialize lists for storing the read values
        values_dict = {}

        # Read and store parameters for each gas
        for gas_key, fluid_types in gas_params.items():
            params = self.generate_params(self.gas_ID[gas_key])
            values = self.mfc_master.read_parameters(params)
            time.sleep(0.01)

            lst = []
            for value in values:
                if "data" in value:
                    flow = value.get("data")
                lst.append(f"{flow: .2f}")

            # Store the corresponding fluid type
            fluid_value = float(lst[2]) if len(fluid_types) > 1 else None
            if fluid_value is not None:
                fluid = fluid_types[int(fluid_value)]  # Pick based on the value
            else:
                fluid = fluid_types[0]

            values_dict[gas_key] = (lst, fluid)

        # Calculate percentage values for the actual flows
        total_flow_a = f'{(sum(float(values_dict[gas][0][0]) for gas in ["H2_A", "O2_A", "CO_AH", "CH4_A", "He_A"])): .2f}'
        total_flow_b = f'{(sum(float(values_dict[gas][0][0]) for gas in ["H2_B", "O2_B", "CO_BH", "CH4_B", "He_B"])): .2f}'

        # Concentration percentages for gases on line A and B
        percentages_a = {
            gas: f"{(float(values_dict[gas][0][0]) / float(total_flow_a)) * 100: .1f}"
            for gas in ["H2_A", "O2_A", "CO_AH", "CH4_A", "He_A"]
        }
        percentages_b = {
            gas: f"{(float(values_dict[gas][0][0]) / float(total_flow_b)) * 100: .1f}"
            for gas in ["H2_B", "O2_B", "CO_BH", "CH4_B", "He_B"]
        }

        # Creating and printing table with the actual and set flows, and line pressures
        if verbose:
            print(" ")
            print("------------------------------------------------------------")
            print("-------------------")
            print("--- Flow Report ---")
            print("-------------------")
            for gas_key, (lst, fluid) in values_dict.items():
                setpoint = lst[1]
                if float(setpoint) != 0:
                    concentration = (
                        percentages_a[gas_key]
                        if (
                            gas_key.endswith("_A")
                            or gas_key.endswith("_AH")
                            or gas_key.endswith("_AL")
                        )
                        else percentages_b[gas_key]
                    )
                    print(
                        f"{fluid}: measured flow is {lst[0]} sccm, Flow setpoint is {setpoint} sccm, Concentration is {concentration} %."
                    )

            print(f"Total flow line A: {total_flow_a} sccm")
            print(f"Total flow line B: {total_flow_b} sccm")
            print("-----------------------")
            print("--- Pressure Report ---")
            print("-----------------------")
            self.pressure_report(verbose=True)
            print("------------------------------------------------------------")

    def pressure_report(self, verbose: bool = False):
        values_p_a = self.mfc_master.read_parameters(
            [
                {
                    "node": 3,
                    "proc_nr": 33,
                    "parm_nr": 0,
                    "parm_type": propar.PP_TYPE_FLOAT,
                }
            ]
        )
        time.sleep(0.1)
        self.p_a = float(f"{values_p_a[0]['data']: .2f}")
        values_p_b = self.mfc_master.read_parameters(
            [
                {
                    "node": 14,
                    "proc_nr": 33,
                    "parm_nr": 0,
                    "parm_type": propar.PP_TYPE_FLOAT,
                }
            ]
        )
        time.sleep(0.1)
        self.p_b = float(f"{values_p_b[0]['data']: .2f}")
        if verbose is True:
            print(
                f"Pressure in Line A = {self.p_a} psia\nPressure in Line B = {self.p_b} psia"
            )
        return self.p_a, self.p_b
