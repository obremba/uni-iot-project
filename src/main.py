from Config import Config
import asyncio
from Device import Factory, DeviceProp
from asyncua import Client


async def main():
    config = Config()

    subscriptions = []
    agents = []
    while True:
        async with Client(config.factory_url) as client:
            factory = await Factory(client).initialize()
            for device in factory.devices:
                print(await device.read_value(DeviceProp.ProductionStatus))

            await asyncio.sleep(5)

if __name__ == '__main__':
    try:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        pass
