# Phone Controller User Guide

## Overview

The Phone Controller module provides comprehensive Android device management via ADB for OTA testing. It offers both synchronous (simple) and asynchronous (advanced) interfaces for device control, network management, AT commands, and BIP monitoring.

## Table of Contents

1. [Quick Start](#quick-start)
2. [ADB Controller (Synchronous)](#adb-controller-synchronous)
3. [Network Manager](#network-manager)
4. [AT Interface (Async)](#at-interface-async)
5. [BIP Monitoring (Async)](#bip-monitoring-async)
6. [SMS Triggers (Async)](#sms-triggers-async)
7. [Profile Management (Async)](#profile-management-async)
8. [Complete Examples](#complete-examples)
9. [Troubleshooting](#troubleshooting)

---

## Quick Start

### Prerequisites

```bash
# Install ADB (Android Debug Bridge)
# Windows: Download from https://developer.android.com/studio/releases/platform-tools
# macOS: brew install android-platform-tools
# Linux: sudo apt-get install android-tools-adb

# Verify ADB installation
adb version

# Enable USB debugging on Android device:
# Settings ’ About Phone ’ tap "Build number" 7 times
# Settings ’ Developer Options ’ enable "USB debugging"
```

### Basic Device Control

```python
from cardlink.phone import ADBController, NetworkManager

# Connect to device
adb = ADBController()  # Auto-connects to first device

# Or specify device
adb = ADBController(serial="ABC123")

# Get device info
info = adb.get_device_info()
print(f"Device: {info.manufacturer} {info.model}")
print(f"Android: {info.android_version} (SDK {info.sdk_version})")

# Control network
network = NetworkManager(adb)
status = network.get_status()
print(f"WiFi: {status.ssid} ({status.ip_address})")

# Test connectivity
if network.ping("8.8.8.8"):
    print("Internet connection OK")
```

---

## ADB Controller (Synchronous)

The ADB Controller provides synchronous, easy-to-use device control.

### Device Discovery

```python
from cardlink.phone import ADBController

# List all connected devices
devices = ADBController.list_devices()
print(f"Found {len(devices)} device(s)")
for serial in devices:
    print(f"  - {serial}")

# Connect to specific device
adb = ADBController(serial=devices[0])
```

### Device Information

```python
# Get comprehensive device info
info = adb.get_device_info()

print(f"Serial: {info.serial}")
print(f"Model: {info.model}")
print(f"Manufacturer: {info.manufacturer}")
print(f"Android: {info.android_version}")
print(f"SDK Level: {info.sdk_version}")
```

### Shell Commands

```python
# Execute shell commands
output = adb.shell("getprop ro.build.version.release")
print(f"Android version: {output}")

# With custom timeout
output = adb.shell("ping -c 3 google.com", timeout=15)

# Get system properties
prop = adb.get_property("ro.product.model")
print(f"Model: {prop}")
```

### Screen Control

```python
# Check screen state
if not adb.is_screen_on():
    # Wake up screen
    adb.wake_screen()
    print("Screen turned on")
```

### File Transfer

```python
# Push file to device
adb.push_file(
    local="/path/to/local/file.txt",
    remote="/sdcard/Download/file.txt"
)

# Pull file from device
adb.pull_file(
    remote="/sdcard/Download/file.txt",
    local="/path/to/local/file.txt"
)
```

### Device Reboot

```python
# Normal reboot
adb.reboot()

# Reboot to recovery
adb.reboot(mode="recovery")

# Reboot to bootloader
adb.reboot(mode="bootloader")
```

---

## Network Manager

Manage WiFi and network connectivity.

### Network Status

```python
from cardlink.phone import NetworkManager, NetworkStatus

network = NetworkManager(adb)

# Get current status
status = network.get_status()

print(f"WiFi Enabled: {status.wifi_enabled}")
print(f"Connected: {status.connected}")
if status.connected:
    print(f"SSID: {status.ssid}")
    print(f"IP Address: {status.ip_address}")
    print(f"Gateway: {status.gateway}")
```

### WiFi Control

```python
# Enable WiFi
network.enable_wifi()

# Disable WiFi
network.disable_wifi()

# Connect to network
success = network.connect_wifi(
    ssid="MyNetwork",
    password="mypassword",
    security="WPA"  # WPA, WPA2, or WEP
)

if success:
    print("Connected to WiFi")
else:
    print("Connection failed")
```

### Mobile Data Control

```python
# Disable mobile data (force WiFi usage)
network.disable_mobile_data()
```

### Connectivity Testing

```python
# Ping a host
if network.ping("8.8.8.8", count=3):
    print("Internet connectivity OK")
else:
    print("No internet connection")

# Ping with custom count
network.ping("google.com", count=5)
```

### Complete Network Setup Example

```python
def setup_wifi_for_testing(ssid, password):
    """Configure device for WiFi-only testing."""

    adb = ADBController()
    network = NetworkManager(adb)

    # Disable mobile data
    network.disable_mobile_data()

    # Enable WiFi
    network.enable_wifi()

    # Connect to test network
    print(f"Connecting to {ssid}...")
    if network.connect_wifi(ssid, password):
        # Verify connection
        status = network.get_status()
        print(f"Connected!")
        print(f"  IP: {status.ip_address}")
        print(f"  Gateway: {status.gateway}")

        # Test connectivity
        if network.ping("8.8.8.8"):
            print(" Internet access confirmed")
            return True
        else:
            print(" No internet access")
            return False
    else:
        print(" Connection failed")
        return False
```

---

## AT Interface (Async)

For advanced modem communication via AT commands.

### Basic AT Commands

```python
import asyncio
from cardlink.phone.adb_client import ADBClient
from cardlink.phone.at_interface import ATInterface

async def check_sim_status():
    """Check SIM card status via AT commands."""

    client = ADBClient()
    at = ATInterface(client, serial="ABC123")

    # Check if AT interface is available
    if not await at.is_available():
        print("AT interface not available")
        return

    # Check SIM status
    status = await at.get_sim_status()
    print(f"SIM Status: {status}")

    # Get ICCID
    iccid = await at.get_iccid()
    print(f"ICCID: {iccid}")

    # Get IMSI
    imsi = await at.get_imsi()
    print(f"IMSI: {imsi}")

# Run async function
asyncio.run(check_sim_status())
```

### Custom AT Commands

```python
async def send_custom_at_command():
    """Send custom AT command."""

    client = ADBClient()
    at = ATInterface(client, "ABC123")

    # Send AT command
    response = await at.send_command("AT+CPIN?")

    if response.is_ok:
        print("Command successful")
        for line in response.response_lines:
            print(f"  {line}")
    else:
        print(f"Command failed: {response.error_message}")
```

### SIM Card Operations

```python
async def get_sim_info():
    """Get comprehensive SIM information."""

    client = ADBClient()
    at = ATInterface(client, "ABC123")

    # Get SIM status
    status = await at.get_sim_status()
    print(f"Status: {status}")

    # Get ICCID (SIM serial number)
    iccid = await at.get_iccid()
    print(f"ICCID: {iccid}")

    # Get IMSI (subscriber identity)
    imsi = await at.get_imsi()
    print(f"IMSI: {imsi}")

    # Get signal quality
    rssi, ber = await at.get_signal_quality()
    print(f"Signal: RSSI={rssi}, BER={ber}")

    # Get operator
    operator = await at.get_operator()
    print(f"Operator: {operator}")

    # Get network registration
    n, stat = await at.get_network_registration()
    print(f"Network: n={n}, stat={stat}")
```

---

## BIP Monitoring (Async)

Monitor Bearer Independent Protocol events for OTA sessions.

### Basic BIP Monitoring

```python
from cardlink.phone.bip_monitor import BIPMonitor

async def monitor_bip_events(duration=60):
    """Monitor BIP events for specified duration."""

    client = ADBClient()
    monitor = BIPMonitor(client, "ABC123")

    # Define event callback
    def on_bip_event(event):
        print(f"BIP Event: {event.event_type.value}")
        if event.channel_id:
            print(f"  Channel: {event.channel_id}")

    # Register callback
    monitor.on_bip_event(on_bip_event)

    # Start monitoring
    await monitor.start()

    # Monitor for specified duration
    await asyncio.sleep(duration)

    # Stop monitoring
    await monitor.stop()

    # Get captured events
    events = monitor.events
    print(f"\nCaptured {len(events)} BIP events")

# Run monitoring
asyncio.run(monitor_bip_events(duration=60))
```

### Using Async Iterator

```python
async def monitor_with_iterator():
    """Monitor BIP events using async iterator."""

    client = ADBClient()
    monitor = BIPMonitor(client, "ABC123")

    async with monitor.start_monitoring() as events:
        async for event in events:
            print(f"Event: {event.event_type.value}")

            # Stop after specific event
            if event.event_type.value == "open_channel":
                print("Channel opened, stopping monitoring")
                break
```

### Waiting for Specific Events

```python
async def wait_for_channel_open():
    """Wait for BIP channel to open."""

    client = ADBClient()
    monitor = BIPMonitor(client, "ABC123")

    await monitor.start()

    # Wait for specific event type
    event = await monitor.wait_for_event(
        event_type="open_channel",
        timeout=30
    )

    if event:
        print(f"Channel opened: {event.channel_id}")
    else:
        print("Timeout waiting for channel open")

    await monitor.stop()
```

---

## SMS Triggers (Async)

Send SMS-PP triggers to initiate OTA sessions.

### Using Pre-defined Templates

```python
from cardlink.phone.sms_trigger import SMSTrigger

async def send_ota_trigger():
    """Send OTA trigger using template."""

    client = ADBClient()
    at = ATInterface(client, "ABC123")
    trigger = SMSTrigger(client, "ABC123", at)

    # Send using template
    result = await trigger.send_trigger(
        template_name="ota_trigger",
        params={
            "smsc": "1234567890",
            "ud": "D0818106123456789012345678901234567890"
        }
    )

    if result.success:
        print(f"Trigger sent via {result.method_used}")
        print(f"PDU: {result.pdu_sent}")
    else:
        print(f"Failed: {result.error_message}")
```

### Building Custom PDU

```python
async def send_custom_trigger():
    """Build and send custom SMS trigger PDU."""

    client = ADBClient()
    trigger = SMSTrigger(client, "ABC123")

    # Build OTA trigger PDU
    pdu = trigger.build_ota_trigger_pdu(
        smsc="",
        destination="+1234567890",
        command_data=bytes.fromhex("D081810612345678"),
        protocol_id=0x7F,  # SIM Data Download
        data_coding=0x16   # Class 2, 8-bit
    )

    # Send raw PDU
    result = await trigger.send_raw_pdu(pdu)

    if result.success:
        print("Trigger sent successfully")
```

### HTTPS Admin Trigger

```python
async def send_https_admin_trigger():
    """Send HTTPS Admin trigger for SCP81."""

    client = ADBClient()
    trigger = SMSTrigger(client, "ABC123")

    result = await trigger.send_https_admin_trigger(
        tar="B0FF",          # TAR for HTTP Admin
        counter=0,
        padding_counter=0
    )

    print(f"Trigger sent: {result.success}")
```

---

## Profile Management (Async)

Save and load device profiles for comparison and tracking.

### Save Device Profile

```python
from cardlink.phone.profile_manager import ProfileManager
from cardlink.phone.device_info import DeviceInfo

async def save_device_profile(serial):
    """Save complete device profile."""

    client = ADBClient()
    device_info = DeviceInfo(client, serial)

    # Get full profile
    profile = await device_info.get_full_profile()

    # Save profile
    manager = ProfileManager()
    path = await manager.save_profile(
        name=f"device_{serial}",
        profile=profile
    )

    print(f"Profile saved to: {path}")
```

### Load and Compare Profiles

```python
async def compare_profiles(name1, name2):
    """Compare two device profiles."""

    manager = ProfileManager()

    # Load profiles
    profile1 = await manager.load_profile(name1)
    profile2 = await manager.load_profile(name2)

    # Compare
    diff = manager.compare(profile1, profile2)

    if diff:
        print("Differences found:")
        for section, changes in diff.items():
            print(f"\n{section}:")
            print(f"  {changes}")
    else:
        print("Profiles are identical")
```

### List Saved Profiles

```python
def list_all_profiles():
    """List all saved device profiles."""

    manager = ProfileManager()
    profiles = manager.list_profiles()

    print(f"Found {len(profiles)} profile(s):\n")

    for prof in profiles:
        print(f"{prof['name']}:")
        print(f"  Serial: {prof['serial']}")
        print(f"  Model: {prof['model']}")
        print(f"  Saved: {prof['saved_at']}")
        print()
```

### Export Profile

```python
async def export_profile_summary(name):
    """Export profile as human-readable summary."""

    manager = ProfileManager()

    # Export as summary
    summary = await manager.export_profile(name, format="summary")
    print(summary)

    # Export as JSON
    json_data = await manager.export_profile(name, format="json")

    # Save to file
    with open(f"{name}.json", "w") as f:
        f.write(json_data)
```

---

## Complete Examples

### Example 1: Device Setup for OTA Testing

```python
from cardlink.phone import ADBController, NetworkManager
import asyncio
from cardlink.phone.adb_client import ADBClient
from cardlink.phone.at_interface import ATInterface
from cardlink.phone.bip_monitor import BIPMonitor

async def setup_device_for_ota(serial, wifi_ssid, wifi_password):
    """Complete device setup for OTA testing."""

    print(f"Setting up device {serial} for OTA testing...\n")

    # Step 1: Basic device check
    print("1. Checking device connection...")
    adb = ADBController(serial)
    info = adb.get_device_info()
    print(f"    Connected to {info.manufacturer} {info.model}")
    print(f"    Android {info.android_version}")

    # Step 2: Configure network
    print("\n2. Configuring network...")
    network = NetworkManager(adb)

    # Disable mobile data
    network.disable_mobile_data()
    print("    Mobile data disabled")

    # Enable and connect WiFi
    network.enable_wifi()
    if network.connect_wifi(wifi_ssid, wifi_password):
        status = network.get_status()
        print(f"    WiFi connected: {status.ssid}")
        print(f"    IP address: {status.ip_address}")
    else:
        print("    WiFi connection failed")
        return False

    # Verify internet connectivity
    if network.ping("8.8.8.8"):
        print("    Internet connectivity verified")
    else:
        print("    No internet access")
        return False

    # Step 3: Check SIM status
    print("\n3. Checking SIM status...")
    client = ADBClient()
    at = ATInterface(client, serial)

    if await at.is_available():
        status = await at.get_sim_status()
        iccid = await at.get_iccid()
        print(f"    SIM status: {status}")
        print(f"    ICCID: {iccid}")
    else:
        print("     AT interface not available")

    # Step 4: Start BIP monitoring
    print("\n4. Starting BIP monitor...")
    monitor = BIPMonitor(client, serial)

    def on_event(event):
        print(f"   ’ BIP Event: {event.event_type.value}")

    monitor.on_bip_event(on_event)
    await monitor.start()
    print("    BIP monitoring active")

    print("\n Device setup complete!")
    print("Ready for OTA testing")

    return monitor  # Return monitor to keep it running

# Run setup
monitor = asyncio.run(setup_device_for_ota(
    serial="ABC123",
    wifi_ssid="TestNetwork",
    wifi_password="password123"
))
```

### Example 2: Automated OTA Test

```python
async def run_ota_test(serial, wifi_ssid, wifi_password, trigger_tar):
    """Run complete OTA test workflow."""

    # Setup device
    adb = ADBController(serial)
    network = NetworkManager(adb)
    client = ADBClient()

    # Configure WiFi
    network.enable_wifi()
    network.connect_wifi(wifi_ssid, wifi_password)

    # Start BIP monitoring
    monitor = BIPMonitor(client, serial)
    await monitor.start()

    # Send trigger
    trigger = SMSTrigger(client, serial)
    result = await trigger.send_https_admin_trigger(tar=trigger_tar)

    if not result.success:
        print(f"Trigger failed: {result.error_message}")
        return False

    print("Trigger sent, waiting for BIP channel...")

    # Wait for channel open
    event = await monitor.wait_for_event(
        event_type="open_channel",
        timeout=60
    )

    if event:
        print(f" BIP channel opened: {event.channel_id}")

        # Wait for session completion
        await asyncio.sleep(30)

        # Check events
        events = monitor.events
        print(f"\nCaptured {len(events)} BIP events:")
        for e in events:
            print(f"  - {e.event_type.value}")

        return True
    else:
        print(" Timeout waiting for BIP channel")
        return False

    await monitor.stop()

# Run test
success = asyncio.run(run_ota_test(
    serial="ABC123",
    wifi_ssid="TestNetwork",
    wifi_password="password123",
    trigger_tar="B0FF"
))
```

---

## Troubleshooting

### ADB Connection Issues

**Problem:** `RuntimeError: ADB not found`

**Solutions:**
1. Install Android Platform Tools
2. Add ADB to PATH:
   ```bash
   # Windows
   set PATH=%PATH%;C:\path\to\platform-tools

   # Linux/macOS
   export PATH=$PATH:/path/to/platform-tools
   ```

**Problem:** Device not authorized

**Solutions:**
1. Check phone screen for authorization dialog
2. Revoke and retry:
   ```bash
   adb kill-server
   adb devices
   ```

### WiFi Connection Failures

**Problem:** `connect_wifi()` returns `False`

**Solutions:**
1. Check SSID and password are correct
2. Verify WiFi is enabled: `network.enable_wifi()`
3. Check Android version compatibility (cmd wifi requires Android 10+)
4. Try manual connection first to verify credentials

### AT Interface Not Available

**Problem:** `await at.is_available()` returns `False`

**Solutions:**
1. Device may not have accessible modem device
2. May require root access:
   ```bash
   adb root
   adb shell ls /dev/smd*
   ```
3. Some devices don't expose AT interface

### BIP Monitoring Not Working

**Problem:** No BIP events captured

**Solutions:**
1. Check STK (SIM Toolkit) app is enabled
2. Verify logcat permissions:
   ```bash
   adb logcat -v time StkAppService:V CatService:V *:S
   ```
3. Check phone has active data connection
4. Ensure monitoring is started before trigger

### SMS Trigger Failures

**Problem:** `send_trigger()` returns unsuccessful result

**Solutions:**
1. Check AT interface is available
2. Verify device has phone number
3. Try alternative methods (content provider, intent)
4. Check SIM card supports SMS

---

## Best Practices

### Resource Management

```python
# Always disconnect when done
try:
    adb = ADBController(serial)
    # ... operations ...
finally:
    # ADB controller doesn't need explicit cleanup
    pass

# For async resources, use context managers
async with monitor.start_monitoring() as events:
    async for event in events:
        # Process events
        pass
# Monitor automatically stopped
```

### Error Handling

```python
from cardlink.phone.exceptions import (
    ADBNotFoundError,
    DeviceNotFoundError,
    ATCommandError
)

try:
    adb = ADBController()
    # ... operations ...
except ADBNotFoundError:
    print("ADB not installed")
except DeviceNotFoundError:
    print("No device connected")
except RuntimeError as e:
    print(f"Command failed: {e}")
```

### Logging

```python
import logging

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)

# Or specific logger
logger = logging.getLogger('cardlink.phone')
logger.setLevel(logging.DEBUG)
```

### Testing Multiple Devices

```python
def test_all_devices():
    """Run tests on all connected devices."""

    devices = ADBController.list_devices()

    for serial in devices:
        print(f"\nTesting device: {serial}")
        adb = ADBController(serial)

        # Run tests...
        info = adb.get_device_info()
        print(f"  Model: {info.model}")
```

---

## Additional Resources

- **ADB Documentation:** https://developer.android.com/studio/command-line/adb
- **AT Commands Reference:** 3GPP TS 27.007
- **BIP Specification:** ETSI TS 102 223
- **CardLink API Reference:** `/docs/api/phone.md`

---

**Last Updated:** December 2025
**Version:** 1.0
**Module:** cardlink.phone
