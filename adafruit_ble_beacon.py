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

**Software and Dependencies:**

* Adafruit CircuitPython firmware for the supported boards:
  https://circuitpython.org/downloads

"""

import struct
from micropython import const
import _bleio
from adafruit_ble.advertising import Advertisement, AdvertisingDataField

try:
    from typing import Optional, Union, Type, Tuple, Sequence
except ImportError:
    pass

__version__ = "0.0.0+auto.0"
__repo__ = "https://github.com/tekktrik/Adafruit_CircuitPython_BLE_Beacon.git"


_MANUFACTURING_DATA_ADT = const(0xFF)

_APPLE_COMPANY_ID = const(0x004C)
_IBEACON_TYPE = const(0x02)
_IBEACON_LENGTH = const(0x15)


class MultiStruct(AdvertisingDataField):
    """`struct` encoded data in an Advertisement."""

    def __init__(self, struct_format: str, *, advertising_data_type: int) -> None:
        self._format = struct_format
        self._adt = advertising_data_type

    def __get__(
        self, obj: Optional["Advertisement"], cls: Type["Advertisement"]
    ) -> Optional[Union[Tuple, "MultiStruct"]]:
        if obj is None:
            return self
        if self._adt not in obj.data_dict:
            return None
        return struct.unpack(self._format, obj.data_dict[self._adt])

    def __set__(self, obj: "Advertisement", value: Sequence) -> None:
        obj.data_dict[self._adt] = struct.pack(self._format, *value)


class _BeaconAdvertisement(Advertisement):
    """Advertisement for location beacons like iBeacon"""

    path_loss_const: float = 3
    """The path loss constant, typically between 2-4"""

    @property
    def uuid(self) -> bytes:
        """The UUID of the beacon"""
        raise NotImplementedError("Must be implemented in beacon subclass")

    @uuid.setter
    def uuid(self, uuid: bytes) -> None:
        raise NotImplementedError("Must be implemented in beacon subclass")

    @property
    def distance(self) -> float:
        """The approximate distance to the beacon, in meters"""
        return 10 ** ((self.beacon_tx_power - self.rssi) / (10 * self.path_loss_const))

    @property
    def beacon_tx_power(self) -> int:
        """The beacon TX power"""
        raise NotImplementedError("Must be implemented in beacon subclass")

    @beacon_tx_power.setter
    def beacon_tx_power(self, power: int) -> None:
        raise NotImplementedError("Must be implemented in beacon subclass")


# pylint: disable=invalid-name
class iBeaconAdvertisement(_BeaconAdvertisement):
    """An iBeacon advertisement"""

    match_prefixes = (
        struct.pack(
            "<BHBB",
            _MANUFACTURING_DATA_ADT,
            _APPLE_COMPANY_ID,
            _IBEACON_TYPE,
            _IBEACON_LENGTH,
        ),
    )

    _data_format = ">HBBQQHHb"
    _beacon_data = MultiStruct(_data_format, advertising_data_type=0xFF)

    _uuid_msb_index = 3
    _uuid_lsb_index = 4
    _major_index = 5
    _minor_index = 6
    _beacon_tx_power_index = 7

    def __init__(self, *, entry: Optional[_bleio.ScanEntry] = None) -> None:
        super().__init__(entry=entry)
        if not entry:
            self._init_struct()

    @property
    def uuid(self) -> bytes:
        """The UUID of the beacon"""
        uuid_msb = self._get_struct_index(self._uuid_msb_index)
        uuid_lsb = self._get_struct_index(self._uuid_lsb_index)
        return struct.pack(">QQ", uuid_msb, uuid_lsb)

    @uuid.setter
    def uuid(self, uuid: bytes) -> None:
        uuid_msb, uuid_lsb = struct.unpack(">QQ", uuid)
        self._set_struct_index(3, uuid_msb)
        self._set_struct_index(4, uuid_lsb)

    @property
    def major(self) -> int:
        """The major store number for the beacon"""
        return self._get_struct_index(self._major_index)

    @major.setter
    def major(self, number: int) -> None:
        self._set_struct_index(5, number)

    @property
    def minor(self) -> int:
        """The minor store number for the beacon"""
        return self._get_struct_index(self._minor_index)

    @minor.setter
    def minor(self, number: int) -> None:
        self._set_struct_index(6, number)

    @property
    def beacon_tx_power(self) -> int:
        """The beacon TX power"""
        return self._get_struct_index(self._beacon_tx_power_index)

    @beacon_tx_power.setter
    def beacon_tx_power(self, power: int) -> None:
        self._set_struct_index(7, power)

    def _set_struct_index(self, index: int, value: int) -> int:
        current_beacon_data = list(self._beacon_data)
        current_beacon_data[index] = value
        self._beacon_data = current_beacon_data

    def _get_struct_index(self, index: int) -> int:
        temp_tuple = self._beacon_data
        return temp_tuple[index]

    def _init_struct(self) -> None:
        apple_id_flipped = struct.unpack(">H", struct.pack("<H", _APPLE_COMPANY_ID))
        self._beacon_data = (
            apple_id_flipped,
            _IBEACON_TYPE,
            _IBEACON_LENGTH,
            0,
            0,
            0,
            0,
            0,
        )
