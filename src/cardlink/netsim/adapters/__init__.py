"""Network simulator adapters.

This package contains vendor-specific adapter implementations for
different network simulators.

Adapters:
    - AmarisoftAdapter: Amarisoft Callbox integration via JSON-RPC
    - GenericAdapter: Generic REST-based adapter for other simulators
"""

from cardlink.netsim.adapters.amarisoft import AmarisoftAdapter
from cardlink.netsim.adapters.generic import GenericAdapter

__all__ = [
    "AmarisoftAdapter",
    "GenericAdapter",
]
