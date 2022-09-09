# SPDX-FileCopyrightText: 2017 Scott Shawcroft, written for Adafruit Industries
# SPDX-FileCopyrightText: Copyright (c) 2022 Alec Delaney for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
`adafruit_ble_beacon`
================================================================================

BLE Location Beacon for CircuitPython


* Author(s): Alec Delaney

Implementation Notes
--------------------

**Hardware:**

.. todo:: Add links to any specific hardware product page(s), or category page(s).
  Use unordered list & hyperlink rST inline format: "* `Link Text <url>`_"

**Software and Dependencies:**

* Adafruit CircuitPython firmware for the supported boards:
  https://circuitpython.org/downloads

.. todo:: Uncomment or remove the Bus Device and/or the Register library dependencies
  based on the library's use of either.

# * Adafruit's Bus Device library: https://github.com/adafruit/Adafruit_CircuitPython_BusDevice
# * Adafruit's Register library: https://github.com/adafruit/Adafruit_CircuitPython_Register
"""

import struct
from micropython import const
import _bleio
from adafruit_ble.advertising import Advertisement, Struct, AdvertisingDataField
from adafruit_ble.advertising.standard import ManufacturerData

try:
    from typing import Optional, Union, Any, Type, Tuple, Sequence
except ImportError:
    pass

__version__ = "0.0.0+auto.0"
__repo__ = "https://github.com/tekktrik/Adafruit_CircuitPython_BLE_Beacon.git"

_MANUFACTURING_DATA_ADT = const(0xFF)

_APPLE_COMPANY_ID = const(0x004C)
_IBEACON_TYPE = const(0x02)
_IBEACON_LENGTH = const(0x15)

# TODO: fix this
_APPLE_COMPANY_ID_FLIPPED = const(0x4C00)


class MultiStruct(AdvertisingDataField):
    """`struct` encoded data in an Advertisement."""

    def __init__(self, struct_format: str, *, advertising_data_type: int) -> None:
        self._format = struct_format
        self._adt = advertising_data_type

    def __get__(
        self, obj: Optional["Advertisement"], cls: Type["Advertisement"]
    ) -> Optional[Union[Tuple, "Struct"]]:
        if obj is None:
            return self
        if self._adt not in obj.data_dict:
            return None
        return struct.unpack(self._format, obj.data_dict[self._adt])

    def __set__(self, obj: "Advertisement", value: Sequence) -> None:
        obj.data_dict[self._adt] = struct.pack(self._format, *value)

class _BeaconAdvertisement(Advertisement):
    """Advertisement for location beacons like iBeacon"""

    path_loss_const: int = 3
    """The path loss constant, typically between 2-4"""

    @property
    def distance(self) -> float:
        """The approximate distance to the beacon"""

        return 10**((self.beacon_tx_power - self.rssi) / (10*self.path_loss_const))

    @property
    def beacon_tx_power(self) -> int:
        raise NotImplementedError("Must be defined in beacon subclass")

    

class iBeaconAdvertisement(_BeaconAdvertisement):

    match_prefixes = (struct.pack("<BHBB", _MANUFACTURING_DATA_ADT, _APPLE_COMPANY_ID, _IBEACON_TYPE, _IBEACON_LENGTH),)

    _data_format = ">HBBQQHHb"
    _beacon_data = MultiStruct(_data_format, advertising_data_type=0xFF)

    def __init__(self, *, entry: Optional[_bleio.ScanEntry] = None, ) -> None:
        super().__init__(entry=entry)

        if not entry:
            self._init_struct()
    
    @property
    def uuid(self) -> bytes:
        _, _, _, uuid_msb, uuid_lsb, _, _, _ = self._beacon_data
        return struct.pack(">QQ", uuid_msb, uuid_lsb)

    @uuid.setter
    def uuid(self, id: bytes) -> None:
        uuid_msb, uuid_lsb = struct.unpack(">QQ", id)
        self._set_struct_index(3, uuid_msb)
        self._set_struct_index(4, uuid_lsb)


    @property
    def major(self) -> int:
        _, _, _, _, _, major, _, _ = self._beacon_data
        return major

    @major.setter
    def major(self, number: int) -> None:
        #flipped = self.flip_endian(number)
        self._set_struct_index(5, number)

    @property
    def minor(self) -> int:
        _, _, _, _, _, _, minor, _ = self._beacon_data
        return minor

    @minor.setter
    def minor(self, number: int) -> None:
        self._set_struct_index(6, number)

    @property
    def beacon_tx_power(self) -> int:
        _, _, _, _, _, _, _, tx_power = self._beacon_data
        return tx_power

    @beacon_tx_power.setter
    def beacon_tx_power(self, power: int) -> None:
        self._set_struct_index(7, power)

    def _set_struct_index(self, index: int, value: int) -> int:
        current_beacon_data = list(self._beacon_data)
        flipped = self.flip_endian(value, index)
        current_beacon_data[index] = flipped
        self._beacon_data = current_beacon_data

    def _init_struct(self) -> None:
        self._beacon_data = (_APPLE_COMPANY_ID_FLIPPED, _IBEACON_TYPE, _IBEACON_LENGTH, 0, 0, 0, 0, 0)

    def flip_endian(self, number: int, index: int):
        index_format = self._data_format[index+1]
        temp_bytes = struct.pack("<" + index_format, number)
        return struct.unpack("<" + index_format, temp_bytes)[0]
