"""
Generates solidity interface definitions from ABIs.
"""
import os
from re import I
import textwrap
from typing import Any, Dict, List

from ..version import MOONWORM_VERSION

INTERFACE_TEMPLATE_FILENAME = "SolidityInterface.sol.template"
INTERFACE_TEMPLATE_FILEPATH = os.path.realpath(
    os.path.join(os.path.dirname(__file__), INTERFACE_TEMPLATE_FILENAME)
)


def generate_interface(
    name: str, abi: List[Dict[str, Any]], pragma_version: str = "^0.8.9"
) -> str:
    interface_body_components: List[str] = []
    for item in abi:
        if (
            item.get("type") == "event"
            and item.get("name") is not None
            and item.get("inputs") is not None
        ):
            inputs: List[str] = []
            for arg in item["inputs"]:
                middle = " "
                if arg.get("indexed", False):
                    middle = " indexed "
                # TODO(zomglings): Should we be using "type" or "internalType"? Check against Dark Forest ABI.
                input_component = f"{arg['type']}{middle}{arg['name']}"
                inputs.append(input_component)

            body_component = f"event {item['name']}({', '.join(inputs)});"
            interface_body_components.append(body_component)
        elif (
            item.get("type") == "function"
            and item.get("name") is not None
            and item.get("inputs") is not None
            and item.get("outputs") is not None
        ):
            mutability = ""
            if item.get("stateMutability") == "view":
                mutability = "view "
            elif item.get("stateMutability") == "payable":
                mutability = "payable "

            inputs: List[str] = []
            for arg in item["inputs"]:
                # TODO(zomglings): Should we be using "type" or "internalType"? Check against Dark Forest ABI.
                input_component = f"{arg['type']}{arg['name']}"
                inputs.append(input_component)

            outputs: List[str] = []
            for arg in item["outputs"]:
                name = ""
                if arg.get("name"):
                    name = f" {arg['name']}"
                # TODO(zomglings): Should we be using "type" or "internalType"? Check against Dark Forest ABI.
                output_component = f"{arg['type']}{name}"
                outputs.append(output_component)

            body_component = f"function {item['name']}({', '.join(inputs)}) external {mutability}returns ({', '.join(outputs)});"
            interface_body_components.append(body_component)

    interface_body = textwrap.indent("\n\n".join(interface_body_components), "\t")

    with open(INTERFACE_TEMPLATE_FILEPATH, "r") as ifp:
        interface_template = ifp.read().strip()

    return interface_template.format(
        moonworm_version=MOONWORM_VERSION,
        pragma_version=pragma_version,
        interface_name=name,
        interface_body=interface_body,
    )


if __name__ == "__main__":
    import json

    with open(
        "/home/neeraj/dev/bugout-dev/moonworm/moonworm/fixture/abis/OwnableERC20.json",
        "r",
    ) as ifp:
        abi = json.load(ifp)

    interface = generate_interface("ERC20", abi)
    print(interface)
