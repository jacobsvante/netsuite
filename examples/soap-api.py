import argparse
import asyncio

from netsuite import Config
from netsuite.constants import DEFAULT_INI_PATH, DEFAULT_INI_SECTION
from netsuite.soap_api.client import NetSuiteSoapApi

parser = argparse.ArgumentParser()
parser.add_argument("-p", "--config-path", default=DEFAULT_INI_PATH, dest="path")
parser.add_argument(
    "-c", "--config-section", default=DEFAULT_INI_SECTION, dest="section"
)


async def main():
    args = parser.parse_args()

    config = Config.from_ini(**vars(args))
    api = NetSuiteSoapApi(config)

    resp1 = await api.getList("customer", internalIds=[1])
    print(resp1)

    # Re-use same connection
    async with api:
        resp2 = await api.getList("salesOrder", internalIds=[1])
        resp3 = await api.getList("salesOrder", internalIds=[2])

    print(resp2)
    print(resp3)


if __name__ == "__main__":
    asyncio.run(main())
