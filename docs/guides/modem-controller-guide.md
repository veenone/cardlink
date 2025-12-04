# Modem Controller User Guide

## Overview

The Modem Controller module provides comprehensive management for IoT cellular modems via serial communication. It supports modem discovery, AT command execution, network configuration, BIP monitoring, SMS triggers, and QXDM diagnostics for Qualcomm-based modems.

## Table of Contents

1. [Quick Start](#quick-start)
2. [Prerequisites](#prerequisites)
3. [Modem Discovery](#modem-discovery)
4. [Modem Information](#modem-information)
5. [AT Commands](#at-commands)
6. [Network Management](#network-management)
7. [BIP Monitoring](#bip-monitoring)
8. [SMS Triggers](#sms-triggers)
9. [Profile Management](#profile-management)
10. [QXDM Diagnostics](#qxdm-diagnostics)
11. [API Usage](#api-usage)
12. [Troubleshooting](#troubleshooting)

---

## Quick Start

### Installation

```bash
# Install with modem support
pip install -e ".[modem]"

# Or install pyserial separately
pip install pyserial

# Verify installation
gp-modem --help
```

### Basic Usage

```bash
# List connected modems
gp-modem list

# Get modem information
gp-modem info /dev/ttyUSB2

# Send AT command
gp-modem at /dev/ttyUSB2 ATI

# Monitor BIP events
gp-modem monitor /dev/ttyUSB2
```

---

## Prerequisites

### Hardware Requirements

- **IoT Cellular Modem** (USB or serial)
  - Quectel (EC25, EG25, BG96, etc.)
  - Sierra Wireless
  - Simcom
  - Telit
  - u-blox
  - Other AT command-compatible modems

- **USB/Serial Connection**
  - USB-to-serial adapter (if needed)
  - Appropriate drivers installed

### Software Requirements

```bash
# Python 3.9+
python --version

# pyserial for serial communication
pip install pyserial

# Optional: For enhanced terminal output
pip install rich
```

### Verify Setup

```bash
# Check serial ports
gp-modem ports

# Should show available ports
# Example output:
# /dev/ttyUSB0  Quectel EC25  2c7c:0125  Quectel
# /dev/ttyUSB1  Quectel EC25  2c7c:0125  Quectel
# /dev/ttyUSB2  Quectel EC25  2c7c:0125  Quectel
```

---

## Modem Discovery

### List Connected Modems

```bash
# Basic listing
gp-modem list

# JSON output (for scripting)
gp-modem list --json

# Verbose output
gp-modem -v list
```

**Example Output:**
```
Connected Modems
┏━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━┓
┃ Port         ┃ Manufacturer ┃ Model      ┃ IMEI      ┃
┡━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━┩
│ /dev/ttyUSB2 │ Quectel      │ EC25       │ ***5678   │
│ /dev/ttyUSB6 │ Sierra       │ MC7455     │ ***1234   │
└──────────────┴──────────────┴────────────┴───────────┘

Total: 2 modem(s)
```

### List Serial Ports

```bash
# Show all serial ports (including non-modems)
gp-modem ports
```

**Example Output:**
```
Serial Ports
┏━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━━━┓
┃ Port         ┃ Description          ┃ VID:PID  ┃ Manufacturer ┃
┡━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━━━┩
│ /dev/ttyUSB0 │ Quectel EC25         │ 2c7c:0125│ Quectel      │
│ /dev/ttyUSB1 │ Quectel EC25         │ 2c7c:0125│ Quectel      │
│ /dev/ttyUSB2 │ Quectel EC25         │ 2c7c:0125│ Quectel      │
│ /dev/ttyUSB3 │ FTDI USB Serial      │ 0403:6001│ FTDI         │
└──────────────┴──────────────────────┴──────────┴──────────────┘
```

---

## Modem Information

### Complete Information

```bash
# Show all information
gp-modem info /dev/ttyUSB2

# Show only modem hardware info
gp-modem info /dev/ttyUSB2 --modem

# Show only SIM card info
gp-modem info /dev/ttyUSB2 --sim

# Show only network status
gp-modem info /dev/ttyUSB2 --network

# JSON output
gp-modem info /dev/ttyUSB2 --json
```

**Example Output:**
```
Modem Information
┏━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Property     ┃ Value                    ┃
┡━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ Manufacturer │ Quectel                  │
│ Model        │ EC25                     │
│ Firmware     │ EC25EFAR06A03M4G         │
│ IMEI         │ 867698041234567          │
│ Vendor       │ QUECTEL                  │
└──────────────┴──────────────────────────┘

SIM Information
┏━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Property    ┃ Value                  ┃
┡━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━┩
│ Status      │ READY                  │
│ ICCID       │ 8901234567890123456    │
│ IMSI        │ 310260123456789        │
│ MSISDN      │ +1234567890            │
│ MCC/MNC     │ 310/260                │
└─────────────┴────────────────────────┘

Network Information
┏━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━┓
┃ Property         ┃ Value            ┃
┡━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━┩
│ Registration     │ REGISTERED_HOME  │
│ Operator         │ T-Mobile USA     │
│ Network Type     │ LTE              │
│ APN              │ fast.t-mobile.com│
│ RSSI             │ -75 dBm          │
│ RSRP             │ -98 dBm          │
│ SINR             │ 13 dB            │
│ RSRQ             │ -10 dB           │
│ IP Address       │ 10.123.45.67     │
│ Cell ID          │ 12AB34CD         │
│ TAC              │ 5678             │
└──────────────────┴──────────────────┘
```

---

## AT Commands

### Send AT Commands

```bash
# Basic AT command
gp-modem at /dev/ttyUSB2 ATI

# Query SIM status
gp-modem at /dev/ttyUSB2 "AT+CPIN?"

# Get signal quality
gp-modem at /dev/ttyUSB2 "AT+CSQ"

# Get operator
gp-modem at /dev/ttyUSB2 "AT+COPS?"

# With custom timeout
gp-modem at /dev/ttyUSB2 "AT+CGDCONT?" --timeout 10
```

**Example Output:**
```
Command: AT+CPIN?
Result: OK

Response:
  +CPIN: READY
```

### Common AT Commands

```bash
# Modem Identification
gp-modem at /dev/ttyUSB2 "AT+CGMI"  # Manufacturer
gp-modem at /dev/ttyUSB2 "AT+CGMM"  # Model
gp-modem at /dev/ttyUSB2 "AT+CGMR"  # Firmware version
gp-modem at /dev/ttyUSB2 "AT+CGSN"  # IMEI

# SIM Information
gp-modem at /dev/ttyUSB2 "AT+CPIN?" # PIN status
gp-modem at /dev/ttyUSB2 "AT+QCCID" # ICCID (Quectel)
gp-modem at /dev/ttyUSB2 "AT+CIMI"  # IMSI
gp-modem at /dev/ttyUSB2 "AT+CNUM"  # MSISDN

# Network Status
gp-modem at /dev/ttyUSB2 "AT+CREG?" # Registration status
gp-modem at /dev/ttyUSB2 "AT+COPS?" # Operator
gp-modem at /dev/ttyUSB2 "AT+CSQ"   # Signal quality

# PDP Context
gp-modem at /dev/ttyUSB2 "AT+CGDCONT?" # List contexts
gp-modem at /dev/ttyUSB2 "AT+CGACT?"   # Context state
gp-modem at /dev/ttyUSB2 "AT+CGPADDR"  # IP address
```

---

## Network Management

### Configure APN

```bash
# Set APN
gp-modem configure-apn /dev/ttyUSB2 "fast.t-mobile.com"

# With username and password
gp-modem configure-apn /dev/ttyUSB2 "internet" \
  --username "user" \
  --password "pass"
```

### Test Connectivity

```bash
# Ping host
gp-modem ping /dev/ttyUSB2 8.8.8.8

# Custom ping count
gp-modem ping /dev/ttyUSB2 google.com --count 10
```

**Example Output:**
```
Pinging 8.8.8.8 from /dev/ttyUSB2

Ping statistics for 8.8.8.8:
  Packets: Sent = 4, Received = 4, Lost = 0
  Round-trip times: min=45ms, max=89ms, avg=67ms
```

### Network Configuration Example

```bash
# Complete network setup
#!/bin/bash

PORT="/dev/ttyUSB2"
APN="fast.t-mobile.com"

# Configure APN
gp-modem configure-apn $PORT $APN

# Verify configuration
gp-modem at $PORT "AT+CGDCONT?"

# Check IP address
gp-modem at $PORT "AT+CGPADDR"

# Test connectivity
gp-modem ping $PORT 8.8.8.8
```

---

## BIP Monitoring

### Real-time Monitoring

```bash
# Monitor BIP events
gp-modem monitor /dev/ttyUSB2

# Monitor for specific duration (seconds)
gp-modem monitor /dev/ttyUSB2 --duration 300

# Verbose output
gp-modem -v monitor /dev/ttyUSB2
```

**Example Output:**
```
Monitoring BIP events on /dev/ttyUSB2
Press Ctrl+C to stop

BIP Event: OPEN_CHANNEL
  Channel ID: 1
  Destination: 192.168.1.100:8443
  Buffer Size: 1500

BIP Event: SEND_DATA
  Channel ID: 1
  Raw PDU: D0818106...

BIP Event: RECEIVE_DATA
  Channel ID: 1

BIP Event: CLOSE_CHANNEL
  Channel ID: 1

^C
Interrupted

Monitoring stopped
```

### BIP Event Types

The monitor detects these BIP proactive commands:
- **OPEN_CHANNEL** - Opens data channel
- **CLOSE_CHANNEL** - Closes data channel
- **SEND_DATA** - Sends data over channel
- **RECEIVE_DATA** - Receives data from channel
- **GET_CHANNEL_STATUS** - Queries channel status

---

## SMS Triggers

### Send SMS Trigger

```bash
# Send raw PDU
gp-modem trigger /dev/ttyUSB2 "0001000B91...PDU..."

# Verbose output shows delivery status
gp-modem -v trigger /dev/ttyUSB2 "PDU_HEX_STRING"
```

**Example Output:**
```
Sending SMS PDU to /dev/ttyUSB2
SMS sent successfully
Message Reference: 123
```

### SMS PDU Format

The SMS trigger uses PDU mode (AT+CMGF=0) for sending:
- **SMS-PP Data Download** - Protocol ID 0x7F
- **Class 2 Messages** - Data Coding Scheme 0x16
- **OTA Triggers** - Contains proactive command

**Example:**
```
00           # SMSC length (use default)
11           # First octet (SMS-SUBMIT)
00           # Message reference
0B91         # Destination length + type
1234567890   # Destination number
7F           # Protocol ID (SIM data download)
16           # Data coding (Class 2, 8-bit)
0A           # User data length
D081810612345678  # User data (command)
```

---

## Profile Management

### Save Modem Profile

```bash
# Save current configuration
gp-modem profile save /dev/ttyUSB2 my_modem_baseline

# Overwrite existing
gp-modem profile save /dev/ttyUSB2 my_modem_baseline --force
```

**Output:**
```
Profile saved: /home/user/.cardlink/profiles/modem/my_modem_baseline.json
  Port: /dev/ttyUSB2
  Model: EC25
  IMEI: 867698041234567
```

### Load Profile

```bash
# Display saved profile
gp-modem profile load my_modem_baseline

# Export as JSON
gp-modem profile load my_modem_baseline --json
```

### List Profiles

```bash
# List all saved profiles
gp-modem profile list
```

**Example Output:**
```
Saved Modem Profiles
┏━━━━━━━━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━━━━━━━━┓
┃ Name             ┃ Model  ┃ IMEI    ┃ Saved          ┃
┡━━━━━━━━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━━━━━━━┩
│ my_modem_baseline│ EC25   │ ***5678 │ 2025-12-04 10:30│
│ after_update     │ EC25   │ ***5678 │ 2025-12-04 11:45│
│ production_config│ MC7455 │ ***1234 │ 2025-12-03 14:20│
└──────────────────┴────────┴─────────┴────────────────┘

Total: 3 profile(s)
```

### Compare Profiles

```bash
# Compare two saved profiles
gp-modem profile compare my_modem_baseline after_update
```

**Example Output:**
```
Comparing Profiles
  Profile 1: my_modem_baseline
  Profile 2: after_update

Modem Differences
┏━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━┓
┃ Field           ┃ Profile 1        ┃ Profile 2        ┃
┡━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━┩
│ firmware_version│ EC25EFAR06A03M4G │ EC25EFAR06A04M4G │
└─────────────────┴──────────────────┴──────────────────┘

Network Differences
┏━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━┓
┃ Field      ┃ Profile 1       ┃ Profile 2       ┃
┡━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━┩
│ rssi       │ -75             │ -82             │
│ operator   │ T-Mobile USA    │ AT&T            │
└────────────┴─────────────────┴─────────────────┘
```

### Delete Profile

```bash
# Delete profile with confirmation
gp-modem profile delete my_modem_baseline

# Skip confirmation
gp-modem profile delete my_modem_baseline --yes
```

---

## QXDM Diagnostics

QXDM (Qualcomm eXtensible Diagnostic Monitor) support for Qualcomm-based modems.

### Check QXDM Availability

```bash
# Check if QXDM is available
gp-modem diag /dev/ttyUSB2
```

**Output:**
```
QXDM Available: Yes
DM Port: /dev/ttyUSB0
```

### Start Diagnostic Logging

```bash
# Start logging
gp-modem diag /dev/ttyUSB2 --start
```

**Output:**
```
Starting diagnostic logging...
Diagnostic logging started
```

### Stop Diagnostic Logging

```bash
# Stop logging
gp-modem diag /dev/ttyUSB2 --stop
```

### Export Diagnostic Log

```bash
# Export captured logs
gp-modem diag /dev/ttyUSB2 --export diagnostics.qmdl
```

**Output:**
```
Exporting diagnostic log to diagnostics.qmdl...
Log exported: diagnostics.qmdl
```

### QXDM Workflow Example

```bash
#!/bin/bash

PORT="/dev/ttyUSB2"
LOG_FILE="test_$(date +%Y%m%d_%H%M%S).qmdl"

# Start logging
gp-modem diag $PORT --start

# Run your OTA test
echo "Running OTA test..."
sleep 60

# Stop logging
gp-modem diag $PORT --stop

# Export logs
gp-modem diag $PORT --export "$LOG_FILE"

echo "Diagnostic log saved: $LOG_FILE"
```

---

## API Usage

### Python API Examples

#### Basic Modem Control

```python
import asyncio
from cardlink.modem import ModemController

async def basic_example():
    """Basic modem control example."""

    # Create controller
    controller = ModemController()

    # Discover modems
    modems = await controller.discover_modems()
    print(f"Found {len(modems)} modem(s)")

    for modem_info in modems:
        print(f"  {modem_info.port}: {modem_info.model}")

    # Get modem instance
    modem = await controller.get_modem("/dev/ttyUSB2")

    # Get profile
    profile = await modem.get_profile()
    print(f"IMEI: {profile.modem.imei}")
    print(f"Network: {profile.network.operator_name}")

    # Close all connections
    await controller.close_all_modems()

# Run example
asyncio.run(basic_example())
```

#### Send AT Commands

```python
async def at_command_example():
    """AT command example."""

    controller = ModemController()
    modem = await controller.get_modem("/dev/ttyUSB2")

    # Send AT command
    response = await modem.at.send_command("AT+CSQ")

    if response.success:
        print(f"Response: {response.data}")
    else:
        print(f"Error: {response.error_message}")

    await controller.close_all_modems()

asyncio.run(at_command_example())
```

#### Configure Network

```python
async def network_config_example():
    """Network configuration example."""

    controller = ModemController()
    modem = await controller.get_modem("/dev/ttyUSB2")

    # Configure APN
    success = await modem.network.configure_apn(
        apn="fast.t-mobile.com",
        username="",
        password=""
    )

    if success:
        print("APN configured")

    # Activate PDP context
    success = await modem.network.activate_pdp(context_id=1)

    if success:
        print("PDP context activated")

        # Get IP address
        ip = await modem.network.get_ip_address(context_id=1)
        print(f"IP Address: {ip}")

    # Test connectivity
    result = await modem.network.ping("8.8.8.8", count=4)

    if result.success:
        print(f"Ping: {result.received}/{result.sent} packets received")
        print(f"Avg RTT: {result.avg_time}ms")

    await controller.close_all_modems()

asyncio.run(network_config_example())
```

#### Monitor BIP Events

```python
async def bip_monitoring_example():
    """BIP event monitoring example."""

    controller = ModemController()
    modem = await controller.get_modem("/dev/ttyUSB2")

    # Define event handler
    def on_bip_event(event):
        print(f"BIP Event: {event.command.name}")
        if event.channel_id:
            print(f"  Channel ID: {event.channel_id}")
        if event.destination_address:
            print(f"  Destination: {event.destination_address}")

    # Register handler
    modem.on_bip_event(on_bip_event)

    # Start monitoring
    await modem.start_bip_monitoring()

    # Monitor for 5 minutes
    await asyncio.sleep(300)

    # Stop monitoring
    await modem.stop_bip_monitoring()
    await controller.close_all_modems()

asyncio.run(bip_monitoring_example())
```

#### Send SMS Trigger

```python
async def sms_trigger_example():
    """SMS trigger sending example."""

    controller = ModemController()
    modem = await controller.get_modem("/dev/ttyUSB2")

    # PDU for OTA trigger
    pdu = "0001000B911234567890007F160AD081810612345678"

    # Send trigger
    result = await modem.sms.send_raw_pdu(pdu)

    if result.success:
        print(f"SMS sent, reference: {result.message_reference}")
    else:
        print(f"SMS failed: {result.error}")

    await controller.close_all_modems()

asyncio.run(sms_trigger_example())
```

---

## Troubleshooting

### Modem Not Detected

**Problem:** `gp-modem list` shows no modems

**Solutions:**
1. Check USB connection:
   ```bash
   lsusb  # Linux
   # or
   ls /dev/tty*  # Check for ttyUSB* devices
   ```

2. Check permissions:
   ```bash
   # Add user to dialout group (Linux)
   sudo usermod -a -G dialout $USER
   # Log out and back in
   ```

3. Install drivers:
   - Linux: Usually automatic via usb_wwan driver
   - Windows: Install modem manufacturer's drivers
   - macOS: Install driver for specific modem

4. Check modem power:
   - Some modems need external power
   - Check power LED is on

### Serial Port Access Denied

**Problem:** `Permission denied` error

**Solutions:**
1. Linux - Add to dialout group:
   ```bash
   sudo usermod -a -G dialout $USER
   newgrp dialout  # Or logout/login
   ```

2. Or run with sudo (not recommended):
   ```bash
   sudo gp-modem list
   ```

3. Check port permissions:
   ```bash
   ls -l /dev/ttyUSB2
   # Should be: crw-rw---- dialout
   ```

### AT Commands Timeout

**Problem:** AT commands fail with timeout

**Solutions:**
1. Check correct port:
   ```bash
   # Some modems have multiple ports
   # AT port is usually ttyUSB2 or ttyUSB3
   gp-modem ports  # Check descriptions
   ```

2. Increase timeout:
   ```bash
   gp-modem at /dev/ttyUSB2 "AT+COPS?" --timeout 30
   ```

3. Check modem is responding:
   ```bash
   # Try basic command first
   gp-modem at /dev/ttyUSB2 "AT"
   ```

4. Reset modem:
   ```bash
   gp-modem at /dev/ttyUSB2 "AT+CFUN=1,1"  # Reboot
   ```

### SIM Not Ready

**Problem:** `+CPIN: SIM PIN` or SIM errors

**Solutions:**
1. Check SIM is inserted properly

2. Unlock SIM if PIN protected:
   ```bash
   gp-modem at /dev/ttyUSB2 "AT+CPIN=1234"  # Use your PIN
   ```

3. Disable PIN:
   ```bash
   gp-modem at /dev/ttyUSB2 "AT+CLCK=\"SC\",0,\"1234\""
   ```

4. Check SIM status:
   ```bash
   gp-modem at /dev/ttyUSB2 "AT+CPIN?"
   ```

### Network Registration Failed

**Problem:** Not registered to network

**Solutions:**
1. Check registration status:
   ```bash
   gp-modem at /dev/ttyUSB2 "AT+CREG?"
   # 0,1 = registered home
   # 0,5 = registered roaming
   # 0,2 = searching
   # 0,3 = denied
   ```

2. Manual network selection:
   ```bash
   # Scan networks
   gp-modem at /dev/ttyUSB2 "AT+COPS=?"

   # Select manually
   gp-modem at /dev/ttyUSB2 "AT+COPS=1,2,\"310260\""
   ```

3. Check signal strength:
   ```bash
   gp-modem at /dev/ttyUSB2 "AT+CSQ"
   # +CSQ: 20,99  (20 = -73 dBm, good signal)
   ```

4. Reset network registration:
   ```bash
   gp-modem at /dev/ttyUSB2 "AT+COPS=2"  # Deregister
   gp-modem at /dev/ttyUSB2 "AT+COPS=0"  # Auto register
   ```

### BIP Monitoring Shows No Events

**Problem:** No BIP events detected

**Solutions:**
1. Enable STK notifications (Quectel):
   ```bash
   gp-modem at /dev/ttyUSB2 "AT+QSTK=1"
   ```

2. Check for unsolicited result codes:
   ```bash
   # Enable all URCs
   gp-modem at /dev/ttyUSB2 "AT+QURCCFG=\"urcport\",\"usbmodem\""
   ```

3. Verify SIM supports STK/BIP:
   - Not all SIMs have STK applets
   - Test with known STK-enabled SIM

4. Use verbose mode:
   ```bash
   gp-modem -v monitor /dev/ttyUSB2
   ```

### QXDM Not Available

**Problem:** QXDM interface not available

**Solutions:**
1. Check modem vendor:
   - QXDM only works with Qualcomm-based modems
   - Quectel, Sierra Wireless (most models)

2. Find DM port:
   ```bash
   gp-modem ports
   # Look for "DM" or "Diag" in description
   # Usually first USB interface (ttyUSB0)
   ```

3. Check DM port permissions:
   ```bash
   ls -l /dev/ttyUSB0
   ```

4. Enable diagnostic mode:
   ```bash
   # Some modems require enabling
   gp-modem at /dev/ttyUSB2 "AT+QCFG=\"usbnet\",0"
   ```

---

## Best Practices

### Connection Management

```python
# Always close connections
async def example():
    controller = ModemController()
    try:
        modem = await controller.get_modem("/dev/ttyUSB2")
        # Use modem...
    finally:
        await controller.close_all_modems()

# Or use async context manager (if available)
async with controller.get_modem_context("/dev/ttyUSB2") as modem:
    # Use modem...
    pass
# Automatically closed
```

### Error Handling

```python
from cardlink.modem.exceptions import (
    ModemNotFoundError,
    SerialPortError,
    ATCommandError,
    ATTimeoutError
)

async def robust_example():
    controller = ModemController()

    try:
        modem = await controller.get_modem("/dev/ttyUSB2")
        response = await modem.at.send_command("AT+CSQ")

    except ModemNotFoundError:
        print("Modem not found on port")
    except SerialPortError as e:
        print(f"Serial port error: {e}")
    except ATTimeoutError:
        print("AT command timed out")
    except ATCommandError as e:
        print(f"AT command failed: {e}")
    finally:
        await controller.close_all_modems()
```

### Logging

```python
import logging

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)

# Or specific loggers
logging.getLogger('cardlink.modem').setLevel(logging.DEBUG)
logging.getLogger('cardlink.modem.at_interface').setLevel(logging.DEBUG)
```

### Performance Tips

1. **Reuse modem instances** - Don't recreate for each command
2. **Use caching** - ModemInfo caches results (60s TTL)
3. **Increase timeouts** - For slow commands (COPS scan, etc.)
4. **Close unused modems** - Free serial port resources

---

## Additional Resources

- **Modem AT Command Manuals**:
  - Quectel: https://www.quectel.com/download/
  - Sierra Wireless: https://source.sierrawireless.com/
  - Simcom: https://www.simcom.com/download.html

- **3GPP Standards**:
  - TS 27.007: AT command set for User Equipment
  - TS 27.005: Use of DTE-DCE interface for SMS
  - TS 102 223: ETSI SIM Application Toolkit (STK)

- **CardLink Documentation**:
  - API Reference: `/docs/api/modem.md`
  - Protocol Specifications: `/docs/protocols/`

---

## Support

For issues or questions:
1. Check troubleshooting section above
2. Review modem manufacturer's AT command guide
3. Check CardLink GitHub issues
4. Enable verbose mode: `gp-modem -v <command>`

---

**Last Updated:** December 2025
**Version:** 1.0
**Module:** cardlink.modem
