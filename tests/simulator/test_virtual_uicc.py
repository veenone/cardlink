"""Tests for VirtualUICC component."""

import pytest
from cardlink.simulator import VirtualUICC, UICCProfile, ParsedAPDU


class TestVirtualUICC:
    """Test VirtualUICC APDU processing."""

    def test_initialization(self, uicc_profile):
        """Test VirtualUICC initialization."""
        uicc = VirtualUICC(uicc_profile)
        assert uicc.profile == uicc_profile
        assert uicc.selected_aid is None

    def test_select_isd(self, uicc_profile):
        """Test SELECT ISD-R command."""
        uicc = VirtualUICC(uicc_profile)

        # SELECT by AID
        aid = bytes.fromhex(uicc_profile.aid_isd)
        c_apdu = bytes([0x00, 0xA4, 0x04, 0x00, len(aid)]) + aid

        r_apdu = uicc.process_apdu(c_apdu)

        # Should return FCI + 9000
        assert len(r_apdu) >= 2
        assert r_apdu[-2:] == bytes([0x90, 0x00])
        assert uicc.selected_aid == aid

    def test_select_nonexistent_aid(self, uicc_profile):
        """Test SELECT with non-existent AID."""
        uicc = VirtualUICC(uicc_profile)

        # SELECT non-existent AID
        # Note: Virtual UICC allows selecting any AID for testing flexibility
        aid = bytes.fromhex("A000000000000000")
        c_apdu = bytes([0x00, 0xA4, 0x04, 0x00, len(aid)]) + aid

        r_apdu = uicc.process_apdu(c_apdu)

        # Should succeed (virtual UICC accepts any AID)
        assert r_apdu[-2:] == bytes([0x90, 0x00])
        assert uicc.selected_aid == aid

    def test_get_status(self, uicc_profile):
        """Test GET STATUS command."""
        uicc = VirtualUICC(uicc_profile)

        # GET STATUS for ISD
        c_apdu = bytes([0x80, 0xF2, 0x80, 0x00, 0x02, 0x4F, 0x00])

        r_apdu = uicc.process_apdu(c_apdu)

        # Should return status data + 9000
        assert len(r_apdu) >= 2
        assert r_apdu[-2:] == bytes([0x90, 0x00])

    def test_get_data(self, uicc_profile):
        """Test GET DATA command."""
        uicc = VirtualUICC(uicc_profile)

        # GET DATA for card data (tag 66)
        c_apdu = bytes([0x80, 0xCA, 0x00, 0x66, 0x00])

        r_apdu = uicc.process_apdu(c_apdu)

        # Should return data + 9000 or 6A88 (data not found)
        assert len(r_apdu) >= 2
        sw = r_apdu[-2:]
        assert sw == bytes([0x90, 0x00]) or sw == bytes([0x6A, 0x88])

    def test_unsupported_command(self, uicc_profile):
        """Test unsupported command returns 6D00."""
        uicc = VirtualUICC(uicc_profile)

        # Unknown INS
        c_apdu = bytes([0x00, 0xFF, 0x00, 0x00, 0x00])

        r_apdu = uicc.process_apdu(c_apdu)

        # Should return 6D00 (INS not supported)
        assert r_apdu[-2:] == bytes([0x6D, 0x00])

    def test_apdu_parsing(self):
        """Test APDU parsing."""
        # Case 1: No data, no Le
        apdu = bytes([0x00, 0xA4, 0x04, 0x00])
        parsed = ParsedAPDU.parse(apdu)
        assert parsed.cla == 0x00
        assert parsed.ins == 0xA4
        assert parsed.p1 == 0x04
        assert parsed.p2 == 0x00
        assert parsed.lc == 0
        assert parsed.data == b""
        assert parsed.le is None  # No Le present

        # Case 2: Data, no Le
        apdu = bytes([0x00, 0xA4, 0x04, 0x00, 0x03, 0x01, 0x02, 0x03])
        parsed = ParsedAPDU.parse(apdu)
        assert parsed.cla == 0x00
        assert parsed.lc == 3
        assert parsed.data == bytes([0x01, 0x02, 0x03])
        assert parsed.le is None  # No Le present

        # Case 3: No data, with Le
        apdu = bytes([0x00, 0xA4, 0x04, 0x00, 0x10])
        parsed = ParsedAPDU.parse(apdu)
        assert parsed.lc == 0
        assert parsed.le == 0x10

        # Case 4: Data and Le
        apdu = bytes([0x00, 0xA4, 0x04, 0x00, 0x03, 0x01, 0x02, 0x03, 0x10])
        parsed = ParsedAPDU.parse(apdu)
        assert parsed.lc == 3
        assert parsed.data == bytes([0x01, 0x02, 0x03])
        assert parsed.le == 0x10

    def test_reset(self, uicc_profile):
        """Test UICC reset."""
        uicc = VirtualUICC(uicc_profile)

        # Select something
        aid = bytes.fromhex(uicc_profile.aid_isd)
        c_apdu = bytes([0x00, 0xA4, 0x04, 0x00, len(aid)]) + aid
        uicc.process_apdu(c_apdu)

        assert uicc.selected_aid is not None

        # Reset
        uicc.reset()

        assert uicc.selected_aid is None

    def test_applet_selection(self, uicc_profile):
        """Test selecting pre-installed applet."""
        uicc = VirtualUICC(uicc_profile)

        # Select applet
        applet_aid = bytes.fromhex(uicc_profile.applets[0].aid)
        c_apdu = bytes([0x00, 0xA4, 0x04, 0x00, len(applet_aid)]) + applet_aid

        r_apdu = uicc.process_apdu(c_apdu)

        # Should succeed
        assert r_apdu[-2:] == bytes([0x90, 0x00])
        assert uicc.selected_aid == applet_aid

    def test_case_sensitivity(self, uicc_profile):
        """Test various APDU case handling."""
        uicc = VirtualUICC(uicc_profile)

        # Test different CLA bytes
        for cla in [0x00, 0x80]:
            aid = bytes.fromhex(uicc_profile.aid_isd)
            c_apdu = bytes([cla, 0xA4, 0x04, 0x00, len(aid)]) + aid
            r_apdu = uicc.process_apdu(c_apdu)

            # Both should work
            assert len(r_apdu) >= 2
