from enum import Enum
from asyncua import Client
from asyncua.ua import NodeClass
from asyncua.common import Node


class DeviceProp(Enum):
    ProductionStatus = "ProductionStatus"
    WorkorderId = "WorkorderId"
    ProductionRate = "ProductionRate"
    GoodCount = "GoodCount"
    BadCount = "BadCount"
    Temperature = "Temperature"
    DeviceError = "DeviceError"


class DeviceMethod(Enum):
    EmergencyStop = "EmergencyStop"
    ResetErrorStatus = "ResetErrorStatus"


class DeviceError(Enum):
    EmergencyStop = 1
    PowerFailure = 2
    SensorFailure = 4
    Unknown = 8

    @classmethod
    def list(cls, error_code: int):
        return [e for e in cls if e.value & error_code]


class Device:
    def __init__(self, client: Client, node: Node):
        self.client = client
        self.node = node

    @property
    async def name(self):
        return (await self.node.read_browse_name()).Name

    @property
    async def properties(self):
        variables = {}
        device = self.client.get_node(self.node)
        children = await device.get_children()

        for child in children:
            node = self.client.get_node(child)
            node_name = await node.read_browse_name()
            variables[node_name.Name] = child

        return variables

    async def get_node(self, prop: DeviceProp):
        return (await self.properties)[prop.value]

    async def read_value(self, prop: DeviceProp):
        return await (await self.get_node(prop)).read_value()

    async def write_value(self, prop: DeviceProp, value):
        property_node = (await self.properties)[prop.value]
        await self.client.get_node(property_node).write_value(value)

    async def call_method(self, prop: DeviceMethod):
        node = self.client.get_node(self.node)
        await node.call_method(prop.value)


class Factory:
    def __init__(self, client: Client):
        self.client = client
        self.devices = []

    async def initialize(self):
        server = self.client.get_server_node()
        for child in await self.client.get_objects_node().get_children():
            if child != server and await child.read_node_class() == NodeClass.Object:
                self.devices.append(Device(self.client, child))
        return self
