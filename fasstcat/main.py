#!/usr/bin/env python3
"""FASST-CAT main entry point for interactive gas control system.

This module provides command line interface to launch an interactive IPython
session with a GasControl object initialized from configuration files.
"""

import argparse
import sys
from pathlib import Path
from typing import Union

try:
    from IPython import embed
    from IPython.terminal.prompts import Prompts, Token
    from IPython.terminal.ipapp import load_default_config
except ImportError:
    print("Error: IPython is required but not installed.")
    print("Please install it with: pip install ipython")
    sys.exit(1)

from fasstcat.gasControl import GasControl


class FASSTCATPrompts(Prompts):
    """Custom IPython prompts for FASST-CAT that preserve default styling."""

    def in_prompt_tokens(self, cli=None):
        # Simple approach: just prepend FASST-CAT to the default prompt
        return [
            (Token.Prompt, "FASST-CAT "),
            (Token.Prompt.Number, "In"),
            (Token.Prompt, "[%d]: " % self.shell.execution_count),
        ]

    # def out_prompt_tokens(self, cli=None):
    #     # Simple approach: just prepend FASST-CAT to the default prompt
    #     return [
    #         (Token.Prompt, "FASST-CAT "),
    #         (Token.Prompt.Number, "Out"),
    #         (Token.Prompt, "[%d]: " % self.shell.execution_count),
    #     ]


def help_gc():
    """Show help for GasControl methods."""
    print("FASST-CAT Objects:")
    print("=" * 40)
    print("  gc          - GasControl instance")
    print("  gc.valves   - Valves instance")
    print("  gc.flowSMS  - FlowSMS instance")
    print("  gc.eurotherm - Eurotherm instance")
    print()
    print("FASST-CAT Easy-Access Methods:")
    print("=" * 40)
    print("Valve Control:")
    print("  set_valve_A(position)     # Set valve A position")
    print("  set_valve_B(position)     # Set valve B position")
    print("  set_valve_C(position)     # Set valve C position")
    print()
    print("Operation Modes:")
    print("  set_loop_A_continuous()         # Continuous mode A")
    print("  set_loop_B_continuous()         # Continuous mode B")
    print("  set_loop_A_pulsed()  # Pulses loop mode A")
    print("  set_loop_B_pulsed()  # Pulses loop mode B")
    print()
    print("Pulses Control:")
    print("  send_loop_A_pulses(pulses, time_bp) # Send pulses to loop A")
    print("  send_loop_B_pulses(pulses, time_bp) # Send pulses to loop B")
    print("  send_valve_A_pulses(pulses, time_vo, time_bp) # Send pulses to valve A")
    print()
    print("Flow Control:")
    print("  set_flowrate(gas, flow) # Set flow rate for a given gas")
    print()
    print("System Status:")
    print("  status()          # Show system status")
    print("  flow_status()     # Show flow status")
    print("  pressure_report() # Show pressure report")
    print("  gases()           # Show available gases")
    print("  help(gc)          # Show all methods of GasControl object")


def status():
    """Show current system status."""
    # This will be called from within the IPython session, so we can access gc directly
    try:
        # Get the current IPython instance
        from IPython import get_ipython

        ip = get_ipython()
        if ip and "gc" in ip.user_ns:
            print("FASST-CAT System Status:")
            print("=" * 30)
            gc = ip.user_ns["gc"]
            gc.valves.display_valve_positions()
            print()
            gc.flowSMS.status()
        else:
            print("GasControl not available")
    except Exception as e:
        print(f"Error getting status: {e}")


def main():
    """Main entry point for FASST-CAT interactive session."""
    parser = argparse.ArgumentParser(
        description="FASST-CAT Catalysis control system - Interactive mode",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py                                    # Use default config files
  python main.py -c my_config.json -g my_gases.toml # Use custom config files
  python main.py --help                             # Show this help message
        """,
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

    parser.add_argument("--version", action="version", version="FASST-CAT 3.0")

    args = parser.parse_args()

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
    config_path_abs = Path(args.config)
    gases_path_abs = Path(args.gases)

    if config_path_abs.exists() and gases_path_abs.exists():
        # Both files exist as specified
        config_path = config_path_abs
        gases_path = gases_path_abs
    else:
        # Determine search paths for config files
        if args.config == "config.json" and args.gases == "gases.toml":
            # Use default search order: config/ -> examples/
            config_search_paths = [config_dir, examples_dir]
            gases_search_paths = [config_dir, examples_dir]
        else:
            # Try to find them in the project directories
            config_search_paths = [project_root, config_dir, examples_dir]
            gases_search_paths = [project_root, config_dir, examples_dir]

        # Find configuration files
        config_path = find_config_file(args.config, config_search_paths)
        gases_path = find_config_file(args.gases, gases_search_paths)

    if config_path is None:
        print(f"Error: Configuration file '{args.config}' not found.")
        print("Searched in:")
        for path in config_search_paths:
            print(f"  - {path}")
        print(f"\nPlease copy example files from {examples_dir} to {config_dir}")
        print("or provide a valid path to your config.json file.")
        sys.exit(1)

    if gases_path is None:
        print(f"Error: Gases file '{args.gases}' not found.")
        print("Searched in:")
        for path in gases_search_paths:
            print(f"  - {path}")
        print(f"\nPlease copy example files from {examples_dir} to {config_dir}")
        print("or provide a valid path to your gases.toml file.")
        sys.exit(1)

    print("FASST-CAT Catalysis Control System")
    print("=" * 40)
    print(f"Loading configuration from: {config_path}")
    print(f"Loading gases from: {gases_path}")
    print()

    try:
        # Initialize GasControl with provided config files
        print("Initializing gas control system...")
        gc = GasControl(str(config_path), str(gases_path))
        print("✓ Gas control system initialized successfully!")
        print()

        # Set up IPython configuration for better experience
        config = load_default_config()
        config.TerminalInteractiveShell.autocall = 2
        config.TerminalInteractiveShell.autoindent = True
        config.TerminalInteractiveShell.automagic = True
        config.TerminalInteractiveShell.simple_prompt = False
        config.TerminalInteractiveShell.prompts_class = FASSTCATPrompts

        # Create a local namespace with the gas control object and common imports
        import json
        import time

        # Try to import optional scientific packages
        try:
            import numpy as np

            numpy_available = True
        except ImportError:
            numpy_available = False

        try:
            import matplotlib.pyplot as plt

            matplotlib_available = True
        except ImportError:
            matplotlib_available = False

        local_ns = {
            "gc": gc,
            "GasControl": GasControl,
            "config_path": str(config_path),
            "gases_path": str(gases_path),
            "Path": Path,
            "json": json,
            "time": time,
            "help_gc": help_gc,
            "status": status,
        }

        gc_functions = [
            ["valve_A", "set_valve_A"],
            ["valve_B", "set_valve_B"],
            ["valve_C", "set_valve_C"],
            ["cont_mode_A", "set_loop_A_continuous"],
            ["cont_mode_B", "set_loop_B_continuous"],
            ["pulses_loop_mode_A", "set_loop_A_pulsed"],
            ["pulses_loop_mode_B", "set_loop_B_pulsed"],
            ["send_pulses_loop_A", "send_loop_A_pulses"],
            ["send_pulses_loop_B", "send_loop_B_pulses"],
            ["send_pulses_valve_A", "send_valve_A_pulses"],
        ]

        sms_functions = [
            "set_flowrate",
            "pressure_report",
            ["print_gases", "gases"],
            ["status", "flow_status"],
        ]

        for function_tuple in gc_functions:
            if isinstance(function_tuple, Union[list, tuple]):
                function = function_tuple[0]
                function_name = function_tuple[1]
            else:
                function = function_tuple
                function_name = function_tuple
            local_ns[function_name] = getattr(gc, function)
        for function_tuple in sms_functions:
            if isinstance(function_tuple, Union[list, tuple]):
                function = function_tuple[0]
                function_name = function_tuple[1]
            else:
                function = function_tuple
                function_name = function_tuple
            local_ns[function_name] = getattr(gc.flowSMS, function)
        # Add optional imports if available
        if numpy_available:
            local_ns["np"] = np
        if matplotlib_available:
            local_ns["plt"] = plt

        # Print helpful information
        print("🚀 FASST-CAT Interactive Environment Ready!")
        print("=" * 50)
        print("📚 Available objects:")
        print("  gc          - GasControl instance")
        print("  GasControl  - GasControl class")
        print("  config_path - Path to config file")
        print("  gases_path  - Path to gases file")
        print("  Path, json, time - Common utilities")
        if numpy_available:
            print("  np          - NumPy")
        if matplotlib_available:
            print("  plt         - Matplotlib")
        print()
        print("🛠️  Helper functions:")
        print("  help_gc()   - Show GasControl method help")
        print("  status()    - Show current system status")
        print()
        print("💡 Example usage:")
        print("  gc.cont_mode_A()                    # Set continuous mode A")
        print("  gc.flowSMS.setpoints(Ar_A=15)       # Set flow rates")
        print("  gc.valves.display_valve_positions() # Show valve status")
        print("  help_gc()                           # Show all methods")
        print()
        print("Type 'exit()' or press Ctrl+D to quit.")
        print("=" * 50)

        # Start IPython interactive session with enhanced configuration
        embed(
            config=config,
            user_ns=local_ns,
            banner1="",
            exit_msg="FASST-CAT session ended. Goodbye!",
            using=False,  # Don't use the current namespace
        )

    except Exception as e:
        print(f"Error initializing gas control system: {e}")
        print("Please check your configuration files and try again.")
        sys.exit(1)


if __name__ == "__main__":
    main()
