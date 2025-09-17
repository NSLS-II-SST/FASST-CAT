import asyncio
from pathlib import Path
from caproto.server import PVGroup, pvproperty, SubGroup, template_arg_parser, run
from caproto._data import ChannelType
from fasstcat.utils import get_config_files
from fasstcat.flowSMS import FlowSMS

import tomllib
import json


def inputLineFactory(input_num, gas_config):
    available_gases = gas_config.get("available_gases", [])
    gas_details = gas_config.get("gas_details", {})
    a_enabled = gas_config.get("a_enabled", False)
    b_enabled = gas_config.get("b_enabled", False)

    # Determine flow limits based on available gases
    # Use the highest upper limit among available gases
    max_flow = 0.0
    for gas_name, details in gas_details.items():
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
        Gas_Name = (
            pvproperty(
                value=available_gases[0] if available_gases else "",
                dtype=str,
                max_length=20,
                read_only=True,
                doc="Current gas name based on selection",
            ),
        )
        # Gas flow for line A (only if enabled)
        A_SP = (
            pvproperty(
                value=0.0,
                dtype=float,
                doc=f"Setpoint for Input {input_num}, A line (sccm)",
                units="sccm",
                lower_ctrl_limit=0.0,
                upper_ctrl_limit=max_flow,
            ),
        )
        A_RB = (
            pvproperty(
                value=0.0,
                dtype=float,
                read_only=True,
                doc=f"Readback for Input {input_num}, A line (sccm)",
                units="sccm",
            ),
        )
        A_ENABLED = (
            pvproperty(
                value=a_enabled,
                dtype=bool,
                read_only=True,
                doc=f"A line enabled for Input {input_num}",
            ),
        )
        # Gas flow for line B (only if enabled)
        B_SP = (
            pvproperty(
                value=0.0,
                dtype=float,
                doc=f"Setpoint for Input {input_num}, B line (sccm)",
                units="sccm",
                lower_ctrl_limit=0.0,
                upper_ctrl_limit=max_flow,
            ),
        )
        B_RB = (
            pvproperty(
                value=0.0,
                dtype=float,
                read_only=True,
                doc=f"Readback for Input {input_num}, B line (sccm)",
                units="sccm",
            ),
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

        @A_RB.startup
        async def A_RB(self, instance, async_lib):
            rb, sp, _ = self.flowSMS.get_gas_status(self.Gas_Name.value, "A")
            self.A_RB.write(rb)
            self.A_SP.write(sp)

        @B_RB.startup
        async def B_RB(self, instance, async_lib):
            rb, sp, _ = self.flowSMS.get_gas_status(self.Gas_Name.value, "B")
            self.B_RB.write(rb)
            self.B_SP.write(sp)

    return InputLine


if __name__ == "__main__":
    parser, split_args = template_arg_parser(
        desc="Simulation IOC Generator", default_prefix="SIM:"
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

    flowSMS = FlowSMS(config, gas_config)
    InputLineClass = inputLineFactory(1, gas_config)
    ioc = InputLineClass(flowSMS=flowSMS, **ioc_options)
    run(ioc.pvdb, **run_options)
