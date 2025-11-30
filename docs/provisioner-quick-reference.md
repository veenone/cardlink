# UICC Provisioner Quick Reference

## Installation

```bash
pip install gp-ota-tester[provisioner]
```

## Platform Setup

### Linux
```bash
sudo apt-get install pcscd pcsc-tools
sudo systemctl start pcscd
```

### macOS
```bash
# PC/SC built-in, no setup needed
```

### Windows
```powershell
# WinSCard built-in, no setup needed
```

## Basic Operations

### List Readers
```python
from cardlink.provisioner import list_readers

readers = list_readers()
for r in readers:
    print(f"{r.name} - Card: {r.has_card}")
```

### Connect to Card
```python
from cardlink.provisioner import PCSCClient

client = PCSCClient()
client.connect("Reader Name")
print(f"ATR: {client.card_info.atr_hex}")
```

### Send APDU
```python
from cardlink.provisioner import APDUInterface
from cardlink.provisioner.models import APDUCommand, INS

apdu = APDUInterface(client.transmit)
response = apdu.select_by_aid("A000000151000000")
print(f"SW: {response.sw:04X}")
```

## Security Operations

### Establish SCP02
```python
from cardlink.provisioner import SCP02

scp = SCP02(apdu)
scp.initialize()  # Uses default test keys
```

### Establish SCP03
```python
from cardlink.provisioner import SCP03

scp = SCP03(apdu)
scp.initialize()
```

### Custom Keys
```python
from cardlink.provisioner.models import SCPKeys

keys = SCPKeys(
    enc=bytes.fromhex("404142434445464748494A4B4C4D4E4F"),
    mac=bytes.fromhex("404142434445464748494A4B4C4D4E4F"),
    dek=bytes.fromhex("404142434445464748494A4B4C4D4E4F"),
)
scp = SCP02(apdu, keys)
scp.initialize()
```

## Configuration

### PSK Configuration
```python
from cardlink.provisioner.psk_config import PSKConfig
from cardlink.provisioner.models import PSKConfiguration

# Generate PSK
psk = PSKConfiguration.generate("card_001", key_size=16)
print(f"Key: {psk.key.hex()}")

# Configure (requires secure channel)
psk_config = PSKConfig(apdu, secure_channel=scp.send)
psk_config.configure(psk)

# Read back
current = psk_config.read_configuration()
print(f"Identity: {current.identity}")
```

### URL Configuration
```python
from cardlink.provisioner.url_config import URLConfig
from cardlink.provisioner.models import URLConfiguration

# Create URL
url = URLConfiguration.from_url("https://server.example.com:8443/admin")

# Configure
url_config = URLConfig(apdu)
url_config.configure(url)

# Read back
current = url_config.read_configuration()
print(f"URL: {current.url}")
```

## Key Management

### Generate Random Key
```python
from cardlink.provisioner.key_manager import KeyManager

key = KeyManager.generate_random_key(16)  # 128-bit
print(f"Key: {key.hex()}")
```

### Derive Key (HKDF)
```python
master = KeyManager.generate_random_key(32)
derived = KeyManager.derive_key(
    master,
    info=b"encryption",
    length=16
)
```

### Secure Comparison
```python
if KeyManager.secure_compare(key1, key2):
    print("Keys match")
```

## Utilities

### Parse ATR
```python
from cardlink.provisioner import parse_atr

atr_info = parse_atr(atr_bytes)
print(f"Type: {atr_info.card_type.value}")
print(f"Protocol: {atr_info.protocols}")
```

### TLV Operations
```python
from cardlink.provisioner import TLVParser

# Parse
tlv_list = TLVParser.parse(data)
for tlv in tlv_list:
    print(f"Tag: {tlv.tag:04X}, Value: {tlv.value.hex()}")

# Build
tlv = TLVParser.build(0x5F50, b"data")
```

### Manage Security Domains
```python
from cardlink.provisioner import SecureDomainManager

sd = SecureDomainManager(apdu)
sd.select_isd()

# List applications
apps = sd.get_status_apps()
for app in apps:
    print(f"AID: {app.aid.hex()}, State: {app.lifecycle_state.name}")
```

## Common Patterns

### Complete Provisioning
```python
# Connect
client = PCSCClient()
client.connect(reader_name)

# Setup
apdu = APDUInterface(client.transmit)
sd = SecureDomainManager(apdu)
sd.select_isd()

# Secure channel
scp = SCP02(apdu)
scp.initialize()

# Configure PSK
psk = PSKConfiguration.generate("card_001", 16)
psk_config = PSKConfig(apdu, secure_channel=scp.send)
psk_config.configure(psk)

# Configure URL
url = URLConfiguration.from_url("https://admin.example.com:8443")
url_config = URLConfig(apdu)
url_config.configure(url)

# Cleanup
client.disconnect()
```

### Error Handling
```python
from cardlink.provisioner import APDUError, SecurityError

try:
    psk_config.configure(psk)
except SecurityError:
    print("Secure channel required")
except APDUError as e:
    print(f"APDU failed: SW={e.sw:04X}")
```

## Status Words

| SW     | Meaning                     |
|--------|-----------------------------|
| `9000` | Success                     |
| `61XX` | More data (XX bytes)        |
| `6982` | Security not satisfied      |
| `6985` | Conditions not satisfied    |
| `6A82` | File not found              |
| `6A86` | Incorrect P1/P2             |
| `6D00` | INS not supported           |
| `6E00` | CLA not supported           |

## Common Issues

### No Readers Found
```bash
# Linux
sudo systemctl start pcscd

# Check
pcsc_scan
```

### Card Not Detected
- Reinsert card
- Clean contacts
- Check orientation

### Authentication Failed
```python
# Try default test keys
scp = SCP02(apdu)
scp.initialize()
```

### File Not Found (6A82)
```python
# File may not exist on card
# Check file path/create file
```

### Security Error (6982)
```python
# Establish secure channel first
scp = SCP02(apdu)
scp.initialize()
psk_config = PSKConfig(apdu, secure_channel=scp.send)
```

## API Quick Reference

### PCSCClient
- `list_readers()` - List all readers
- `connect(name, protocol)` - Connect to card
- `disconnect()` - Disconnect
- `transmit(apdu)` - Send APDU
- `is_connected` - Connection status
- `card_info` - Card information

### APDUInterface
- `send(command)` - Send APDU
- `select_by_aid(aid)` - SELECT by AID
- `select_by_path(path)` - SELECT by path
- `read_binary(offset, length)` - READ BINARY
- `update_binary(offset, data)` - UPDATE BINARY

### SCP02/SCP03
- `initialize(keys)` - Establish secure channel
- `send(command)` - Send secured APDU

### PSKConfig
- `configure(psk)` - Configure PSK
- `read_configuration()` - Read PSK identity
- `verify(psk)` - Verify PSK

### URLConfig
- `configure(url)` - Configure URL
- `read_configuration()` - Read URL
- `validate(url)` - Validate URL format

### KeyManager
- `generate_random_key(size)` - Generate key
- `derive_key(master, info, length)` - HKDF
- `secure_compare(a, b)` - Constant-time compare
- `secure_erase(data)` - Erase memory

## Resources

- **Full Guide**: [docs/provisioner-guide.md](provisioner-guide.md)
- **GlobalPlatform**: https://globalplatform.org
- **pyscard**: https://pyscard.sourceforge.io
- **Issues**: https://github.com/your-org/cardlink/issues
