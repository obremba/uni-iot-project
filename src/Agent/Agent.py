from azure.iot.device import IoTHubDeviceClient, Message, MethodRequest, MethodResponse
from asyncua import ua
from Device import Device, DeviceProp, DeviceMethod, DeviceError
import json
from datetime import datetime
from enum import Enum
import asyncio


class MessageType(Enum):
    TELEMETRY = 'telemetry'
    EVENT = 'event'


class Agent:
    def __init__(self, device: Device, connection_string: str):
        self.device = device
        self.errors = []
        self.tasks = []
        self.message_count = 0

        self.client = IoTHubDeviceClient.create_from_connection_string(connection_string)
        self.client.connect()
        self.client.on_method_request_received = self.method_handler
        self.client.on_twin_desired_properties_patch_received = self.twin_update_handler

    async def send_telemetry(self):
        data = {
            "ProductionStatus": await self.device.read_value(DeviceProp.ProductionStatus),
            "WorkorderId": await self.device.read_value(DeviceProp.WorkorderId),
            "GoodCount": await self.device.read_value(DeviceProp.GoodCount),
            "BadCount": await self.device.read_value(DeviceProp.BadCount),
            "Temperature": await self.device.read_value(DeviceProp.Temperature),
        }

        print(data)
        await self.send_message(data, MessageType.TELEMETRY)

    async def send_message(self, data, message_type: MessageType):
        msg = Message(
            data=json.dumps(data),
            content_type='application/json',
            content_encoding='utf-8'
        )
        msg.custom_properties["message_type"] = message_type.value
        self.message_count += 1
        self.client.send_message(msg)

    @property
    def tasks_list(self):
        tasks = [asyncio.create_task(task) for task in self.tasks]
        self.tasks.clear()
        tasks.append(asyncio.create_task(self.send_telemetry()))
        return tasks

    @property
    async def observed_properties(self):
        return [
            await self.device.get_node(DeviceProp.ProductionRate),
            await self.device.get_node(DeviceProp.DeviceError)
        ]

    def method_handler(self, method: MethodRequest):
        if method.name == "emergency_stop":
            self.tasks.append(self.device.call_method(DeviceMethod.EmergencyStop))

        elif method.name == "reset_error_status":
            self.tasks.append(self.device.call_method(DeviceMethod.ResetErrorStatus))

        elif method.name == "maintenance_done":
            self.client.patch_twin_reported_properties({"last_maintenance_date": datetime.now().isoformat()})

        self.client.send_method_response(MethodResponse(method.request_id, 200))

    def twin_update_handler(self, data):
        if "production_rate" in data:
            self.tasks.append(self.device.write_value(
                DeviceProp.ProductionRate, ua.Variant(data["production_rate"], ua.VariantType.Int32)
            ))

    # asyncua subcription callback
    async def datachange_notification(self, node, val, _):
        name = await node.read_browse_name()
        print(f"Wykryto zmianę {name.Name} dla urządzenia {await self.device.name}: {val}")
        if name.Name == DeviceProp.DeviceError.value:
            errors = DeviceError.list(val)
            for error in errors:
                if error not in self.errors:
                    self.client.patch_twin_reported_properties({"last_error_date": datetime.now().isoformat()})
                    await self.send_message({"device_error": error.value}, MessageType.EVENT)

            self.errors = errors
            self.client.patch_twin_reported_properties({"device_error": sum(error.value for error in self.errors)})
        elif name.Name == DeviceProp.ProductionRate.value:
            self.client.patch_twin_reported_properties({"production_rate": val})

    def shutdown(self):
        self.client.shutdown()
