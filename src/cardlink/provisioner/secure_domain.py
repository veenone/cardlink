"""Security Domain Manager for GlobalPlatform card operations.

This module provides management of Security Domains on GlobalPlatform cards,
including ISD selection, application listing, installation, deletion,
and key management.

Example:
    ```python
    from cardlink.provisioner import PCSCClient, SecureDomainManager

    client = PCSCClient()
    client.connect(0)

    sd_manager = SecureDomainManager(client.transmit)

    # Select ISD
    sd_manager.select_isd()

    # List applications
    apps = sd_manager.get_status_apps()
    for app in apps:
        print(f"AID: {app.aid.hex()} State: {app.lifecycle_state}")

    # Delete application
    sd_manager.delete("A0000000041010")

    client.disconnect()
    ```
"""

import logging
from typing import Callable, List, Optional, Union

from cardlink.provisioner.apdu_interface import APDUInterface, SWDecoder
from cardlink.provisioner.exceptions import (
    APDUError,
    InvalidAPDUError,
    ProvisionerError,
    SecurityError,
)
from cardlink.provisioner.models import (
    APDUCommand,
    APDUResponse,
    ApplicationInfo,
    INS,
    LifeCycleState,
    Privilege,
    SecurityDomainInfo,
)
from cardlink.provisioner.tlv_parser import TLV, TLVParser, Tags

logger = logging.getLogger(__name__)


# =============================================================================
# Constants
# =============================================================================

# Standard ISD AID (GlobalPlatform)
ISD_AID = bytes.fromhex("A000000151000000")

# Alternative ISD AIDs used by some vendors
ISD_AID_SHORT = bytes.fromhex("A0000001510000")
ISD_AID_VISA = bytes.fromhex("A0000000030000")

# GlobalPlatform CLA byte
GP_CLA = 0x80

# GET STATUS P1 values
GET_STATUS_ISD = 0x80  # Issuer Security Domain
GET_STATUS_APPS = 0x40  # Applications and Security Domains
GET_STATUS_LOAD_FILES = 0x20  # Executable Load Files
GET_STATUS_LOAD_FILES_MODULES = 0x10  # Load Files and Modules

# GET STATUS P2 values
GET_STATUS_FIRST_OR_ALL = 0x00
GET_STATUS_NEXT = 0x01
GET_STATUS_TLV_FORMAT = 0x02

# INSTALL P1 values
INSTALL_FOR_LOAD = 0x02
INSTALL_FOR_INSTALL = 0x04
INSTALL_FOR_MAKE_SELECTABLE = 0x08
INSTALL_FOR_INSTALL_AND_MAKE_SELECTABLE = 0x0C
INSTALL_FOR_EXTRADITION = 0x10
INSTALL_FOR_PERSONALIZATION = 0x20
INSTALL_FOR_REGISTRY_UPDATE = 0x40

# DELETE P2 values
DELETE_CARD_CONTENT = 0x00
DELETE_CARD_CONTENT_AND_REGISTRY = 0x80

# Transmit function type
TransmitFunc = Callable[[bytes], APDUResponse]


# =============================================================================
# Security Domain Manager
# =============================================================================


class SecureDomainManager:
    """Manager for GlobalPlatform Security Domain operations.

    This class provides methods for managing Security Domains on GlobalPlatform
    cards, including selecting domains, listing applications, installing and
    deleting applications, and managing keys.

    Attributes:
        is_isd_selected: Whether the ISD is currently selected.
        current_sd_aid: AID of the currently selected Security Domain.

    Example:
        ```python
        manager = SecureDomainManager(client.transmit)
        manager.select_isd()

        # Get ISD info
        isd_info = manager.get_status_isd()
        print(f"ISD State: {isd_info.lifecycle_state}")

        # List all apps
        for app in manager.get_status_apps():
            print(f"  {app.aid.hex()}: {app.lifecycle_state.name}")
        ```
    """

    def __init__(
        self,
        transmit_func: TransmitFunc,
        auto_get_response: bool = True,
    ):
        """Initialize Security Domain Manager.

        Args:
            transmit_func: Function to transmit APDU and receive response.
            auto_get_response: Automatically handle GET RESPONSE (SW=61xx).
        """
        self._apdu = APDUInterface(transmit_func, auto_get_response)
        self._is_isd_selected = False
        self._current_sd_aid: Optional[bytes] = None

    @property
    def is_isd_selected(self) -> bool:
        """Check if ISD is currently selected."""
        return self._is_isd_selected

    @property
    def current_sd_aid(self) -> Optional[bytes]:
        """Get AID of currently selected Security Domain."""
        return self._current_sd_aid

    # =========================================================================
    # Selection Methods
    # =========================================================================

    def select_isd(self, aid: Optional[bytes] = None) -> APDUResponse:
        """Select the Issuer Security Domain (ISD).

        Args:
            aid: Optional custom ISD AID. Uses default if not specified.

        Returns:
            SELECT response with FCI data.

        Raises:
            APDUError: If selection fails.
        """
        if aid is None:
            aid = ISD_AID

        response = self._apdu.select_by_aid(aid)

        if response.is_success:
            self._is_isd_selected = True
            self._current_sd_aid = aid
            logger.info(f"ISD selected: {aid.hex().upper()}")
        elif response.sw == 0x6A82:
            # Try shorter AID
            response = self._apdu.select_by_aid(ISD_AID_SHORT)
            if response.is_success:
                self._is_isd_selected = True
                self._current_sd_aid = ISD_AID_SHORT
                logger.info(f"ISD selected (short AID): {ISD_AID_SHORT.hex().upper()}")
            else:
                raise APDUError(
                    response.sw1,
                    response.sw2,
                    "SELECT ISD",
                    "ISD not found - card may not be GlobalPlatform compliant",
                )
        else:
            raise APDUError(
                response.sw1,
                response.sw2,
                "SELECT ISD",
                SWDecoder.decode(response.sw1, response.sw2),
            )

        return response

    def select_sd(self, aid: Union[bytes, str]) -> APDUResponse:
        """Select a Security Domain by AID.

        Args:
            aid: Security Domain AID as bytes or hex string.

        Returns:
            SELECT response with FCI data.

        Raises:
            APDUError: If selection fails.
        """
        if isinstance(aid, str):
            aid = bytes.fromhex(aid.replace(" ", ""))

        response = self._apdu.select_by_aid(aid)

        if response.is_success:
            self._current_sd_aid = aid
            self._is_isd_selected = aid == ISD_AID or aid == ISD_AID_SHORT
            logger.info(f"Security Domain selected: {aid.hex().upper()}")
        else:
            raise APDUError(
                response.sw1,
                response.sw2,
                f"SELECT SD {aid.hex()}",
                SWDecoder.decode(response.sw1, response.sw2),
            )

        return response

    def select_application(self, aid: Union[bytes, str]) -> APDUResponse:
        """Select an application by AID.

        Args:
            aid: Application AID as bytes or hex string.

        Returns:
            SELECT response.

        Raises:
            APDUError: If selection fails.
        """
        if isinstance(aid, str):
            aid = bytes.fromhex(aid.replace(" ", ""))

        response = self._apdu.select_by_aid(aid)

        if response.is_success:
            self._current_sd_aid = None  # Not a SD
            self._is_isd_selected = False
            logger.info(f"Application selected: {aid.hex().upper()}")

        return response

    # =========================================================================
    # GET STATUS Methods
    # =========================================================================

    def get_status_isd(self) -> SecurityDomainInfo:
        """Get status of the Issuer Security Domain.

        Returns:
            SecurityDomainInfo for the ISD.

        Raises:
            APDUError: If GET STATUS fails.
            ProvisionerError: If ISD not selected.
        """
        if not self._is_isd_selected:
            self.select_isd()

        response = self._get_status(GET_STATUS_ISD)
        items = self._parse_get_status_response(response.data)

        if not items:
            raise ProvisionerError("Failed to parse ISD status")

        return items[0]

    def get_status_apps(
        self,
        aid_filter: Optional[Union[bytes, str]] = None,
    ) -> List[SecurityDomainInfo]:
        """Get status of applications and Security Domains.

        Args:
            aid_filter: Optional AID prefix filter.

        Returns:
            List of SecurityDomainInfo for matching applications.

        Raises:
            APDUError: If GET STATUS fails.
        """
        if not self._is_isd_selected:
            self.select_isd()

        if isinstance(aid_filter, str):
            aid_filter = bytes.fromhex(aid_filter.replace(" ", ""))

        all_items = []

        # Get first batch
        response = self._get_status(GET_STATUS_APPS, aid_filter=aid_filter)

        if response.is_success:
            items = self._parse_get_status_response(response.data)
            all_items.extend(items)

            # Get remaining batches (if more data available)
            while response.sw == 0x6310:  # More data available
                response = self._get_status(
                    GET_STATUS_APPS,
                    p2=GET_STATUS_NEXT | GET_STATUS_TLV_FORMAT,
                    aid_filter=aid_filter,
                )
                if response.data:
                    items = self._parse_get_status_response(response.data)
                    all_items.extend(items)

        return all_items

    def get_status_load_files(
        self,
        aid_filter: Optional[Union[bytes, str]] = None,
        include_modules: bool = False,
    ) -> List[ApplicationInfo]:
        """Get status of Executable Load Files.

        Args:
            aid_filter: Optional AID prefix filter.
            include_modules: Include module AIDs in response.

        Returns:
            List of ApplicationInfo for load files.
        """
        if not self._is_isd_selected:
            self.select_isd()

        if isinstance(aid_filter, str):
            aid_filter = bytes.fromhex(aid_filter.replace(" ", ""))

        p1 = GET_STATUS_LOAD_FILES_MODULES if include_modules else GET_STATUS_LOAD_FILES

        response = self._get_status(p1, aid_filter=aid_filter)
        return self._parse_load_file_response(response.data) if response.data else []

    def _get_status(
        self,
        p1: int,
        p2: int = GET_STATUS_TLV_FORMAT,
        aid_filter: Optional[bytes] = None,
    ) -> APDUResponse:
        """Send GET STATUS command.

        Args:
            p1: Status type (ISD, Apps, Load Files).
            p2: Response format.
            aid_filter: Optional AID filter.

        Returns:
            GET STATUS response.
        """
        # Build command data (4F tag with AID filter)
        if aid_filter:
            data = bytes([Tags.AID, len(aid_filter)]) + aid_filter
        else:
            data = bytes([Tags.AID, 0x00])  # Empty filter = all

        command = APDUCommand(
            cla=GP_CLA,
            ins=INS.GET_STATUS,
            p1=p1,
            p2=p2,
            data=data,
            le=0,
        )

        response = self._apdu.send(command)

        # Accept 9000 (success), 6310 (more data), or 6A88 (not found)
        if response.sw not in [0x9000, 0x6310, 0x6A88]:
            raise APDUError(
                response.sw1,
                response.sw2,
                "GET STATUS",
                SWDecoder.decode(response.sw1, response.sw2),
            )

        return response

    def _parse_get_status_response(self, data: bytes) -> List[SecurityDomainInfo]:
        """Parse GET STATUS response data.

        Args:
            data: Response data in TLV format.

        Returns:
            List of SecurityDomainInfo entries.
        """
        result = []

        if not data:
            return result

        try:
            # Response contains multiple E3 (GP Registry Entry) TLVs
            offset = 0
            while offset < len(data):
                # Parse outer TLV
                if offset + 2 > len(data):
                    break

                tag = data[offset]
                offset += 1

                # Parse length
                length = data[offset]
                offset += 1

                if length & 0x80:
                    num_len_bytes = length & 0x7F
                    length = int.from_bytes(data[offset:offset + num_len_bytes], "big")
                    offset += num_len_bytes

                if offset + length > len(data):
                    break

                entry_data = data[offset:offset + length]
                offset += length

                # Parse entry (E3 tag for registry entry)
                if tag == 0xE3:
                    info = self._parse_registry_entry(entry_data)
                    if info:
                        result.append(info)

        except Exception as e:
            logger.warning(f"Error parsing GET STATUS response: {e}")

        return result

    def _parse_registry_entry(self, data: bytes) -> Optional[SecurityDomainInfo]:
        """Parse a single registry entry.

        Args:
            data: Entry data (contents of E3 TLV).

        Returns:
            SecurityDomainInfo or None if parsing fails.
        """
        aid = None
        lifecycle_state = LifeCycleState.UNKNOWN
        privileges = []
        executable_load_file_aid = None
        executable_module_aid = None

        try:
            tlvs = TLVParser.parse_all(data)

            for tlv in tlvs:
                if tlv.tag == Tags.AID:  # 4F - AID
                    aid = tlv.value
                elif tlv.tag == 0x9F70:  # Lifecycle state
                    if tlv.value:
                        lifecycle_state = self._decode_lifecycle_state(tlv.value[0])
                elif tlv.tag == 0xC5:  # Privileges
                    privileges = self._decode_privileges(tlv.value)
                elif tlv.tag == 0xC4:  # Executable Load File AID
                    executable_load_file_aid = tlv.value
                elif tlv.tag == 0xCE:  # Executable Module AID (Application)
                    executable_module_aid = tlv.value
                elif tlv.tag == 0xCF:  # Associated Security Domain AID
                    pass  # Could add to info if needed

        except Exception as e:
            logger.debug(f"Error parsing registry entry: {e}")
            return None

        if aid is None:
            return None

        return SecurityDomainInfo(
            aid=aid,
            lifecycle_state=lifecycle_state,
            privileges=privileges,
            executable_load_file_aid=executable_load_file_aid,
            executable_module_aid=executable_module_aid,
        )

    def _decode_lifecycle_state(self, state_byte: int) -> LifeCycleState:
        """Decode lifecycle state byte.

        Args:
            state_byte: Raw state byte from card.

        Returns:
            LifeCycleState enum value.
        """
        # GP lifecycle states
        state_map = {
            0x01: LifeCycleState.OP_READY,
            0x03: LifeCycleState.INITIALIZED,
            0x07: LifeCycleState.SECURED,
            0x0F: LifeCycleState.CARD_LOCKED,
            0x7F: LifeCycleState.TERMINATED,
            # Application states
            0x03: LifeCycleState.INSTALLED,
            0x07: LifeCycleState.SELECTABLE,
            0x83: LifeCycleState.LOCKED,
        }

        return state_map.get(state_byte, LifeCycleState.UNKNOWN)

    def _decode_privileges(self, priv_bytes: bytes) -> List[Privilege]:
        """Decode privileges byte(s).

        Args:
            priv_bytes: Privilege bytes from card.

        Returns:
            List of Privilege enum values.
        """
        privileges = []

        if not priv_bytes:
            return privileges

        priv = priv_bytes[0]

        if priv & 0x80:
            privileges.append(Privilege.SECURITY_DOMAIN)
        if priv & 0x40:
            privileges.append(Privilege.DAP_VERIFICATION)
        if priv & 0x20:
            privileges.append(Privilege.DELEGATED_MANAGEMENT)
        if priv & 0x10:
            privileges.append(Privilege.CARD_LOCK)
        if priv & 0x08:
            privileges.append(Privilege.CARD_TERMINATE)
        if priv & 0x04:
            privileges.append(Privilege.CARD_RESET)
        if priv & 0x02:
            privileges.append(Privilege.CVM_MANAGEMENT)
        if priv & 0x01:
            privileges.append(Privilege.MANDATED_DAP_VERIFICATION)

        # Check second privilege byte if present
        if len(priv_bytes) > 1:
            priv2 = priv_bytes[1]
            if priv2 & 0x80:
                privileges.append(Privilege.TRUSTED_PATH)
            if priv2 & 0x40:
                privileges.append(Privilege.AUTHORIZED_MANAGEMENT)
            if priv2 & 0x20:
                privileges.append(Privilege.TOKEN_VERIFICATION)
            if priv2 & 0x10:
                privileges.append(Privilege.GLOBAL_DELETE)
            if priv2 & 0x08:
                privileges.append(Privilege.GLOBAL_LOCK)
            if priv2 & 0x04:
                privileges.append(Privilege.GLOBAL_REGISTRY)
            if priv2 & 0x02:
                privileges.append(Privilege.FINAL_APPLICATION)
            if priv2 & 0x01:
                privileges.append(Privilege.RECEIPT_GENERATION)

        return privileges

    def _parse_load_file_response(self, data: bytes) -> List[ApplicationInfo]:
        """Parse GET STATUS response for load files.

        Args:
            data: Response data.

        Returns:
            List of ApplicationInfo for load files.
        """
        result = []

        try:
            offset = 0
            while offset < len(data):
                # Parse E3 TLV
                if data[offset] != 0xE3:
                    break

                offset += 1
                length = data[offset]
                offset += 1

                if length & 0x80:
                    num_len = length & 0x7F
                    length = int.from_bytes(data[offset:offset + num_len], "big")
                    offset += num_len

                entry_data = data[offset:offset + length]
                offset += length

                # Parse entry
                tlvs = TLVParser.parse_all(entry_data)
                aid = None
                lifecycle = LifeCycleState.UNKNOWN
                modules = []

                for tlv in tlvs:
                    if tlv.tag == Tags.AID:
                        aid = tlv.value
                    elif tlv.tag == 0x9F70:
                        lifecycle = self._decode_lifecycle_state(tlv.value[0]) if tlv.value else LifeCycleState.UNKNOWN
                    elif tlv.tag == 0x84:  # Module AID
                        modules.append(tlv.value)

                if aid:
                    result.append(ApplicationInfo(
                        aid=aid,
                        lifecycle_state=lifecycle,
                        module_aids=modules,
                    ))

        except Exception as e:
            logger.warning(f"Error parsing load file response: {e}")

        return result

    # =========================================================================
    # Installation Methods
    # =========================================================================

    def install_for_load(
        self,
        load_file_aid: Union[bytes, str],
        sd_aid: Optional[Union[bytes, str]] = None,
        load_file_data_block_hash: Optional[bytes] = None,
        load_parameters: Optional[bytes] = None,
        load_token: Optional[bytes] = None,
    ) -> APDUResponse:
        """INSTALL [for load] command to prepare for loading.

        Args:
            load_file_aid: AID of load file to be loaded.
            sd_aid: Associated Security Domain AID (defaults to ISD).
            load_file_data_block_hash: Hash for DAP verification.
            load_parameters: Load parameters.
            load_token: Token for delegated management.

        Returns:
            INSTALL response.

        Raises:
            APDUError: If installation fails.
        """
        if isinstance(load_file_aid, str):
            load_file_aid = bytes.fromhex(load_file_aid.replace(" ", ""))

        if isinstance(sd_aid, str):
            sd_aid = bytes.fromhex(sd_aid.replace(" ", ""))

        # Build install data
        data = bytearray()

        # Load file AID (length + data)
        data.append(len(load_file_aid))
        data.extend(load_file_aid)

        # Security Domain AID (length + data, or 00 for ISD)
        if sd_aid:
            data.append(len(sd_aid))
            data.extend(sd_aid)
        else:
            data.append(0x00)

        # Load file data block hash (length + data)
        if load_file_data_block_hash:
            data.append(len(load_file_data_block_hash))
            data.extend(load_file_data_block_hash)
        else:
            data.append(0x00)

        # Load parameters (length + data)
        if load_parameters:
            data.append(len(load_parameters))
            data.extend(load_parameters)
        else:
            data.append(0x00)

        # Load token (length + data)
        if load_token:
            data.append(len(load_token))
            data.extend(load_token)
        else:
            data.append(0x00)

        command = APDUCommand(
            cla=GP_CLA,
            ins=INS.INSTALL,
            p1=INSTALL_FOR_LOAD,
            p2=0x00,
            data=bytes(data),
        )

        response = self._apdu.send(command)

        if not response.is_success:
            raise APDUError(
                response.sw1,
                response.sw2,
                "INSTALL [for load]",
                SWDecoder.decode(response.sw1, response.sw2),
            )

        logger.info(f"INSTALL [for load] successful: {load_file_aid.hex().upper()}")
        return response

    def install_for_install(
        self,
        load_file_aid: Union[bytes, str],
        module_aid: Union[bytes, str],
        application_aid: Union[bytes, str],
        privileges: int = 0x00,
        install_parameters: Optional[bytes] = None,
        install_token: Optional[bytes] = None,
    ) -> APDUResponse:
        """INSTALL [for install and make selectable] command.

        Args:
            load_file_aid: AID of the executable load file.
            module_aid: AID of the module in the load file.
            application_aid: AID to assign to the application instance.
            privileges: Privilege byte(s).
            install_parameters: Application-specific install parameters.
            install_token: Token for delegated management.

        Returns:
            INSTALL response.

        Raises:
            APDUError: If installation fails.
        """
        if isinstance(load_file_aid, str):
            load_file_aid = bytes.fromhex(load_file_aid.replace(" ", ""))
        if isinstance(module_aid, str):
            module_aid = bytes.fromhex(module_aid.replace(" ", ""))
        if isinstance(application_aid, str):
            application_aid = bytes.fromhex(application_aid.replace(" ", ""))

        # Build install data
        data = bytearray()

        # Executable Load File AID
        data.append(len(load_file_aid))
        data.extend(load_file_aid)

        # Executable Module AID
        data.append(len(module_aid))
        data.extend(module_aid)

        # Application AID
        data.append(len(application_aid))
        data.extend(application_aid)

        # Privileges (1 byte minimum)
        data.append(0x01)
        data.append(privileges)

        # Install parameters (C9 tag TLV format)
        if install_parameters:
            # Wrap in C9 TLV
            params = bytes([0xC9, len(install_parameters)]) + install_parameters
            data.append(len(params))
            data.extend(params)
        else:
            data.append(0x02)  # Length of C9 00 (empty parameters)
            data.extend([0xC9, 0x00])

        # Install token
        if install_token:
            data.append(len(install_token))
            data.extend(install_token)
        else:
            data.append(0x00)

        command = APDUCommand(
            cla=GP_CLA,
            ins=INS.INSTALL,
            p1=INSTALL_FOR_INSTALL_AND_MAKE_SELECTABLE,
            p2=0x00,
            data=bytes(data),
        )

        response = self._apdu.send(command)

        if not response.is_success:
            raise APDUError(
                response.sw1,
                response.sw2,
                "INSTALL [for install]",
                SWDecoder.decode(response.sw1, response.sw2),
            )

        logger.info(f"INSTALL [for install] successful: {application_aid.hex().upper()}")
        return response

    def install_for_personalization(
        self,
        application_aid: Union[bytes, str],
    ) -> APDUResponse:
        """INSTALL [for personalization] command.

        Args:
            application_aid: AID of application to personalize.

        Returns:
            INSTALL response.
        """
        if isinstance(application_aid, str):
            application_aid = bytes.fromhex(application_aid.replace(" ", ""))

        data = bytearray()

        # Empty load file and module AIDs
        data.append(0x00)
        data.append(0x00)

        # Application AID
        data.append(len(application_aid))
        data.extend(application_aid)

        # Empty privileges, parameters, token
        data.extend([0x00, 0x00, 0x00])

        command = APDUCommand(
            cla=GP_CLA,
            ins=INS.INSTALL,
            p1=INSTALL_FOR_PERSONALIZATION,
            p2=0x00,
            data=bytes(data),
        )

        response = self._apdu.send(command)

        if not response.is_success:
            raise APDUError(
                response.sw1,
                response.sw2,
                "INSTALL [for personalization]",
                SWDecoder.decode(response.sw1, response.sw2),
            )

        return response

    # =========================================================================
    # Deletion Methods
    # =========================================================================

    def delete(
        self,
        aid: Union[bytes, str],
        cascade: bool = False,
        delete_related_objects: bool = False,
    ) -> APDUResponse:
        """DELETE command to remove application or load file.

        Args:
            aid: AID of object to delete.
            cascade: Delete related objects (packages for apps, apps for packages).
            delete_related_objects: Include related key packages, etc.

        Returns:
            DELETE response.

        Raises:
            APDUError: If deletion fails.
        """
        if isinstance(aid, str):
            aid = bytes.fromhex(aid.replace(" ", ""))

        # Build delete data (4F TLV)
        data = bytes([Tags.AID, len(aid)]) + aid

        # P2 indicates cascade behavior
        p2 = DELETE_CARD_CONTENT_AND_REGISTRY if delete_related_objects else DELETE_CARD_CONTENT

        command = APDUCommand(
            cla=GP_CLA,
            ins=INS.DELETE,
            p1=0x00,
            p2=p2,
            data=data,
        )

        response = self._apdu.send(command)

        # 6A88 = not found (may already be deleted)
        if response.sw == 0x6A88:
            logger.warning(f"Object not found for deletion: {aid.hex().upper()}")
            return response

        if not response.is_success:
            raise APDUError(
                response.sw1,
                response.sw2,
                f"DELETE {aid.hex()}",
                SWDecoder.decode(response.sw1, response.sw2),
            )

        logger.info(f"DELETE successful: {aid.hex().upper()}")

        # Cascade delete if requested
        if cascade:
            # Try to delete related objects - ignore errors
            try:
                self.delete(aid, cascade=False)
            except APDUError:
                pass

        return response

    # =========================================================================
    # Key Management Methods
    # =========================================================================

    def put_key(
        self,
        key_version: int,
        key_id: int,
        key_type: int,
        key_data: bytes,
        check_value: Optional[bytes] = None,
        replace: bool = False,
    ) -> APDUResponse:
        """PUT KEY command to add or replace keys.

        Args:
            key_version: Key version number (0x00 for new).
            key_id: Key identifier.
            key_type: Key type (e.g., 0x80 for DES, 0x88 for AES).
            key_data: Key data (typically encrypted).
            check_value: Optional key check value (KCV).
            replace: Replace existing key if True.

        Returns:
            PUT KEY response.

        Raises:
            APDUError: If PUT KEY fails.
        """
        # Build key data TLV
        data = bytearray()

        # New key version number
        new_version = key_version if replace else 0x00
        data.append(new_version)

        # Key component TLV
        # First component (key data)
        data.append(key_type)  # Key type
        data.append(len(key_data) + 1)  # Length including encryption flag
        data.append(len(key_data))  # Actual key length
        data.extend(key_data)

        # Key check value
        if check_value:
            data.append(len(check_value))
            data.extend(check_value)
        else:
            data.append(0x03)  # Standard KCV length
            data.extend([0x00, 0x00, 0x00])  # Placeholder KCV

        # P1: key version (to replace) or 00
        # P2: key ID | 0x80 if multiple keys
        command = APDUCommand(
            cla=GP_CLA,
            ins=INS.PUT_KEY,
            p1=key_version if replace else 0x00,
            p2=key_id,
            data=bytes(data),
        )

        response = self._apdu.send(command)

        if not response.is_success:
            raise APDUError(
                response.sw1,
                response.sw2,
                "PUT KEY",
                SWDecoder.decode(response.sw1, response.sw2),
            )

        logger.info(f"PUT KEY successful: version={key_version}, id={key_id}")
        return response

    # =========================================================================
    # Card Lifecycle Methods
    # =========================================================================

    def set_status(
        self,
        aid: Optional[Union[bytes, str]] = None,
        new_state: LifeCycleState = LifeCycleState.LOCKED,
    ) -> APDUResponse:
        """SET STATUS command to change lifecycle state.

        Args:
            aid: AID of application (None for ISD).
            new_state: New lifecycle state.

        Returns:
            SET STATUS response.
        """
        if isinstance(aid, str):
            aid = bytes.fromhex(aid.replace(" ", ""))

        # Map lifecycle state to P2
        state_map = {
            LifeCycleState.LOCKED: 0x83,
            LifeCycleState.CARD_LOCKED: 0x7F,
            LifeCycleState.TERMINATED: 0xFF,
        }

        if new_state not in state_map:
            raise ProvisionerError(f"Cannot set state to {new_state.name}")

        p2 = state_map[new_state]

        # P1: 0x80 for ISD/SD, 0x40 for application
        p1 = 0x80 if aid is None else 0x40

        # Data: AID if specified
        data = bytes([Tags.AID, len(aid)]) + aid if aid else b""

        command = APDUCommand(
            cla=GP_CLA,
            ins=INS.SET_STATUS,
            p1=p1,
            p2=p2,
            data=data if data else None,
        )

        response = self._apdu.send(command)

        if not response.is_success:
            raise APDUError(
                response.sw1,
                response.sw2,
                "SET STATUS",
                SWDecoder.decode(response.sw1, response.sw2),
            )

        return response

    # =========================================================================
    # Data Store Methods
    # =========================================================================

    def store_data(
        self,
        data: bytes,
        tag: int = 0x9E,
        p1: int = 0x00,
    ) -> APDUResponse:
        """STORE DATA command.

        Args:
            data: Data to store.
            tag: Tag for data (default 0x9E for general data).
            p1: P1 byte (DGI indicator).

        Returns:
            STORE DATA response.
        """
        # Wrap data in TLV
        tlv_data = TLVParser.build(tag, data)

        command = APDUCommand(
            cla=GP_CLA,
            ins=INS.STORE_DATA,
            p1=p1,
            p2=0x00,
            data=tlv_data,
        )

        response = self._apdu.send(command)

        if not response.is_success:
            raise APDUError(
                response.sw1,
                response.sw2,
                "STORE DATA",
                SWDecoder.decode(response.sw1, response.sw2),
            )

        return response

    def get_data_gp(self, tag: int) -> APDUResponse:
        """GET DATA command (GlobalPlatform).

        Args:
            tag: Data object tag.

        Returns:
            GET DATA response with data.
        """
        if tag > 0xFF:
            p1 = (tag >> 8) & 0xFF
            p2 = tag & 0xFF
        else:
            p1 = 0x00
            p2 = tag

        command = APDUCommand(
            cla=GP_CLA,
            ins=INS.GET_DATA,
            p1=p1,
            p2=p2,
            le=0,
        )

        return self._apdu.send(command)
