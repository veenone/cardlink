# PC/SC Smart Card Reader Setup Guide

This guide provides platform-specific instructions for setting up PC/SC (Personal Computer/Smart Card) support for UICC card provisioning.

## Table of Contents

- [Linux Setup](#linux-setup)
- [macOS Setup](#macos-setup)
- [Windows Setup](#windows-setup)
- [Verifying Installation](#verifying-installation)
- [Troubleshooting](#troubleshooting)
- [Supported Readers](#supported-readers)

## Linux Setup

### Prerequisites

Linux requires the **pcscd** daemon (PC/SC Daemon) and appropriate drivers.

### Ubuntu/Debian

```bash
# Install PC/SC daemon and USB support
sudo apt-get update
sudo apt-get install pcscd pcsc-tools libpcsclite1 libpcsclite-dev

# Install USB CCID driver for most readers
sudo apt-get install libccid

# Start the PC/SC daemon
sudo systemctl start pcscd
sudo systemctl enable pcscd

# Verify daemon is running
sudo systemctl status pcscd
```

### Fedora/RHEL/CentOS

```bash
# Install PC/SC daemon and tools
sudo dnf install pcsc-lite pcsc-lite-ccid pcsc-tools

# Start the PC/SC daemon
sudo systemctl start pcscd
sudo systemctl enable pcscd

# Verify daemon is running
sudo systemctl status pcscd
```

### Arch Linux

```bash
# Install PC/SC support
sudo pacman -S pcsclite ccid

# Start the PC/SC daemon
sudo systemctl start pcscd.service
sudo systemctl enable pcscd.service
```

### User Permissions

Add your user to the `pcscd` or `scard` group to access readers without root:

```bash
# Check which group owns the PC/SC socket
ls -l /var/run/pcscd/

# Add user to appropriate group (usually pcscd or scard)
sudo usermod -a -G pcscd $USER

# Log out and back in for group changes to take effect
```

## macOS Setup

macOS includes built-in PC/SC support (part of the Smartcard Services framework). No additional installation is required.

### Verify PC/SC Support

```bash
# Check if PC/SC is available
system_profiler SPUSBDataType | grep -i "smart card"

# List readers (after connecting a reader)
pcsctest
```

### Installing pyscard

With Homebrew:

```bash
# Install SWIG (required for pyscard compilation)
brew install swig

# Install Python development tools if needed
brew install python@3.11

# Install pyscard via pip
pip install pyscard
```

## Windows Setup

Windows includes built-in Smart Card support through **WinSCard.dll** (Windows Smart Card API). No additional installation is required for the OS.

### Requirements

- Windows 7 or later
- Smart card reader with Windows drivers installed (usually automatic via Windows Update)

### Driver Installation

Most modern smart card readers are automatically recognized by Windows:

1. Connect your smart card reader via USB
2. Windows will automatically search for and install drivers
3. Check Device Manager → Smart card readers to verify

### Manual Driver Installation

If Windows doesn't automatically install drivers:

1. Download drivers from your reader manufacturer's website:
   - **Gemalto/Thales**: https://www.thalesgroup.com/
   - **Identiv/SCM**: https://www.identiv.com/
   - **Omnikey/HID**: https://www.hidglobal.com/
   - **ACS**: http://www.acs.com.hk/

2. Run the driver installer as Administrator
3. Restart your computer if prompted

### Installing pyscard

```cmd
# Install Visual C++ Build Tools (required for pyscard compilation)
# Download from: https://visualstudio.microsoft.com/downloads/
# Select "Desktop development with C++"

# Install pyscard via pip
pip install pyscard
```

## Verifying Installation

### Check for Connected Readers

```bash
# Using pcsc_scan (Linux/macOS)
pcsc_scan

# Using Python
python3 -c "from smartcard.System import readers; print(readers())"
```

Expected output:
```
[<smartcard.pcsc.PCSCReader.PCSCReader object at 0x...>]
```

### Test Card Connection

```bash
# Using cardlink provisioner
gp-provision list

# Expected output:
# Available PC/SC readers:
#   [0] Gemalto PC Twin Reader 00 00
#       Card present: Yes
#       ATR: 3B 9F 96 80 1F C7 80 31 A0 73 BE 21 13 67 43 20 07 18 00 00 01 A5
```

### Test APDU Communication

```python
from cardlink.provisioner import PCSCClient, APDUInterface

# Connect to first available reader
client = PCSCClient()
readers = client.list_readers()
print(f"Found {len(readers)} reader(s)")

if readers:
    client.connect(readers[0].name)
    print(f"Connected to: {readers[0].name}")
    print(f"ATR: {client.card_info.atr.hex()}")

    # Send SELECT ISD command
    apdu = APDUInterface(client.transmit)
    response = apdu.select_by_aid("A0000000151000")
    print(f"ISD select: SW={response.sw:04X} ({response.status_message})")

    client.disconnect()
```

## Troubleshooting

### Linux: "No readers found"

**Problem**: `pcsc_scan` or Python can't find any readers

**Solutions**:

1. Check if pcscd daemon is running:
   ```bash
   sudo systemctl status pcscd
   ```

2. Restart the daemon:
   ```bash
   sudo systemctl restart pcscd
   ```

3. Check USB connection:
   ```bash
   lsusb | grep -i smart
   ```

4. Check permissions:
   ```bash
   ls -l /var/run/pcscd/
   # Ensure your user can access the socket
   ```

5. Try running with sudo to rule out permission issues:
   ```bash
   sudo python3 -c "from smartcard.System import readers; print(readers())"
   ```

### Linux: "Resource busy" or "Sharing violation"

**Problem**: Another application is using the reader

**Solutions**:

1. Check for other PC/SC applications:
   ```bash
   ps aux | grep -i pcsc
   lsof | grep pcscd
   ```

2. Stop conflicting services:
   ```bash
   sudo systemctl stop pcscd
   sudo systemctl start pcscd
   ```

### macOS: "No module named 'smartcard'"

**Problem**: pyscard not installed correctly

**Solutions**:

1. Install SWIG first:
   ```bash
   brew install swig
   ```

2. Reinstall pyscard:
   ```bash
   pip uninstall pyscard
   pip install --no-cache-dir pyscard
   ```

### Windows: "Failed to load SCARD library"

**Problem**: PC/SC subsystem not available

**Solutions**:

1. Ensure Smart Card service is running:
   ```cmd
   sc query SCardSvr
   ```

2. Start the service if stopped:
   ```cmd
   sc start SCardSvr
   ```

3. Set service to automatic startup:
   ```cmd
   sc config SCardSvr start= auto
   ```

### Windows: "Failed to build pyscard"

**Problem**: Missing Visual C++ compiler

**Solutions**:

1. Install Microsoft C++ Build Tools:
   - Download from https://visualstudio.microsoft.com/downloads/
   - Select "Desktop development with C++"

2. Alternatively, use pre-built wheels:
   ```cmd
   pip install --only-binary :all: pyscard
   ```

### Card Not Detected

**Problem**: Reader found but card not detected

**Solutions**:

1. **Clean the card**: Wipe the contact surface with a soft cloth

2. **Reinsert the card**: Remove and reinsert firmly

3. **Try another reader**: Test with a different reader if available

4. **Check card type**: Ensure card is a contact card (not contactless-only)

5. **Verify with ATR**:
   ```bash
   pcsc_scan
   # Should show ATR if card is detected
   ```

### Python Import Errors

**Problem**: `ModuleNotFoundError: No module named 'smartcard'`

**Solutions**:

1. Install pyscard in correct environment:
   ```bash
   # For system Python
   pip install pyscard

   # For virtual environment
   source venv/bin/activate  # or venv\Scripts\activate on Windows
   pip install pyscard
   ```

2. For cardlink installation:
   ```bash
   pip install -e ".[pcsc]"
   ```

## Supported Readers

The following readers have been tested and work with cardlink:

### Verified Compatible Readers

| Manufacturer | Model | Interface | Notes |
|--------------|-------|-----------|-------|
| Gemalto/Thales | PC Twin Reader | USB | Full support |
| Gemalto/Thales | IDBridge CT30 | USB | Full support |
| Identiv/SCM | SCR3310 | USB | Full support |
| Identiv/SCM | SCL011 | USB | Full support |
| Omnikey/HID | 3121 | USB | Full support |
| Omnikey/HID | 5321 | USB | Full support |
| ACS | ACR38U | USB | Full support |
| ACS | ACR122U | USB | Contact mode only |

### Likely Compatible Readers

Any PC/SC compliant reader with CCID (Chip Card Interface Device) support should work. Look for:

- USB CCID certification
- ISO 7816 contact card support
- PC/SC driver availability

### Not Recommended

- **Contactless-only readers**: Cannot provision UICC cards (contact required)
- **Legacy serial readers**: Limited OS support, slow performance
- **Proprietary protocol readers**: May not support standard PC/SC

## Additional Resources

### Official Documentation

- **PC/SC Workgroup**: https://pcscworkgroup.com/
- **pyscard Documentation**: https://pyscard.sourceforge.io/
- **pcsc-lite**: https://pcsclite.apdu.fr/

### Linux PC/SC Resources

- **Debian Wiki**: https://wiki.debian.org/Smartcards
- **Arch Wiki**: https://wiki.archlinux.org/title/PC/SC
- **CCID Driver**: https://ccid.apdu.fr/

### Windows Smart Card Resources

- **Microsoft Smart Card Documentation**: https://docs.microsoft.com/en-us/windows-hardware/drivers/smartcard/

### Testing Tools

- **pcsc_scan**: Real-time ATR display and reader monitoring
- **pcsctest**: PC/SC API testing utility
- **opensc-tool**: OpenSC smart card utility
- **gp**: GlobalPlatform command-line tool

## Getting Help

If you encounter issues not covered in this guide:

1. **Check reader compatibility**: Verify your reader supports ISO 7816 contact cards
2. **Test with system tools**: Use `pcsc_scan` to verify reader/card detection
3. **Check logs**:
   - Linux: `journalctl -u pcscd -f`
   - Windows: Event Viewer → Applications and Services → Microsoft-Windows-SmartCard
4. **File an issue**: https://github.com/yourusername/cardlink/issues

Include in your issue:
- Operating system and version
- Reader model
- Output of `pcsc_scan` or equivalent
- Card ATR (if detected)
- Full error message
