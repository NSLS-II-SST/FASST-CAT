# FASST-CAT Configuration Directory

This directory is where you should place your custom configuration files.

## Configuration Files

- `config.json` - Main system configuration (serial ports, network settings, etc.)
- `gases.toml` - Gas flow controller and valve configuration

## Example Files

Example configuration files are available in the `examples/` directory:
- `examples/config.json` - Example system configuration
- `examples/gases.toml` - Example gas configuration

## Usage

1. Copy the example files to this directory:
   ```bash
   cp examples/config.json config/
   cp examples/gases.toml config/
   ```

2. Edit the files to match your system configuration

3. Run FASST-CAT:
   ```bash
   pixi run interactive
   ```

## File Locations

FASST-CAT will look for configuration files in the following order:
1. Files specified via command line arguments (`-c` and `-g`)
2. Files in the `config/` directory
3. Example files in the `examples/` directory (as fallback)
