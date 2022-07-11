import json
import os
import unittest

import solcx

from ...generators import solidity_interface

SCRIPT_DIR = os.path.realpath(os.path.dirname(__file__))
FIXTURES_ABIS_DIR = os.path.join(SCRIPT_DIR, "..", "..", "fixture", "abis")


class TestGeneration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        solcx.install_solc("0.8.10", show_progress=True)

    def test_generate_ownable_erc20_interface(self):
        OWNABLE_ERC20_ABI_JSON = os.path.join(FIXTURES_ABIS_DIR, "OwnableERC20.json")
        with open(OWNABLE_ERC20_ABI_JSON, "r") as ifp:
            abi = json.load(ifp)

        expected_abi = [item for item in abi if item["type"] in ("function", "event")]

        interface = solidity_interface.generate_interface("OwnableERC20", abi)

        compiler_result = solcx.compile_source(
            interface, output_values=["abi"], solc_version="0.8.10"
        )

        self.assertEqual(len(compiler_result), 1)

        for _, item in compiler_result.items():
            compiled_abi = item["abi"]
            self.assertEqual(len(compiled_abi), len(expected_abi))

            for expected, actual in zip(expected_abi, compiled_abi):
                self.assertEqual(expected["type"], actual["type"])
                self.assertEqual(expected["name"], actual["name"])
                self.assertEqual(expected["inputs"], actual["inputs"])
                self.assertEqual(expected.get("outputs", []), actual.get("outputs", []))

    def test_generate_ownable_erc721_interface(self):
        OWNABLE_ERC721_ABI_JSON = os.path.join(FIXTURES_ABIS_DIR, "OwnableERC721.json")
        with open(OWNABLE_ERC721_ABI_JSON, "r") as ifp:
            abi = json.load(ifp)

        expected_abi = [item for item in abi if item["type"] in ("function", "event")]

        interface = solidity_interface.generate_interface("OwnableERC721", abi)

        compiler_result = solcx.compile_source(
            interface, output_values=["abi"], solc_version="0.8.10"
        )

        self.assertEqual(len(compiler_result), 1)

        for _, item in compiler_result.items():
            compiled_abi = item["abi"]
            self.assertEqual(len(compiled_abi), len(expected_abi))

            for expected, actual in zip(expected_abi, compiled_abi):
                self.assertEqual(expected["type"], actual["type"])
                self.assertEqual(expected["name"], actual["name"])
                self.assertEqual(expected["inputs"], actual["inputs"])
                self.assertEqual(expected.get("outputs", []), actual.get("outputs", []))

    def test_generate_ownable_erc1155_interface(self):
        OWNABLE_ERC1155_ABI_JSON = os.path.join(
            FIXTURES_ABIS_DIR, "OwnableERC1155.json"
        )
        with open(OWNABLE_ERC1155_ABI_JSON, "r") as ifp:
            abi = json.load(ifp)

        expected_abi = [item for item in abi if item["type"] in ("function", "event")]

        interface = solidity_interface.generate_interface("OwnableERC1155", abi)

        compiler_result = solcx.compile_source(
            interface, output_values=["abi"], solc_version="0.8.10"
        )

        self.assertEqual(len(compiler_result), 1)

        for _, item in compiler_result.items():
            compiled_abi = item["abi"]
            self.assertEqual(len(compiled_abi), len(expected_abi))

            for expected, actual in zip(expected_abi, compiled_abi):
                self.assertEqual(expected["type"], actual["type"])
                self.assertEqual(expected["name"], actual["name"])
                self.assertEqual(expected["inputs"], actual["inputs"])
                self.assertEqual(expected.get("outputs", []), actual.get("outputs", []))

    def test_generate_diamond_cut_facet_interface(self):
        # TODO(zomglings): We need to:
        # 1. Update interface generation to use internalType instead of type.
        # 2. Generate structs defined as part of compound types in the ABI.
        #
        # Relevant ABI component:
        # {
        #     "anonymous": false,
        #     "inputs": [
        #         {
        #             "components": [
        #                 {
        #                     "internalType": "address",
        #                     "name": "facetAddress",
        #                     "type": "address"
        #                 },
        #                 {
        #                     "internalType": "enum IDiamondCut.FacetCutAction",
        #                     "name": "action",
        #                     "type": "uint8"
        #                 },
        #                 {
        #                     "internalType": "bytes4[]",
        #                     "name": "functionSelectors",
        #                     "type": "bytes4[]"
        #                 }
        #             ],
        #             "indexed": false,
        #             "internalType": "struct IDiamondCut.FacetCut[]",
        #             "name": "_diamondCut",
        #             "type": "tuple[]"
        #         },
        #         {
        #             "indexed": false,
        #             "internalType": "address",
        #             "name": "_init",
        #             "type": "address"
        #         },
        #         {
        #             "indexed": false,
        #             "internalType": "bytes",
        #             "name": "_calldata",
        #             "type": "bytes"
        #         }
        #     ],
        #     "name": "DiamondCut",
        #     "type": "event"
        # },

        raise unittest.SkipTest

        diamond_cut_facet_ABI_JSON = os.path.join(
            FIXTURES_ABIS_DIR, "DiamondCutFacet.json"
        )
        with open(diamond_cut_facet_ABI_JSON, "r") as ifp:
            abi = json.load(ifp)

        expected_abi = [item for item in abi if item["type"] in ("function", "event")]

        interface = solidity_interface.generate_interface("DiamondCutFacet", abi)

        compiler_result = solcx.compile_source(
            interface, output_values=["abi"], solc_version="0.8.10"
        )

        self.assertEqual(len(compiler_result), 1)

        for _, item in compiler_result.items():
            compiled_abi = item["abi"]
            self.assertEqual(len(compiled_abi), len(expected_abi))

            for expected, actual in zip(expected_abi, compiled_abi):
                self.assertEqual(expected["type"], actual["type"])
                self.assertEqual(expected["name"], actual["name"])
                self.assertEqual(expected["inputs"], actual["inputs"])
                self.assertEqual(expected.get("outputs", []), actual.get("outputs", []))


if __name__ == "__main__":
    unittest.main()
