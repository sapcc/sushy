#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

# This is referred from Redfish standard schema.
# http://redfish.dmtf.org/schemas/v1/Drive.v1_4_0.json

import logging

from sushy import exceptions
from sushy.resources import base
from sushy.resources import common
from sushy.resources import constants as res_cons
from sushy.resources import mappings as res_maps
from sushy.resources.system.storage import volume
from sushy.taskmonitor import TaskMonitor
from sushy import utils

LOG = logging.getLogger(__name__)

class ActionsField(base.CompositeField):
    secure_erase = common.ActionField('#Drive.SecureErase')


class Drive(base.ResourceBase):
    """This class represents a disk drive or other physical storage medium."""

    block_size_bytes = base.Field('BlockSizeBytes', adapter=utils.int_or_none)
    """The size of the smallest addressable unit of this drive in bytes"""

    capacity_bytes = base.Field('CapacityBytes', adapter=utils.int_or_none)
    """The size in bytes of this Drive"""

    identifiers = common.IdentifiersListField('Identifiers', default=[])
    """The Durable names for the drive"""

    identity = base.Field('Id', required=True)
    """The Drive identity string"""

    indicator_led = base.MappedField('IndicatorLED',
                                     res_maps.INDICATOR_LED_VALUE_MAP)
    """Whether the indicator LED is lit or off"""

    manufacturer = base.Field('Manufacturer')
    """This is the manufacturer of this drive"""

    media_type = base.Field('MediaType')
    """The type of media contained in this drive"""

    model = base.Field('Model')
    """This is the model number for the drive"""

    name = base.Field('Name')
    """The name of the resource"""

    part_number = base.Field('PartNumber')
    """The part number for this drive"""

    protocol = base.MappedField('Protocol', res_maps.PROTOCOL_TYPE_VALUE_MAP)
    """Protocol this drive is using to communicate to the storage controller"""

    serial_number = base.Field('SerialNumber')
    """The serial number for this drive"""

    status = common.StatusField('Status')
    """This type describes the status and health of the drive"""

    _actions = ActionsField('Actions')

    @property
    @utils.cache_it
    def volumes(self):
        """A list of volumes that this drive is part of.

        Volumes that this drive either wholly or only partially contains.

        :raises: MissingAttributeError if '@odata.id' field is missing.
        :returns: A list of `Volume` instances
        """
        paths = utils.get_sub_resource_path_by(
            self, ["Links", "Volumes"], is_collection=True)

        return [volume.Volume(self._conn, path,
                              redfish_version=self.redfish_version,
                              registries=self.registries)
                for path in paths]

    def set_indicator_led(self, state):
        """Set IndicatorLED to the given state.

        :param state: Desired LED state, lit (INDICATOR_LED_LIT), blinking
            (INDICATOR_LED_BLINKING), off (INDICATOR_LED_OFF)
        :raises: InvalidParameterValueError, if any information passed is
            invalid.
        """
        if state not in res_maps.INDICATOR_LED_VALUE_MAP_REV:
            raise exceptions.InvalidParameterValueError(
                parameter='state', value=state,
                valid_values=list(res_maps.INDICATOR_LED_VALUE_MAP_REV))

        data = {
            'IndicatorLED': res_maps.INDICATOR_LED_VALUE_MAP_REV[state]
        }

        self._conn.patch(self.path, data=data)
        self.invalidate()

    def _get_secure_erase_action_element(self):
        secure_erase = self._actions.secure_erase
        if not secure_erase:
            raise exceptions.MissingActionError(action='#Disk.SecureErase',
                                                resource=self._path)
        return secure_erase

    def _secure_erase(self, apply_time=None):
        payload = {}
        oat_prop = '@Redfish.OperationApplyTime'
        if apply_time:
            payload[oat_prop] = res_maps.APPLY_TIME_VALUE_MAP_REV[apply_time]
        target_uri = self._get_secure_erase_action_element().target_uri
        r = self._conn.post(target_uri, data=payload, blocking=False)
        return r, target_uri

    def secure_erase(self, apply_time=None):
        """Securely erase the drive.

        :param apply_time: When to update the attributes. Optional.
            APPLY_TIME_IMMEDIATE - Immediate
            APPLY_TIME_ON_RESET - On reset
        :raises: InvalidParameterValueError, if the target value is not
            allowed.
        :raises: ConnectionError
        :raises: HTTPError
        :returns: TaskMonitor
        """
        r, target_uri = self._secure_erase(apply_time)
        return TaskMonitor.from_response(
            self._conn, r, target_uri, self.redfish_version,
            self.registries)
