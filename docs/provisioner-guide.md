# UICC Provisioner User Guide

**Version:** 1.0.0
**Last Updated:** November 29, 2024

## Table of Contents

1. [Introduction](#introduction)
2. [Installation](#installation)
3. [Quick Start](#quick-start)
4. [Core Concepts](#core-concepts)
5. [PC/SC Setup](#pcsc-setup)
6. [Basic Operations](#basic-operations)
7. [Security Configuration](#security-configuration)
8. [Advanced Usage](#advanced-usage)
9. [Troubleshooting](#troubleshooting)
10. [API Reference](#api-reference)

---

## Introduction

The UICC Provisioner is a comprehensive Python toolkit for provisioning and managing UICC (Universal Integrated Circuit Card) smart cards using the GlobalPlatform specification over PC/SC interface.

### What Can You Do?

- **Connect to UICC cards** via PC/SC readers
- **Configure PSK-TLS credentials** for secure server connections
- **Store remote server URLs** for OTA provisioning
- **Establish secure channels** (SCP02/SCP03)
- **Manage card applications** via GlobalPlatform
- **Parse and analyze** card ATR information
- **Read card identifiers** (ICCID, IMSI)

### Use Cases

- **Testing**: Configure test UICC cards for development
- **Provisioning**: Batch provision cards with credentials
- **Management**: Read and update card configurations
- **Development**: Build card management applications

---

## Installation

### Prerequisites

- **Python 3.8+**
- **PC/SC middleware** (platform-specific)
- **Smart card reader** (USB or built-in)
- **UICC/USIM test card** (for testing)

### Install Package

```bash
# Install with provisioner dependencies
pip install gp-ota-tester[provisioner]

# Or install from source
git clone https://github.com/your-org/cardlink
cd cardlink
pip install -e ".[provisioner]"
```

### Platform-Specific Requirements

The provisioner requires PC/SC (Personal Computer/Smart Card) middleware to communicate with smart card readers.

#### Linux

Install `pcscd` (PC/SC Daemon):

```bash
# Debian/Ubuntu
sudo apt-get update
sudo apt-get install pcscd pcsc-tools

# Fedora/RHEL
sudo dnf install pcsc-lite pcsc-tools

# Arch Linux
sudo pacman -S pcsclite ccid

# Start the PC/SC daemon
sudo systemctl start pcscd
sudo systemctl enable pcscd

# Verify reader detection
pcsc_scan
```

#### macOS

PC/SC support is built into macOS - no additional installation required!

```bash
# Verify reader detection (optional)
# Install pcsc-tools via Homebrew if needed
brew install pcsc-lite
pcsc_scan
```

#### Windows

PC/SC support (WinSCard) is built into Windows - no additional installation required!

To verify your reader:
1. Insert card reader
2. Open Device Manager
3. Look under "Smart card readers"

---

## Quick Start

### 5-Minute Tutorial

Here's a complete example showing the most common operations:

```python
from cardlink.provisioner import (
    PCSCClient,
    APDUInterface,
    SecureDomainManager,
    SCP02,
)
from cardlink.provisioner.psk_config import PSKConfig
from cardlink.provisioner.url_config import URLConfig
from cardlink.provisioner.models import PSKConfiguration, URLConfiguration

# 1. Connect to card
client = PCSCClient()
readers = client.list_readers()
print(f"Found {len(readers)} reader(s):")
for r in readers:
    print(f"  - {r.name}")

# Connect to first reader
client.connect(readers[0].name)
print(f"Connected to card, ATR: {client.card_info.atr_hex}")

# 2. Create APDU interface
apdu = APDUInterface(client.transmit)

# 3. Select ISD (Issuer Security Domain)
sd_manager = SecureDomainManager(apdu)
sd_manager.select_isd()
print("ISD selected")

# 4. Establish secure channel (SCP02)
scp = SCP02(apdu)
scp.initialize()  # Uses default test keys
print("Secure channel established")

# 5. Configure PSK credentials
psk = PSKConfiguration.generate("my_card_001", key_size=16)
print(f"Generated PSK: {psk.key.hex()}")

psk_config = PSKConfig(apdu, secure_channel=scp.send)
psk_config.configure(psk)
print(f"PSK configured with identity: {psk.identity}")

# 6. Configure admin server URL
url = URLConfiguration.from_url("https://server.example.com:8443/admin")
url_config = URLConfig(apdu)
url_config.configure(url)
print(f"Admin URL configured: {url.url}")

# 7. Verify configuration
current_psk = psk_config.read_configuration()
current_url = url_config.read_configuration()
print(f"\nCurrent Configuration:")
print(f"  PSK Identity: {current_psk.identity}")
print(f"  Admin URL: {current_url.url}")

# 8. Cleanup
client.disconnect()
print("\nDisconnected")
```

**Output:**
```
Found 1 reader(s):
  - ACS ACR122U PICC Interface 00 00
Connected to card, ATR: 3B9F96801F478031E073FE211B63...
ISD selected
Secure channel established
Generated PSK: 0102030405060708090A0B0C0D0E0F10
PSK configured with identity: my_card_001
Admin URL configured: https://server.example.com:8443/admin

Current Configuration:
  PSK Identity: my_card_001
  Admin URL: https://server.example.com:8443/admin

Disconnected
```

---

## Core Concepts

### PC/SC Architecture

```
┌─────────────────┐
│  Application    │  Your Python code
│  (Provisioner)  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   pyscard       │  Python PC/SC wrapper
│   (smartcard)   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   PC/SC Daemon  │  pcscd (Linux) / WinSCard (Windows)
│                 │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Card Reader    │  USB/Built-in reader
│   (Hardware)    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   UICC Card     │  Smart card
│                 │
└─────────────────┘
```

### APDU Communication

**APDU (Application Protocol Data Unit)** is the communication format between your application and the smart card.

**Command APDU Structure:**
```
┌─────┬─────┬────┬────┬────┬──────────┬────┐
│ CLA │ INS │ P1 │ P2 │ Lc │   Data   │ Le │
└─────┴─────┴────┴────┴────┴──────────┴────┘
  1B    1B   1B   1B   1B   Variable   1B

CLA: Class byte (00=ISO, 80=GlobalPlatform)
INS: Instruction (A4=SELECT, CA=GET DATA)
P1:  Parameter 1
P2:  Parameter 2
Lc:  Data length
Data: Command data
Le:  Expected response length
```

**Response APDU Structure:**
```
┌──────────┬─────┬─────┐
│   Data   │ SW1 │ SW2 │
└──────────┴─────┴─────┘
  Variable   1B    1B

Data: Response data
SW1/SW2: Status words (9000 = success)
```

### GlobalPlatform Security

**Security Domains:**
- **ISD (Issuer Security Domain)**: Root security domain
- **SSD (Supplementary Security Domain)**: Application domains

**Secure Channels:**
- **SCP02**: Triple-DES based secure messaging
- **SCP03**: AES-based secure messaging (recommended)

**Authentication Flow:**
```
Application                Card
     │                      │
     ├─ INITIALIZE UPDATE ─>│
     │<──── Challenge ──────┤
     │                      │
     ├─ EXTERNAL AUTH ─────>│
     │<──── Success ────────┤
     │                      │
     │   [Secure Channel]   │
     ├───── Commands ──────>│
     │<──── Responses ──────┤
```

---

## PC/SC Setup

### Verify Installation

#### Linux
```bash
# Check pcscd status
sudo systemctl status pcscd

# Scan for readers
pcsc_scan

# List readers
opensc-tool --list-readers
```

#### macOS
```bash
# Check for readers (if pcsc-tools installed)
pcsc_scan

# Or use system_profiler
system_profiler SPUSBDataType | grep -A 10 "Card Reader"
```

#### Windows
```powershell
# PowerShell: List readers via Device Manager
Get-PnpDevice -Class SmartCardReader

# Or check in Device Manager GUI
devmgmt.msc
```

### Common Reader Issues

**Reader Not Detected:**

1. **Check USB connection**: Replug the reader
2. **Check driver**: Install reader-specific drivers
3. **Check permissions** (Linux):
   ```bash
   # Add user to pcscd group
   sudo usermod -a -G pcscd $USER
   # Re-login for changes to take effect
   ```
4. **Restart PC/SC service** (Linux):
   ```bash
   sudo systemctl restart pcscd
   ```

**Card Not Detected:**

1. **Check card insertion**: Ensure card is fully inserted
2. **Check card orientation**: Gold contacts facing correct direction
3. **Clean contacts**: Use isopropyl alcohol and lint-free cloth
4. **Try different card**: Card may be damaged

---

## Basic Operations

### List Readers

```python
from cardlink.provisioner import list_readers

# Get all readers
readers = list_readers()
for i, reader in enumerate(readers):
    print(f"{i}: {reader.name}")
    print(f"   Card present: {reader.has_card}")
    if reader.has_card:
        print(f"   ATR: {reader.atr.hex()}")
```

### Connect to Card

```python
from cardlink.provisioner import PCSCClient, Protocol

client = PCSCClient()

# Connect with auto-protocol detection
client.connect("ACS ACR122U PICC Interface 00 00")

# Or specify protocol explicitly
client.connect("Reader Name", protocol=Protocol.T1)

# Check connection
if client.is_connected:
    print(f"Connected: {client.card_info.atr_hex}")
```

### Send APDU Commands

```python
from cardlink.provisioner import APDUInterface
from cardlink.provisioner.models import APDUCommand, INS

apdu = APDUInterface(client.transmit)

# SELECT command
response = apdu.select_by_aid("A000000151000000")
print(f"SW: {response.sw:04X} - {response.status_message}")

# GET DATA command
response = apdu.send(
    APDUCommand(
        cla=0x80,
        ins=INS.GET_DATA,
        p1=0x00,
        p2=0x66,  # Card Data
        le=0,
    )
)
print(f"Card Data: {response.data.hex()}")
```

### Parse ATR

```python
from cardlink.provisioner import parse_atr

atr_bytes = bytes.fromhex("3B9F96801F478031E073FE211B63...")
atr_info = parse_atr(atr_bytes)

print(f"ATR Analysis:")
print(f"  Convention: {atr_info.convention.value}")
print(f"  Protocols: {atr_info.protocols}")
print(f"  Card Type: {atr_info.card_type.value}")
print(f"  Historical: {atr_info.historical_bytes.hex()}")
```

### Read ICCID

```python
from cardlink.provisioner import APDUInterface

apdu = APDUInterface(client.transmit)

# Select MF (Master File)
apdu.select_by_path("3F00")

# Select EF_ICCID
apdu.select_by_path("2FE2")

# Read ICCID
response = apdu.send(
    APDUCommand(cla=0x00, ins=INS.READ_BINARY, p1=0, p2=0, le=10)
)

# Decode BCD
iccid_bcd = response.data
iccid = "".join(f"{b:02X}" for b in iccid_bcd)
iccid = "".join(iccid[i:i+2][::-1] for i in range(0, len(iccid), 2))
print(f"ICCID: {iccid}")
```

---

## Security Configuration

### Establish Secure Channel (SCP02)

```python
from cardlink.provisioner import SCP02
from cardlink.provisioner.models import SCPKeys

# Using default test keys
scp = SCP02(apdu)
scp.initialize()

# Or with custom keys
keys = SCPKeys(
    enc=bytes.fromhex("404142434445464748494A4B4C4D4E4F"),
    mac=bytes.fromhex("404142434445464748494A4B4C4D4E4F"),
    dek=bytes.fromhex("404142434445464748494A4B4C4D4E4F"),
    version=0x01,
)
scp = SCP02(apdu, keys)
scp.initialize()

# Send secured commands
response = scp.send(
    APDUCommand(
        cla=0x84,  # Secure messaging
        ins=INS.GET_STATUS,
        p1=0x80,
        p2=0x00,
        data=bytes([0x4F, 0x00]),
        le=0,
    )
)
```

### Establish Secure Channel (SCP03)

```python
from cardlink.provisioner import SCP03

# SCP03 uses AES instead of 3DES
scp = SCP03(apdu)
scp.initialize()

# Send secured commands (same interface as SCP02)
response = scp.send(command)
```

### Configure PSK Credentials

```python
from cardlink.provisioner.psk_config import PSKConfig
from cardlink.provisioner.models import PSKConfiguration

# Generate random PSK
psk = PSKConfiguration.generate(
    identity="card_12345",
    key_size=16,  # 128-bit key
)
print(f"PSK Key: {psk.key.hex()}")

# Or load from hex
psk = PSKConfiguration.from_hex(
    identity="card_12345",
    key_hex="0102030405060708090A0B0C0D0E0F10"
)

# Configure on card (requires secure channel)
psk_config = PSKConfig(apdu, secure_channel=scp.send)
psk_config.configure(psk)

# Read current identity (key cannot be read back)
current = psk_config.read_configuration()
print(f"Configured PSK Identity: {current.identity}")

# Verify configuration
assert psk_config.verify(psk)
```

### Configure Admin URL

```python
from cardlink.provisioner.url_config import URLConfig
from cardlink.provisioner.models import URLConfiguration

# Create URL configuration
url = URLConfiguration.from_url("https://admin.example.com:8443/api")

# Validate before storing
if URLConfig.validate(url.url):
    url_config = URLConfig(apdu)
    url_config.configure(url)
    print("URL configured successfully")

# Read current URL
current_url = url_config.read_configuration()
print(f"Admin URL: {current_url.url}")
```

---

## Advanced Usage

### Manage Security Domains

```python
from cardlink.provisioner import SecureDomainManager, ISD_AID

sd_manager = SecureDomainManager(apdu)

# Select ISD
sd_manager.select_isd()

# Get ISD status
isd_info = sd_manager.get_status_isd()
print(f"ISD AID: {isd_info.aid.hex()}")
print(f"ISD State: {isd_info.lifecycle_state.name}")

# List applications
apps = sd_manager.get_status_apps()
for app in apps:
    print(f"Application: {app.aid.hex()}")
    print(f"  State: {app.lifecycle_state.name}")
    print(f"  Privileges: {[p.value for p in app.privileges]}")
```

### TLV Parsing

```python
from cardlink.provisioner import TLVParser

# Parse TLV data
data = bytes.fromhex("5F50064E616D653132")
tlv_list = TLVParser.parse(data)

for tlv in tlv_list:
    print(f"Tag: {tlv.tag:04X}")
    print(f"Length: {tlv.length}")
    print(f"Value: {tlv.value.hex()}")

# Build TLV
tlv_data = TLVParser.build(0x5F50, b"Name12")
print(f"TLV: {tlv_data.hex()}")
```

### Key Derivation

```python
from cardlink.provisioner.key_manager import KeyManager

# Generate master key
master_key = KeyManager.generate_random_key(32)

# Derive keys for different purposes
enc_key = KeyManager.derive_key(
    master_key,
    info=b"encryption",
    length=16,
)
mac_key = KeyManager.derive_key(
    master_key,
    info=b"mac",
    length=16,
)

# Secure comparison
if KeyManager.secure_compare(key1, key2):
    print("Keys match")
```

### Custom APDU Scripts

```python
# Execute sequence of commands
commands = [
    "00A4040008A000000151000000",  # SELECT ISD
    "80CA006600",                   # GET DATA (Card Data)
    "80F28000024F00",               # GET STATUS (ISD)
]

for cmd_hex in commands:
    cmd_bytes = bytes.fromhex(cmd_hex)
    response = client.transmit(cmd_bytes)
    sw = (response[-2] << 8) | response[-1]
    print(f"Command: {cmd_hex}")
    print(f"Response: {response.hex()}")
    print(f"SW: {sw:04X}\n")
```

---

## Troubleshooting

### Connection Issues

#### Problem: "No readers found"

**Solutions:**
1. Check reader is plugged in
2. Verify PC/SC daemon is running:
   ```bash
   # Linux
   sudo systemctl status pcscd

   # If not running
   sudo systemctl start pcscd
   ```
3. Check USB permissions (Linux):
   ```bash
   sudo usermod -a -G pcscd $USER
   ```
4. Try a different USB port
5. Install reader drivers from manufacturer

#### Problem: "Card not detected"

**Solutions:**
1. Remove and reinsert card
2. Check card orientation (contacts down)
3. Clean card contacts with isopropyl alcohol
4. Test with different card
5. Check reader LED indicator

#### Problem: "Connection failed with error 6"

**Solutions:**
1. Card may be removed during operation
2. Reader may have lost power
3. Try reconnecting:
   ```python
   client.disconnect()
   client.connect(reader_name)
   ```

### APDU Errors

#### Problem: "SW=6A82 (File not found)"

**Solutions:**
1. File doesn't exist on card
2. Wrong file path/AID
3. Need to create file first
4. Check card supports the file

**Example Fix:**
```python
try:
    apdu.select_by_path("2F50")
except APDUError as e:
    if e.sw == 0x6A82:
        print("File not found - may need to create it")
        # Create file or use different path
```

#### Problem: "SW=6982 (Security status not satisfied)"

**Solutions:**
1. Operation requires authentication
2. Need to establish secure channel
3. Wrong keys used
4. PIN not verified

**Example Fix:**
```python
# Establish secure channel first
scp = SCP02(apdu)
scp.initialize()

# Then perform operation
psk_config = PSKConfig(apdu, secure_channel=scp.send)
psk_config.configure(psk)
```

#### Problem: "SW=6985 (Conditions not satisfied)"

**Solutions:**
1. Card lifecycle state doesn't allow operation
2. Application not selected
3. Prerequisites not met

**Example Fix:**
```python
# Select ISD first
sd_manager.select_isd()

# Then perform operation
apps = sd_manager.get_status_apps()
```

### Authentication Errors

#### Problem: "Authentication failed - wrong cryptogram"

**Solutions:**
1. Using wrong keys
2. Key diversification not matching
3. Card using different SCP version

**Example Fix:**
```python
# Try default test keys
scp = SCP02(apdu)
scp.initialize()  # Uses default test keys

# Or try specific key set
keys = SCPKeys(
    enc=bytes.fromhex("YOUR_ENC_KEY"),
    mac=bytes.fromhex("YOUR_MAC_KEY"),
    dek=bytes.fromhex("YOUR_DEK_KEY"),
)
scp = SCP02(apdu, keys)
scp.initialize()
```

### Platform-Specific Issues

#### Linux: Permission Denied

```bash
# Add user to pcscd group
sudo usermod -a -G pcscd $USER

# Or run with sudo (not recommended)
sudo python3 your_script.py
```

#### macOS: Smart Card Services

```bash
# Check if service is running
launchctl list | grep com.apple.securityd

# Restart if needed
sudo killall -HUP pcscd
```

#### Windows: Driver Issues

1. Download driver from reader manufacturer
2. Install driver
3. Restart computer
4. Check Device Manager for reader

---

## API Reference

### PCSCClient

```python
class PCSCClient:
    """PC/SC client for card communication."""

    def list_readers() -> List[ReaderInfo]:
        """List all available PC/SC readers."""

    def connect(reader_name: str, protocol: Protocol = Protocol.ANY):
        """Connect to card in specified reader."""

    def disconnect():
        """Disconnect from card."""

    def transmit(apdu: bytes) -> bytes:
        """Transmit APDU to card."""

    @property
    def is_connected() -> bool:
        """Check if connected to card."""

    @property
    def card_info() -> CardInfo:
        """Get information about connected card."""
```

### APDUInterface

```python
class APDUInterface:
    """High-level APDU command interface."""

    def send(command: APDUCommand) -> APDUResponse:
        """Send APDU command."""

    def select_by_aid(aid: str) -> APDUResponse:
        """SELECT application by AID."""

    def select_by_path(path: str) -> APDUResponse:
        """SELECT file by path."""

    def read_binary(offset: int, length: int) -> APDUResponse:
        """READ BINARY from current file."""

    def update_binary(offset: int, data: bytes) -> APDUResponse:
        """UPDATE BINARY in current file."""
```

### PSKConfig

```python
class PSKConfig:
    """PSK configuration manager."""

    def __init__(apdu_interface, secure_channel=None):
        """Initialize PSK config manager."""

    def configure(psk: PSKConfiguration):
        """Configure PSK on card."""

    def read_configuration() -> PSKConfiguration:
        """Read current PSK identity."""

    def verify(expected: PSKConfiguration) -> bool:
        """Verify PSK identity matches."""
```

### URLConfig

```python
class URLConfig:
    """URL configuration manager."""

    def __init__(apdu_interface):
        """Initialize URL config manager."""

    def configure(config: URLConfiguration):
        """Configure admin URL on card."""

    def read_configuration() -> URLConfiguration:
        """Read current URL."""

    @staticmethod
    def validate(url: str) -> bool:
        """Validate URL format."""
```

### KeyManager

```python
class KeyManager:
    """Cryptographic key management utilities."""

    @staticmethod
    def generate_random_key(size: int) -> bytes:
        """Generate cryptographically secure random key."""

    @staticmethod
    def derive_key(master_key, salt=None, info=None, length=32) -> bytes:
        """Derive key using HKDF."""

    @staticmethod
    def secure_compare(a: bytes, b: bytes) -> bool:
        """Compare in constant time."""

    @staticmethod
    def secure_erase(data: bytearray):
        """Erase sensitive data from memory."""
```

---

## Best Practices

### Security

1. **Always use secure channel** for writing keys:
   ```python
   psk_config = PSKConfig(apdu, secure_channel=scp.send)
   ```

2. **Don't log sensitive data**:
   ```python
   # Good
   logger.info(f"Configured PSK for identity: {psk.identity}")

   # Bad - don't log keys!
   logger.info(f"PSK key: {psk.key.hex()}")
   ```

3. **Erase keys after use**:
   ```python
   key_array = bytearray(psk.key)
   # Use key...
   KeyManager.secure_erase(key_array)
   ```

4. **Use strong random keys**:
   ```python
   # Good - cryptographically secure
   key = KeyManager.generate_random_key(16)

   # Bad - not secure
   key = bytes(range(16))
   ```

### Resource Management

1. **Always disconnect**:
   ```python
   try:
       client.connect(reader)
       # Operations...
   finally:
       client.disconnect()
   ```

2. **Or use context manager** (if implemented):
   ```python
   with PCSCClient() as client:
       client.connect(reader)
       # Operations...
   ```

3. **Check connection state**:
   ```python
   if client.is_connected:
       response = apdu.send(command)
   ```

### Error Handling

1. **Catch specific exceptions**:
   ```python
   from cardlink.provisioner import APDUError, SecurityError

   try:
       psk_config.configure(psk)
   except SecurityError:
       print("Secure channel required")
   except APDUError as e:
       print(f"APDU failed: SW={e.sw:04X}")
   ```

2. **Validate before operations**:
   ```python
   if URLConfig.validate(url):
       url_config.configure(url_conf)
   else:
       print("Invalid URL format")
   ```

3. **Check response status**:
   ```python
   response = apdu.send(command)
   if response.is_success:
       process_data(response.data)
   else:
       print(f"Failed: {response.status_message}")
   ```

---

## Examples

### Complete Provisioning Script

```python
#!/usr/bin/env python3
"""
Complete UICC card provisioning script.
Configures PSK credentials and admin URL on a test card.
"""

import sys
from cardlink.provisioner import (
    PCSCClient,
    APDUInterface,
    SecureDomainManager,
    SCP02,
)
from cardlink.provisioner.psk_config import PSKConfig
from cardlink.provisioner.url_config import URLConfig
from cardlink.provisioner.models import PSKConfiguration, URLConfiguration


def provision_card(reader_name: str, identity: str, admin_url: str):
    """Provision a UICC card with PSK and URL configuration.

    Args:
        reader_name: PC/SC reader name
        identity: PSK identity for the card
        admin_url: Admin server URL
    """
    client = None

    try:
        # Connect to card
        print(f"Connecting to reader: {reader_name}")
        client = PCSCClient()
        client.connect(reader_name)
        print(f"✓ Connected, ATR: {client.card_info.atr_hex}")

        # Create interfaces
        apdu = APDUInterface(client.transmit)
        sd_manager = SecureDomainManager(apdu)

        # Select ISD
        print("\nSelecting ISD...")
        sd_manager.select_isd()
        print("✓ ISD selected")

        # Establish secure channel
        print("\nEstablishing secure channel (SCP02)...")
        scp = SCP02(apdu)
        scp.initialize()
        print("✓ Secure channel established")

        # Generate PSK
        print(f"\nGenerating PSK for identity: {identity}")
        psk = PSKConfiguration.generate(identity, key_size=16)
        print(f"✓ Generated PSK key: {psk.key.hex()}")

        # Configure PSK
        print("\nConfiguring PSK on card...")
        psk_config = PSKConfig(apdu, secure_channel=scp.send)
        psk_config.configure(psk)
        print("✓ PSK configured")

        # Configure URL
        print(f"\nConfiguring admin URL: {admin_url}")
        url = URLConfiguration.from_url(admin_url)
        url_config = URLConfig(apdu)
        url_config.configure(url)
        print("✓ Admin URL configured")

        # Verify configuration
        print("\nVerifying configuration...")
        current_psk = psk_config.read_configuration()
        current_url = url_config.read_configuration()

        print(f"✓ PSK Identity: {current_psk.identity}")
        print(f"✓ Admin URL: {current_url.url}")

        # Final verification
        if psk_config.verify(psk):
            print("\n✅ Provisioning completed successfully!")
            return 0
        else:
            print("\n❌ Verification failed!")
            return 1

    except Exception as e:
        print(f"\n❌ Error: {e}")
        return 1

    finally:
        if client and client.is_connected:
            client.disconnect()
            print("\nDisconnected from card")


def main():
    """Main entry point."""
    if len(sys.argv) != 4:
        print("Usage: provision.py <reader_name> <identity> <admin_url>")
        print("\nExample:")
        print('  provision.py "ACS ACR122U" card_001 https://admin.example.com:8443/api')
        return 1

    reader_name = sys.argv[1]
    identity = sys.argv[2]
    admin_url = sys.argv[3]

    return provision_card(reader_name, identity, admin_url)


if __name__ == "__main__":
    sys.exit(main())
```

**Usage:**
```bash
python provision.py "ACS ACR122U PICC Interface 00 00" card_001 https://admin.example.com:8443/api
```

---

## Support

### Getting Help

- **Documentation**: [https://github.com/your-org/cardlink](https://github.com/your-org/cardlink)
- **Issues**: [https://github.com/your-org/cardlink/issues](https://github.com/your-org/cardlink/issues)
- **Discussions**: [https://github.com/your-org/cardlink/discussions](https://github.com/your-org/cardlink/discussions)

### Common Resources

- **GlobalPlatform Specification**: [https://globalplatform.org](https://globalplatform.org)
- **PC/SC Workgroup**: [https://pcscworkgroup.com](https://pcscworkgroup.com)
- **pyscard Documentation**: [https://pyscard.sourceforge.io](https://pyscard.sourceforge.io)

---

## Appendix

### Status Word Reference

| SW     | Meaning                              |
|--------|--------------------------------------|
| `9000` | Success                              |
| `61XX` | More data available (XX bytes)       |
| `6200` | Warning: No information given        |
| `6281` | Part of data may be corrupted        |
| `6282` | End of file reached                  |
| `6283` | Selected file invalidated            |
| `6300` | Authentication failed                |
| `63CX` | Counter (X retries remaining)        |
| `6400` | Execution error: State unchanged     |
| `6581` | Memory failure                       |
| `6700` | Wrong length (Lc or Le)             |
| `6882` | Secure messaging not supported       |
| `6982` | Security status not satisfied        |
| `6983` | Authentication method blocked        |
| `6985` | Conditions not satisfied             |
| `6986` | Command not allowed                  |
| `6A80` | Incorrect parameters in data field   |
| `6A81` | Function not supported               |
| `6A82` | File not found                       |
| `6A83` | Record not found                     |
| `6A84` | Not enough memory                    |
| `6A86` | Incorrect P1 P2                      |
| `6A88` | Referenced data not found            |
| `6CXX` | Wrong Le (XX = correct Le)          |
| `6D00` | INS not supported                    |
| `6E00` | CLA not supported                    |
| `6F00` | Unknown error                        |

### Sample ATR Database

Common UICC card ATRs:

```
# Gemalto (Thales) UICC
3B9F96801F478031E073FE211B6305040022A78360B0

# G&D UICC
3B9F95801FC78031E073FE211B6305040022C17879B0

# Oberthur (IDEMIA) UICC
3B9F96801F438031E073FE211B6305040022A5803680

# Generic JavaCard
3B6800009C01000000000000

# eUICC (eSIM)
3B9F96801FC78031A073BE211365020007901580
```

---

**End of User Guide**

*For technical questions or contributions, please visit our GitHub repository.*
