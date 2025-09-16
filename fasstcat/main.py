#!/usr/bin/env python3
"""FASST-CAT main entry point for interactive gas control system.

This module provides command line interface to launch an interactive IPython
session with a GasControl object initialized from configuration files.
"""

import argparse
import sys
from pathlib import Path

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
    """Custom IPython prompts for FASST-CAT."""

    def in_prompt_tokens(self, cli=None):
        return [
            (Token.Prompt, "FASST-CAT [In]: "),
        ]

    def out_prompt_tokens(self, cli=None):
        return [
            (Token.Prompt, "FASST-CAT [Out]: "),
        ]


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

        # Set up IPython configuration
        config = load_default_config()
        config.TerminalIPythonApp.prompts_class = FASSTCATPrompts

        # Create a local namespace with the gas control object
        local_ns = {
            "gc": gc,
            "GasControl": GasControl,
            "config_path": str(config_path),
            "gases_path": str(gases_path),
        }

        # Print helpful information
        print("Available objects in this session:")
        print("  gc          - GasControl instance")
        print("  GasControl  - GasControl class")
        print("  config_path - Path to config file")
        print("  gases_path  - Path to gases file")
        print()
        print("Example usage:")
        print("  gc.cont_mode_A()                    # Set continuous mode A")
        print("  gc.flowSMS.setpoints(Ar_A=15)       # Set flow rates")
        print("  gc.valves.display_valve_positions() # Show valve status")
        print("  help(gc)                            # Show all methods")
        print()
        print("Type 'exit()' or press Ctrl+D to quit.")
        print("=" * 40)

        # Start IPython interactive session
        embed(
            config=config,
            user_ns=local_ns,
            banner1="",
            exit_msg="FASST-CAT session ended. Goodbye!",
        )

    except Exception as e:
        print(f"Error initializing gas control system: {e}")
        print("Please check your configuration files and try again.")
        sys.exit(1)


if __name__ == "__main__":
    main()
