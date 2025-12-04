# UICC Provisioner User Guide

## Overview

The UICC Provisioner module provides tools for provisioning UICC/SIM cards via PC/SC interface using GlobalPlatform specifications. This guide covers the configuration modules for PSK-TLS, triggers, and BIP settings.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [PSK Configuration](#psk-configuration)
3. [Trigger Configuration](#trigger-configuration)
4. [BIP Configuration](#bip-configuration)
5. [Complete Provisioning Example](#complete-provisioning-example)
6. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Hardware Requirements
- PC/SC compatible smart card reader
- UICC/SIM card with GlobalPlatform support

### Software Requirements
```bash
# Install pyscard for PC/SC access
pip install pyscard

# Install cardlink provisioner module
pip install -e ".[pcsc]"
```

### Verify Reader Connection
```python
from cardlink.provisioner import list_readers

readers = list_readers()
print(f"Available readers: {readers}")
```

---

## PSK Configuration

PSK (Pre-Shared Key) configuration is used for PSK-TLS authentication in OTA sessions.

### Basic Usage

```python
from cardlink.provisioner import (
    PCSCClient,
    APDUInterface,
    PSKConfig,
    PSKConfiguration,
    SCP03
)

# Connect to card
client = PCSCClient()
readers = client.list_readers()
client.connect(readers[0])

# Create APDU interface
apdu = APDUInterface(client.transmit)

# Select ISD and authenticate
apdu.select_by_aid("A0000000151000")
scp = SCP03(apdu)
scp.authenticate(keys)  # Use your keys

# Configure PSK
psk_config = PSKConfig(apdu, secure_channel=scp.wrap_command)

# Generate PSK
psk = PSKConfiguration.generate(
    identity="device_001",
    key_size=16  # 128-bit key
)

# Write to card
psk_config.configure(psk)

# Verify configuration
stored_psk = psk_config.read_configuration()
print(f"Stored identity: {stored_psk.identity}")

# Verify PSK
if psk_config.verify(psk):
    print("PSK configuration verified!")
```

### PSK Configuration Details

**Identity Format:**
- ASCII string, max 64 characters
- Used as PSK identity in TLS handshake
- Example: `"device_001"`, `"card_12345678"`

**Key Sizes:**
- 16 bytes (128-bit) - Recommended
- 24 bytes (192-bit)
- 32 bytes (256-bit)

**Security Notes:**
-   **PSK writing requires secure channel** (SCP02/SCP03)
- Keys are stored in card's secure memory
- Keys cannot be read back (write-only)
- Only identity can be verified

### Error Handling

```python
from cardlink.provisioner import SecurityError, ProfileError

try:
    psk_config.configure(psk)
except SecurityError as e:
    print(f"Security error: {e}")
    print("Make sure secure channel is established")
except ProfileError as e:
    print(f"Profile error: {e}")
    print("Check card supports PSK configuration")
```

---

## Trigger Configuration

Triggers initiate OTA sessions on the UICC card. Two types are supported:

1. **SMS-PP Triggers** - Triggered by SMS messages
2. **Poll Triggers** - Periodic polling

### SMS-PP Trigger Configuration

```python
from cardlink.provisioner import (
    TriggerConfig,
    SMSTriggerConfig
)

# Create trigger config manager
trigger_config = TriggerConfig(apdu)

# Configure SMS trigger
sms_trigger = SMSTriggerConfig(
    tar=bytes.fromhex("B00001"),           # TAR: 3 bytes
    originating_address="+1234567890",    # SMS sender
    kic=bytes.fromhex("01"),              # Key for ciphering
    kid=bytes.fromhex("01"),              # Key for integrity
    counter=bytes.fromhex("0000000000")   # Counter: 5 bytes
)

# Write to card
trigger_config.configure_sms_trigger(sms_trigger)

# Verify
config = trigger_config.read_configuration()
if config.sms_trigger:
    print(f"SMS trigger configured:")
    print(f"  TAR: {config.sms_trigger.tar.hex()}")
    print(f"  From: {config.sms_trigger.originating_address}")
```

### SMS Trigger Parameters

**TAR (Toolkit Application Reference):**
- 3 bytes identifying the target application
- Example: `B00001` for HTTP Admin
- Format: hexadecimal string

**Originating Address:**
- Phone number of authorized SMS sender
- Format: `"+1234567890"` (with country code)
- Optional: Leave empty to accept from any sender

**KIc/KId:**
- 1 byte each
- Key identifiers for cryptographic operations
- Must match keys provisioned in card

**Counter:**
- 5 bytes for replay protection
- Starts at `0000000000`
- Increments with each SMS

### Poll Trigger Configuration

```python
from cardlink.provisioner import PollTriggerConfig

# Configure polling
poll_trigger = PollTriggerConfig(
    interval=3600,  # Poll every hour (seconds)
    enabled=True
)

trigger_config.configure_poll_trigger(poll_trigger)

# Read back
config = trigger_config.read_configuration()
if config.poll_trigger:
    print(f"Poll interval: {config.poll_trigger.interval}s")
    print(f"Enabled: {config.poll_trigger.enabled}")
```

### Poll Trigger Constraints

- Minimum interval: **60 seconds**
- Maximum interval: **4,294,967,295 seconds** (~136 years)
- Recommended: 3600s (1 hour) or higher
- Disabled by default

### Disabling Triggers

```python
from cardlink.provisioner import TriggerType

# Disable SMS trigger
trigger_config.disable_trigger(TriggerType.SMS)

# Disable poll trigger
trigger_config.disable_trigger(TriggerType.POLL)
```

---

## BIP Configuration

BIP (Bearer Independent Protocol) configures data channels for OTA communication.

### Basic BIP Configuration

```python
from cardlink.provisioner import (
    BIPConfig,
    BIPConfiguration,
    BearerType
)

# Create BIP config manager
bip_config = BIPConfig(apdu)

# Configure BIP for WiFi
bip = BIPConfiguration(
    bearer_type=BearerType.WIFI,
    apn="internet",           # APN name
    buffer_size=1500,         # MTU size
    timeout=30                # Connection timeout (seconds)
)

# Write to card
bip_config.configure(bip)

# Verify
stored_bip = bip_config.read_configuration()
print(f"Bearer: {stored_bip.bearer_type.value}")
print(f"APN: {stored_bip.apn}")
print(f"Buffer: {stored_bip.buffer_size} bytes")
```

### Bearer Types

```python
from cardlink.provisioner import BearerType

# Available bearer types:
BearerType.GPRS     # 2G/3G mobile data
BearerType.UTRAN    # 3G UMTS
BearerType.EUTRAN   # 4G LTE
BearerType.WIFI     # WiFi connection
```

### APN Configuration

**APN Encoding:**
- Stored in DNS label format (RFC 1035)
- Example: `"internet"` ’ `08 69 6E 74 65 72 6E 65 74`
- Maximum 100 characters
- Alphanumeric and dots allowed

**Common APNs:**
```python
# Mobile carriers
apn = "internet"           # Generic
apn = "wholesale"          # T-Mobile
apn = "att.mvno"          # AT&T MVNO
apn = "fast.t-mobile.com" # T-Mobile

# WiFi (usually not needed)
apn = None  # No APN for WiFi
```

### Buffer Size

- **Minimum:** 128 bytes
- **Maximum:** 65535 bytes
- **Recommended:** 1500 bytes (standard MTU)
- **LTE:** Consider 1400-1500 bytes

### Timeout Settings

- Connection establishment timeout in seconds
- **Minimum:** 5 seconds
- **Maximum:** 300 seconds (5 minutes)
- **Recommended:** 30 seconds

### Advanced Configuration

```python
# Multiple bearer configuration
configs = [
    BIPConfiguration(
        bearer_type=BearerType.EUTRAN,
        apn="internet",
        buffer_size=1500,
        timeout=30
    ),
    BIPConfiguration(
        bearer_type=BearerType.WIFI,
        apn=None,
        buffer_size=1500,
        timeout=30
    )
]

for config in configs:
    bip_config.configure(config)
```

---

## Complete Provisioning Example

Here's a complete example provisioning a card with all configurations:

```python
from cardlink.provisioner import (
    PCSCClient,
    APDUInterface,
    SCP03,
    SCPKeys,
    PSKConfig,
    PSKConfiguration,
    TriggerConfig,
    SMSTriggerConfig,
    PollTriggerConfig,
    BIPConfig,
    BIPConfiguration,
    BearerType
)

def provision_card(reader_index=0):
    """Complete card provisioning workflow."""

    # Step 1: Connect to card
    print("Connecting to card...")
    client = PCSCClient()
    readers = client.list_readers()

    if not readers:
        raise RuntimeError("No card readers found")

    print(f"Using reader: {readers[reader_index]}")
    client.connect(readers[reader_index])

    # Step 2: Get card info
    info = client.get_card_info()
    print(f"Card ICCID: {info.iccid}")
    print(f"GP Version: {info.gp_version}")

    # Step 3: Create APDU interface
    apdu = APDUInterface(client.transmit)

    # Step 4: Select ISD
    print("\nSelecting ISD...")
    apdu.select_by_aid("A0000000151000")

    # Step 5: Authenticate with SCP03
    print("Authenticating...")
    keys = SCPKeys(
        enc=bytes.fromhex("404142434445464748494A4B4C4D4E4F"),
        mac=bytes.fromhex("404142434445464748494A4B4C4D4E4F"),
        dek=bytes.fromhex("404142434445464748494A4B4C4D4E4F")
    )

    scp = SCP03(apdu)
    scp.authenticate(keys, key_version=0x01)
    print("Authentication successful!")

    # Step 6: Configure PSK
    print("\nConfiguring PSK...")
    psk_config = PSKConfig(apdu, secure_channel=scp.wrap_command)

    psk = PSKConfiguration.generate(
        identity=f"card_{info.iccid[-8:]}",
        key_size=16
    )

    psk_config.configure(psk)

    # Verify PSK
    if psk_config.verify(psk):
        print(f" PSK configured: {psk.identity}")

    # Step 7: Configure SMS Trigger
    print("\nConfiguring SMS trigger...")
    trigger_config = TriggerConfig(apdu)

    sms_trigger = SMSTriggerConfig(
        tar=bytes.fromhex("B00001"),
        originating_address="+1234567890",
        kic=bytes.fromhex("01"),
        kid=bytes.fromhex("01")
    )

    trigger_config.configure_sms_trigger(sms_trigger)
    print(" SMS trigger configured")

    # Step 8: Configure Poll Trigger
    print("\nConfiguring poll trigger...")
    poll_trigger = PollTriggerConfig(
        interval=3600,
        enabled=True
    )

    trigger_config.configure_poll_trigger(poll_trigger)
    print(" Poll trigger configured (1 hour interval)")

    # Step 9: Configure BIP
    print("\nConfiguring BIP...")
    bip_config = BIPConfig(apdu)

    bip = BIPConfiguration(
        bearer_type=BearerType.EUTRAN,
        apn="internet",
        buffer_size=1500,
        timeout=30
    )

    bip_config.configure(bip)
    print(" BIP configured for LTE")

    # Step 10: Verify all configurations
    print("\n=== Configuration Summary ===")

    # Verify PSK
    stored_psk = psk_config.read_configuration()
    print(f"PSK Identity: {stored_psk.identity}")

    # Verify triggers
    trigger_conf = trigger_config.read_configuration()
    if trigger_conf.sms_trigger:
        print(f"SMS Trigger TAR: {trigger_conf.sms_trigger.tar.hex()}")
    if trigger_conf.poll_trigger:
        print(f"Poll Interval: {trigger_conf.poll_trigger.interval}s")

    # Verify BIP
    bip_conf = bip_config.read_configuration()
    print(f"BIP Bearer: {bip_conf.bearer_type.value}")
    print(f"BIP APN: {bip_conf.apn}")

    # Step 11: Disconnect
    client.disconnect()
    print("\n Provisioning complete!")

    return {
        'psk': psk,
        'sms_trigger': sms_trigger,
        'poll_trigger': poll_trigger,
        'bip': bip
    }

# Run provisioning
if __name__ == "__main__":
    try:
        config = provision_card()
        print("\nProvisioned configuration:")
        print(f"  PSK Identity: {config['psk'].identity}")
        print(f"  PSK Key: {config['psk'].key.hex()}")
    except Exception as e:
        print(f"Error: {e}")
```

---

## Troubleshooting

### Card Connection Issues

**Problem:** `CardNotFoundError` or `ReaderNotFoundError`

**Solutions:**
1. Check reader is connected: `list_readers()`
2. Verify card is inserted properly
3. Try different USB port
4. Check PC/SC service is running:
   - Windows: `sc query SCardSvr`
   - Linux: `pcscd --version`
   - macOS: `ps aux | grep pcscd`

### Authentication Failures

**Problem:** `AuthenticationError` during SCP authentication

**Solutions:**
1. Verify key values are correct
2. Check key version matches card
3. Ensure keys are 16 bytes (128-bit)
4. Try default keys (if test card):
   ```python
   keys = SCPKeys.default()  # All zeros or 404142...
   ```

### Secure Channel Required

**Problem:** `SecurityError: Secure channel required`

**Solutions:**
1. Establish SCP session before PSK operations:
   ```python
   scp = SCP03(apdu)
   scp.authenticate(keys)
   psk_config = PSKConfig(apdu, secure_channel=scp.wrap_command)
   ```

### TLV Parsing Errors

**Problem:** `TLVError` when reading configuration

**Solutions:**
1. Card may not support the configuration
2. Configuration may not be initialized
3. Try writing before reading:
   ```python
   # Initialize with default values first
   trigger_config.configure_sms_trigger(default_trigger)
   ```

### File Not Found Errors

**Problem:** `ProfileError: Failed to select file`

**Solutions:**
1. Card may not have required files
2. Check GlobalPlatform version compatibility
3. Verify card profile supports OTA features
4. Use `apdu.select_by_path()` to check file existence

### Buffer Size Validation

**Problem:** `ValueError: Buffer size must be between 128 and 65535`

**Solutions:**
1. Use standard MTU: `buffer_size=1500`
2. For restricted networks: `buffer_size=1280` (minimum IPv6 MTU)
3. Check card's maximum supported size

### APN Encoding Issues

**Problem:** `ValueError: Invalid APN format`

**Solutions:**
1. Use alphanumeric and dots only: `"internet.apn"`
2. No spaces or special characters
3. Maximum 100 characters
4. For WiFi, set `apn=None` or empty string

---

## Security Best Practices

### Key Management

1. **Never hardcode keys in production code**
   ```python
   # Bad
   keys = SCPKeys(enc=bytes.fromhex("404142..."))

   # Good
   import os
   keys = SCPKeys.from_hex(
       enc=os.environ['CARD_ENC_KEY'],
       mac=os.environ['CARD_MAC_KEY'],
       dek=os.environ['CARD_DEK_KEY']
   )
   ```

2. **Rotate PSK keys regularly**
   ```python
   # Re-provision with new PSK
   new_psk = PSKConfiguration.generate(identity, 16)
   psk_config.configure(new_psk)
   ```

3. **Use unique identities per card**
   ```python
   # Use ICCID or unique identifier
   identity = f"card_{info.iccid}"
   ```

### Secure Communication

1. **Always use secure channel for sensitive operations**
2. **Verify configurations after writing**
3. **Log provisioning operations for audit**
4. **Use production keys only on production cards**

### Testing vs Production

```python
def get_keys(environment):
    """Get keys based on environment."""
    if environment == "production":
        # Load from secure key storage
        return load_production_keys()
    else:
        # Use test keys
        return SCPKeys.default()
```

---

## Additional Resources

- **GlobalPlatform Specifications:** https://globalplatform.org/
- **PC/SC Specifications:** https://pcscworkgroup.com/
- **pyscard Documentation:** https://pyscard.sourceforge.io/
- **CardLink API Reference:** `/docs/api/provisioner.md`

---

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review test files in `tests/unit/provisioner/`
3. Open an issue on GitHub
4. Consult GlobalPlatform specifications

---

**Last Updated:** December 2025
**Version:** 1.0
**Module:** cardlink.provisioner
