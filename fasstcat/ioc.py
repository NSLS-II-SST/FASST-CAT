import asyncio
from pathlib import Path
from caproto.server import PVGroup, pvproperty, SubGroup, template_arg_parser, run
from caproto._data import ChannelType
from fasstcat.utils import get_config_files
from fasstcat.flowSMS import FlowSMS
from fasstcat.valves import create_valves
from fasstcat.gasControl import GasControl

import tomllib
import json


def inputLineFactory(input_num, gas_config):
    gas_assignments = gas_config["gas_assignments"].get(input_num, {})
    available_gases = set(gas_assignments.values())
    a_enabled = gas_config["inputs"].get("mfc_a", "") != ""
    b_enabled = gas_config["inputs"].get("mfc_b", "") != ""

    # Determine flow limits based on available gases
    # Use the highest upper limit among available gases
    max_flow = 0.0
    for gas_name, details in gas_config["gas_config"].items():
        if gas_name not in available_gases:
            continue
        if isinstance(details, dict) and "flow_range" in details:
            max_flow = max(max_flow, details["flow_range"][1])
        elif isinstance(details, dict):
            # Handle nested gas configs (like CO.high, CO.low)
            for sub_gas, sub_details in details.items():
                if isinstance(sub_details, dict) and "flow_range" in sub_details:
                    max_flow = max(max_flow, sub_details["flow_range"][1])

    # Default to 60 sccm if no flow range found
    if max_flow == 0.0:
        max_flow = 60.0

    class InputLine(PVGroup):
        Gas_Selection = pvproperty(
            value=0,
            enum_strings=available_gases,
            record="mbbo",
            dtype=ChannelType.ENUM,
            doc=f"Gas selection for Input {input_num}",
        )
        Gas_Name = pvproperty(
            value="",
            dtype=str,
            max_length=20,
            read_only=True,
            doc="Current gas name based on selection",
        )
        # Gas flow for line A (only if enabled)
        A_SP = pvproperty(
            value=0.0,
            dtype=float,
            doc=f"Setpoint for Input {input_num}, A line (sccm)",
            units="sccm",
            lower_ctrl_limit=0.0,
            upper_ctrl_limit=max_flow,
        )
        A_RB = pvproperty(
            value=0.0,
            dtype=float,
            read_only=True,
            doc=f"Readback for Input {input_num}, A line (sccm)",
            units="sccm",
        )
        A_ENABLED = pvproperty(
            value=a_enabled,
            dtype=bool,
            read_only=True,
            doc=f"A line enabled for Input {input_num}",
        )
        # Gas flow for line B (only if enabled)
        B_SP = pvproperty(
            value=0.0,
            dtype=float,
            doc=f"Setpoint for Input {input_num}, B line (sccm)",
            units="sccm",
            lower_ctrl_limit=0.0,
            upper_ctrl_limit=max_flow,
        )
        B_RB = pvproperty(
            value=0.0,
            dtype=float,
            read_only=True,
            doc=f"Readback for Input {input_num}, B line (sccm)",
            units="sccm",
        )
        B_ENABLED = pvproperty(
            value=b_enabled,
            dtype=bool,
            read_only=True,
            doc=f"B line enabled for Input {input_num}",
        )

        def __init__(self, *args, flowSMS, **kwargs):
            super().__init__(*args, **kwargs)
            self.flowSMS = flowSMS

        @A_RB.scan(0.5)
        async def A_RB(self, instance, async_lib):
            rb, sp, _ = self.flowSMS.get_input_line_status(input_num, "A")
            await self.A_RB.write(rb)
            await self.A_SP.write(sp)

        @B_RB.scan(0.5)
        async def B_RB(self, instance, async_lib):
            rb, sp, _ = self.flowSMS.get_input_line_status(input_num, "B")
            await self.B_RB.write(rb)
            await self.B_SP.write(sp)

    return InputLine


def flowSMSFactory(gas_config, flowSMS):
    inputClasses = [
        inputLineFactory(input_num, gas_config)
        for input_num in ["1", "2", "3", "4", "5", "6", "7"]
    ]

    class flowSMSIOC(PVGroup):
        Input1 = SubGroup(inputClasses[0], flowSMS=flowSMS)
        Input2 = SubGroup(inputClasses[1], flowSMS=flowSMS)
        Input3 = SubGroup(inputClasses[2], flowSMS=flowSMS)
        Input4 = SubGroup(inputClasses[3], flowSMS=flowSMS)
        Input5 = SubGroup(inputClasses[4], flowSMS=flowSMS)
        Input6 = SubGroup(inputClasses[5], flowSMS=flowSMS)
        Input7 = SubGroup(inputClasses[6], flowSMS=flowSMS)

    return flowSMSIOC


class PulseControl(PVGroup):
    """
    Simulated pulse mode controller.

    Attributes
    ----------
    Line_Select : pvproperty
        Enum: ["A", "B"]
    Line_Mode : pvproperty
        Enum: ["continuous", "pulses"]
    Pulse_Count : pvproperty
        Number of pulses.
    Pulse_Time : pvproperty
        Time per pulse (s).
    Pulse_Trigger : pvproperty
        Write 1 to start pulse sequence.
    Pulse_Status : pvproperty
        Enum: ["idle", "running"]
    """

    Line_Select = pvproperty(
        value=0,
        enum_strings=["A", "B"],
        record="mbbo",
        dtype=ChannelType.ENUM,
        doc="Line select",
    )
    Line_Mode = pvproperty(
        value=0,
        enum_strings=["continuous", "pulses"],
        record="mbbo",
        dtype=ChannelType.ENUM,
        doc="Line mode",
    )
    Pulse_Count = pvproperty(value=1, dtype=int, doc="Number of pulses")
    Pulse_Time = pvproperty(value=1.0, dtype=float, doc="Time per pulse (s)")
    Pulse_Trigger = pvproperty(
        value=0, dtype=int, doc="Write 1 to start pulse sequence"
    )
    Pulse_Status = pvproperty(
        value="idle",
        enum_strings=["idle", "running"],
        record="mbbo",
        dtype=ChannelType.ENUM,
        read_only=True,
        doc="Pulse status (0=idle, 1=running)",
    )

    def __init__(self, *args, gasControl, **kwargs):
        super().__init__(*args, **kwargs)
        self.gasControl = gasControl

    @Line_Select.startup
    async def Line_Select(self, instance, async_lib):
        valve_mode = self.gasControl.get_valve_mode()
        if valve_mode == "Line A Continuous Mode":
            await self.Line_Select.write("A")
            await self.Line_Mode.write("continuous")
        elif valve_mode == "Line B Continuous Mode":
            await self.Line_Select.write("B")
            await self.Line_Mode.write("continuous")
        elif valve_mode == "Pulses Loop Mode A":
            await self.Line_Select.write("A")
            await self.Line_Mode.write("pulses")
        elif valve_mode == "Pulses Loop Mode B":
            await self.Line_Select.write("B")
            await self.Line_Mode.write("pulses")


if __name__ == "__main__":
    parser, split_args = template_arg_parser(
        desc="Simulation IOC Generator", default_prefix="FASSTCAT:"
    )
    parser.add_argument(
        "-c",
        "--config",
        type=str,
        default="config.json",
        help="Path to configuration JSON file (default: config.json)",
    )

    parser.add_argument(
        "-g",
        "--gases",
        type=str,
        default="gases.toml",
        help="Path to gases TOML file (default: gases.toml)",
    )
    args = parser.parse_args()
    ioc_options, run_options = split_args(args)

    config_path, gases_path = get_config_files(args.config, args.gases)

    with open(gases_path, "rb") as f:
        gas_config = tomllib.load(f)

    with open(config_path, "r") as f:
        config = json.load(f)

    gasControl = GasControl(str(config_path), str(gases_path))

    valves = gasControl.valves
    flowSMS = gasControl.flowSMS
    FlowSMSIOCClass = flowSMSFactory(gas_config, flowSMS)
    ioc = FlowSMSIOCClass(**ioc_options)
    run(ioc.pvdb, **run_options)
