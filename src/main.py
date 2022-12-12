from Config import Config
import asyncio
from Agent import Agent
from asyncua import Client
from asyncua.common.subscription import Subscription
from asyncua.ua.uaerrors import BadLicenseExpired
from Device import Factory
from sys import exit


async def main():
    config = Config()
    subscriptions = []
    agents = []

    while True:
        try:
            print("Łączenie z serwerem OPC UA")
            async with Client(config.factory_url) as client:
                print("Połączono!")
                factory = await Factory(client).initialize()
                print("Pobieranie urządzeń...")
                for device in factory.devices:
                    if not config.has_agent_connection_string(await device.name):
                        config.set_agent_connection_string(
                            await device.name,
                            input(f"Podaj connection string dla urządzenia {await device.name}:")
                        )
                    connection_string = config.get_agent_connection_string(await device.name)
                    print(f"Tworzenie instancji agenta dla urządzenia: {await device.name}...")
                    agent = Agent(device, connection_string)
                    print("Instacja stworzona!")

                    subscription: Subscription = await client.create_subscription(200, agent)
                    await subscription.subscribe_data_change(await agent.observed_properties)

                    subscriptions.append(subscription)
                    agents.append(agent)

                while True:
                    await asyncio.gather(*[task for agent in agents for task in agent.tasks_list])
                    await asyncio.sleep(1)

        except KeyboardInterrupt:
            for subscription in subscriptions:
                await subscription.delete()
            for agent in agents:
                agent.shutdown()

        except asyncio.exceptions.TimeoutError:
            print("Nie można połączyć się z serwerem OPC UA")
        except ConnectionError:
            print("Rozłączono z serwerem OPC UA")
        except Exception as e:
            if isinstance(e, BadLicenseExpired):
                print("Licencja wygasła!")
            else:
                print(e)
            exit(1)

if __name__ == '__main__':
    try:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        pass
