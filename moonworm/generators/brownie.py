"""
Generates [`brownie`](https://github.com/eth-brownie/brownie)-compatible bindings to Ethereum smart contracts from their ABIs.

The entrypoint to code generation is [`generate_brownie_interface`][moonworm.generators.brownie.generate_brownie_interface].
"""

import copy
import logging
import os
from typing import Any, Dict, List, Optional

import libcst as cst
from libcst._nodes.statement import SimpleStatementLine

from ..version import MOONWORM_VERSION
from .basic import format_code, function_spec, get_constructor, make_annotation

BROWNIE_INTERFACE_TEMPLATE_PATH = os.path.join(
    os.path.dirname(__file__), "brownie_contract.py.template"
)
BROWNIE_INTERFACE_PROD_TEMPLATE_PATH = os.path.join(
    os.path.dirname(__file__), "brownie_contract_prod.py.template"
)
try:
    with open(BROWNIE_INTERFACE_TEMPLATE_PATH, "r") as ifp:
        BROWNIE_INTERFACE_TEMPLATE = ifp.read()
    with open(BROWNIE_INTERFACE_PROD_TEMPLATE_PATH, "r") as ifp:
        BROWNIE_INTERFACE_PROD_TEMPLATE = ifp.read()
except Exception as e:
    logging.warn(
        f"WARNING: Could not load cli template from ({BROWNIE_INTERFACE_TEMPLATE_PATH})/({BROWNIE_INTERFACE_PROD_TEMPLATE_PATH}):"
    )
    logging.warn(e)


def generate_brownie_contract_class(
    abi: List[Dict[str, Any]],
    contract_name: str,
) -> cst.ClassDef:
    class_name = contract_name
    class_constructor = cst.FunctionDef(
        name=cst.Name("__init__"),
        body=cst.IndentedBlock(
            body=[
                cst.parse_statement(f'self.contract_name = "{contract_name}"'),
                cst.parse_statement("self.address = contract_address"),
                cst.parse_statement("self.contract = None"),
                cst.parse_statement(f'self.abi = get_abi_json("{contract_name}")'),
                cst.If(
                    test=cst.Comparison(
                        left=cst.Attribute(
                            attr=cst.Name(value="address"),
                            value=cst.Name(value="self"),
                        ),
                        comparisons=[
                            cst.ComparisonTarget(
                                operator=cst.IsNot(), comparator=cst.Name(value="None")
                            )
                        ],
                    ),
                    body=cst.parse_statement(
                        "self.contract: Optional[Contract] = Contract.from_abi(self.contract_name, self.address, self.abi)"
                    ),
                ),
            ]
        ),
        params=cst.Parameters(
            params=[
                cst.Param(name=cst.Name("self")),
                cst.Param(
                    name=cst.Name("contract_address"),
                    annotation=make_annotation(["ChecksumAddress"], optional=True),
                ),
            ]
        ),
    )

    contract_constructor = get_constructor(abi)
    contract_constructor["name"] = "constructor"

    class_functions = (
        [class_constructor]
        + [
            generate_brownie_constructor_function(contract_constructor),
            generate_assert_contract_is_instantiated(),
            generate_verify_contract(),
        ]
        + [
            generate_brownie_contract_function(function)
            for function in abi
            if function["type"] == "function"
        ]
    )
    return cst.ClassDef(
        name=cst.Name(class_name), body=cst.IndentedBlock(body=class_functions)
    )


def generate_brownie_constructor_function(
    func_object: Dict[str, Any]
) -> cst.FunctionDef:
    spec = function_spec(func_object)
    func_params = []
    func_params.append(cst.Param(name=cst.Name("self")))
    param_names = []
    for param in spec["inputs"]:
        param_type = make_annotation([param["type"]])
        param_names.append(param["method"])
        func_params.append(
            cst.Param(
                name=cst.Name(value=param["method"]),
                annotation=param_type,
            )
        )
    func_params.append(cst.Param(name=cst.Name("transaction_config")))

    func_name = "deploy"
    param_names.append("transaction_config")

    func_body = cst.IndentedBlock(
        body=[
            cst.parse_statement(
                f"contract_class = contract_from_build(self.contract_name)"
            ),
            cst.parse_statement(
                f"deployed_contract = contract_class.deploy({','.join(param_names)})"
            ),
            cst.parse_statement("self.address = deployed_contract.address"),
            cst.parse_statement("self.contract = deployed_contract"),
            cst.parse_statement("return deployed_contract.tx"),
        ]
    )

    return cst.FunctionDef(
        name=cst.Name(func_name),
        params=cst.Parameters(params=func_params),
        body=func_body,
    )


def generate_verify_contract() -> cst.FunctionDef:
    func_name = "verify_contract"
    func_params = [cst.Param(name=cst.Name("self"))]
    func_body = cst.IndentedBlock(
        body=[
            cst.parse_statement("self.assert_contract_is_instantiated()"),
            cst.parse_statement(
                f"contract_class = contract_from_build(self.contract_name)"
            ),
            cst.parse_statement("contract_class.publish_source(self.contract)"),
        ]
    )

    return cst.FunctionDef(
        name=cst.Name(func_name), params=cst.Parameters(func_params), body=func_body
    )


def generate_assert_contract_is_instantiated() -> cst.FunctionDef:
    function_body = cst.IndentedBlock(
        body=[
            cst.If(
                test=cst.Comparison(
                    left=cst.Attribute(
                        attr=cst.Name(value="contract"), value=cst.Name(value="self")
                    ),
                    comparisons=[
                        cst.ComparisonTarget(
                            operator=cst.Is(), comparator=cst.Name(value="None")
                        )
                    ],
                ),
                body=cst.parse_statement(
                    'raise Exception("contract has not been instantiated")'
                ),
            ),
        ],
    )
    function_def = cst.FunctionDef(
        name=cst.Name(value="assert_contract_is_instantiated"),
        params=cst.Parameters(
            params=[cst.Param(name=cst.Name(value="self"))],
        ),
        body=function_body,
        returns=cst.Annotation(annotation=cst.Name(value="None")),
    )
    return function_def


def generate_brownie_contract_function(func_object: Dict[str, Any]) -> cst.FunctionDef:
    spec = function_spec(func_object)
    func_params = []
    func_params.append(cst.Param(name=cst.Name("self")))

    param_names = []
    for param in spec["inputs"]:
        param_type = make_annotation([param["type"]])
        param_name = param["method"]
        param_names.append(param_name)
        func_params.append(
            cst.Param(
                name=cst.Name(value=param_name),
                annotation=param_type,
            )
        )

    func_raw_name = spec["abi"]
    func_python_name = spec["method"]
    func_name = cst.Name(value=func_python_name)
    if spec["transact"]:
        func_params.append(cst.Param(name=cst.Name(value="transaction_config")))
        param_names.append("transaction_config")
        proxy_call_code = (
            f"return self.contract.{func_raw_name}({','.join(param_names)})"
        )
    else:

        func_params.append(
            cst.Param(
                name=cst.Name(value="block_number"),
                annotation=make_annotation(["str", "int"], optional=True),
                default=cst.SimpleString(value='"latest"'),
            )
        )
        param_names.append("block_identifier=block_number")
        proxy_call_code = (
            f"return self.contract.{func_raw_name}.call({','.join(param_names)})"
        )

    func_body = cst.IndentedBlock(
        body=[
            cst.parse_statement("self.assert_contract_is_instantiated()"),
            cst.parse_statement(proxy_call_code),
        ]
    )
    func_returns = cst.Annotation(annotation=cst.Name(value="Any"))

    return cst.FunctionDef(
        name=func_name,
        params=cst.Parameters(params=func_params),
        body=func_body,
        returns=func_returns,
    )


def generate_get_transaction_config() -> cst.FunctionDef:
    function_body = cst.IndentedBlock(
        body=[
            cst.parse_statement(
                "signer = network.accounts.load(args.sender, args.password)"
            ),
            cst.parse_statement(
                'transaction_config: Dict[str, Any] = {"from": signer}'
            ),
            cst.If(
                test=cst.Comparison(
                    left=cst.Attribute(
                        attr=cst.Name(value="gas_price"), value=cst.Name(value="args")
                    ),
                    comparisons=[
                        cst.ComparisonTarget(
                            operator=cst.IsNot(), comparator=cst.Name(value="None")
                        )
                    ],
                ),
                body=cst.parse_statement(
                    'transaction_config["gas_price"] = args.gas_price'
                ),
            ),
            cst.If(
                test=cst.Comparison(
                    left=cst.Attribute(
                        attr=cst.Name(value="max_fee_per_gas"),
                        value=cst.Name(value="args"),
                    ),
                    comparisons=[
                        cst.ComparisonTarget(
                            operator=cst.IsNot(), comparator=cst.Name(value="None")
                        )
                    ],
                ),
                body=cst.parse_statement(
                    'transaction_config["max_fee"] = args.max_fee_per_gas'
                ),
            ),
            cst.If(
                test=cst.Comparison(
                    left=cst.Attribute(
                        attr=cst.Name(value="max_priority_fee_per_gas"),
                        value=cst.Name(value="args"),
                    ),
                    comparisons=[
                        cst.ComparisonTarget(
                            operator=cst.IsNot(), comparator=cst.Name(value="None")
                        )
                    ],
                ),
                body=cst.parse_statement(
                    'transaction_config["priority_fee"] = args.max_priority_fee_per_gas'
                ),
            ),
            cst.If(
                test=cst.Comparison(
                    left=cst.Attribute(
                        attr=cst.Name(value="confirmations"),
                        value=cst.Name(value="args"),
                    ),
                    comparisons=[
                        cst.ComparisonTarget(
                            operator=cst.IsNot(), comparator=cst.Name(value="None")
                        )
                    ],
                ),
                body=cst.parse_statement(
                    'transaction_config["required_confs"] = args.confirmations'
                ),
            ),
            cst.If(
                test=cst.Comparison(
                    left=cst.Attribute(
                        attr=cst.Name(value="nonce"),
                        value=cst.Name(value="args"),
                    ),
                    comparisons=[
                        cst.ComparisonTarget(
                            operator=cst.IsNot(), comparator=cst.Name(value="None")
                        )
                    ],
                ),
                body=cst.parse_statement('transaction_config["nonce"] = args.nonce'),
            ),
            cst.parse_statement("return transaction_config"),
        ],
    )
    function_def = cst.FunctionDef(
        name=cst.Name(value="get_transaction_config"),
        params=cst.Parameters(
            params=[
                cst.Param(
                    name=cst.Name(value="args"),
                    annotation=cst.Annotation(
                        annotation=cst.Attribute(
                            attr=cst.Name(value="Namespace"),
                            value=cst.Name(value="argparse"),
                        )
                    ),
                )
            ],
        ),
        body=function_body,
        returns=cst.Annotation(
            annotation=cst.Subscript(
                value=cst.Name(value="Dict"),
                slice=[
                    cst.SubscriptElement(slice=cst.Index(value=cst.Name(value="str"))),
                    cst.SubscriptElement(slice=cst.Index(value=cst.Name(value="Any"))),
                ],
            )
        ),
    )
    return function_def


def generate_deploy_handler(
    constructor_abi: Dict[str, Any], contract_name: str
) -> Optional[cst.FunctionDef]:
    """
    Generates a handler which deploys the given contract to the specified blockchain using the constructor
    with the given signature.
    """
    # Since we mutate the ABI before passing to function_spec (to conform to its assumptions), make
    # a copy of the constructor_abi.
    local_abi = copy.deepcopy(constructor_abi)
    local_abi["name"] = "deploy"
    spec = function_spec(local_abi)
    function_name = spec["method"]

    function_body_raw: List[cst.CSTNode] = []

    # Instantiate the contract
    function_body_raw.extend(
        [
            cst.parse_statement("network.connect(args.network)"),
            cst.parse_statement("transaction_config = get_transaction_config(args)"),
            cst.parse_statement(f"contract = {contract_name}(None)"),
        ]
    )

    # Call contract method
    call_args: List[cst.Arg] = []
    for param in spec["inputs"]:
        call_args.append(
            cst.Arg(
                keyword=cst.Name(value=param["method"]),
                value=cst.Attribute(
                    attr=cst.Name(value=param["args"]), value=cst.Name(value="args")
                ),
            )
        )

    call_args.append(
        cst.Arg(
            keyword=cst.Name(value="transaction_config"),
            value=cst.Name(value="transaction_config"),
        )
    )

    method_call = cst.Call(
        func=cst.Attribute(
            attr=cst.Name(value=spec["method"]),
            value=cst.Name(value="contract"),
        ),
        args=call_args,
    )

    method_call_result_statement = cst.SimpleStatementLine(
        body=[
            cst.Assign(
                targets=[cst.AssignTarget(target=cst.Name(value="result"))],
                value=method_call,
            )
        ]
    )
    function_body_raw.append(method_call_result_statement)

    function_body_raw.append(cst.parse_statement("print(result)"))
    verbose_print = cst.If(
        test=cst.parse_expression("args.verbose"),
        body=cst.IndentedBlock(
            body=[
                cst.parse_statement("print(result.info())"),
            ]
        ),
    )
    function_body_raw.append(verbose_print)

    function_body = cst.IndentedBlock(body=function_body_raw)

    function_def = cst.FunctionDef(
        name=cst.Name(value=f"handle_{function_name}"),
        params=cst.Parameters(
            params=[
                cst.Param(
                    name=cst.Name(value="args"),
                    annotation=cst.Annotation(
                        annotation=cst.Attribute(
                            attr=cst.Name(value="Namespace"),
                            value=cst.Name(value="argparse"),
                        )
                    ),
                )
            ],
        ),
        body=function_body,
        returns=cst.Annotation(annotation=cst.Name(value="None")),
    )
    return function_def


def generate_verify_contract_handler(contract_name: str) -> Optional[cst.FunctionDef]:
    """
    Generates a handler which deploys the given contract to the specified blockchain using the constructor
    with the given signature.
    """
    function_body_raw: List[cst.CSTNode] = []

    # Instantiate the contract
    function_body_raw.extend(
        [
            cst.parse_statement("network.connect(args.network)"),
            cst.parse_statement(f"contract = {contract_name}(args.address)"),
        ]
    )

    method_call = cst.Call(
        func=cst.Attribute(
            attr=cst.Name(value="verify_contract"),
            value=cst.Name(value="contract"),
        ),
        args=[],
    )

    method_call_result_statement = cst.SimpleStatementLine(
        body=[
            cst.Assign(
                targets=[cst.AssignTarget(target=cst.Name(value="result"))],
                value=method_call,
            )
        ]
    )
    function_body_raw.append(method_call_result_statement)

    function_body_raw.append(cst.parse_statement("print(result)"))

    function_body = cst.IndentedBlock(body=function_body_raw)

    function_def = cst.FunctionDef(
        name=cst.Name(value=f"handle_verify_contract"),
        params=cst.Parameters(
            params=[
                cst.Param(
                    name=cst.Name(value="args"),
                    annotation=cst.Annotation(
                        annotation=cst.Attribute(
                            attr=cst.Name(value="Namespace"),
                            value=cst.Name(value="argparse"),
                        )
                    ),
                )
            ],
        ),
        body=function_body,
        returns=cst.Annotation(annotation=cst.Name(value="None")),
    )
    return function_def


def generate_cli_handler(
    function_abi: Dict[str, Any], contract_name: str
) -> Optional[cst.FunctionDef]:
    """
    Generates a handler which translates parsed command line arguments to method calls on the generated
    smart contract interface.

    Returns None if it is not appropriate for the given function to have a handler (e.g. fallback or
    receive). constructor is handled separately with a deploy handler.
    """
    spec = function_spec(function_abi)
    function_name = spec["method"]

    function_body_raw: List[cst.CSTNode] = []

    # Instantiate the contract
    function_body_raw.extend(
        [
            cst.parse_statement("network.connect(args.network)"),
            cst.parse_statement(f"contract = {contract_name}(args.address)"),
        ]
    )

    # If a transaction is required, extract transaction parameters from CLI
    requires_transaction = True
    if function_abi["stateMutability"] == "view":
        requires_transaction = False

    if requires_transaction:
        function_body_raw.append(
            cst.parse_statement("transaction_config = get_transaction_config(args)")
        )

    # Call contract method
    call_args: List[cst.Arg] = []
    for param in spec["inputs"]:
        call_args.append(
            cst.Arg(
                keyword=cst.Name(value=param["method"]),
                value=cst.Attribute(
                    attr=cst.Name(value=param["args"]), value=cst.Name(value="args")
                ),
            )
        )
    if requires_transaction:
        call_args.append(
            cst.Arg(
                keyword=cst.Name(value="transaction_config"),
                value=cst.Name(value="transaction_config"),
            )
        )
    else:
        call_args.append(
            cst.Arg(
                keyword=cst.Name(value="block_number"),
                value=cst.Attribute(
                    attr=cst.Name(value="block_number"), value=cst.Name("args")
                ),
            )
        )
    method_call = cst.Call(
        func=cst.Attribute(
            attr=cst.Name(value=spec["method"]),
            value=cst.Name(value="contract"),
        ),
        args=call_args,
    )
    method_call_result_statement = cst.SimpleStatementLine(
        body=[
            cst.Assign(
                targets=[cst.AssignTarget(target=cst.Name(value="result"))],
                value=method_call,
            )
        ]
    )
    function_body_raw.append(method_call_result_statement)

    function_body_raw.append(cst.parse_statement("print(result)"))

    if requires_transaction:
        verbose_print = cst.If(
            test=cst.parse_expression("args.verbose"),
            body=cst.IndentedBlock(
                body=[
                    cst.parse_statement("print(result.info())"),
                ]
            ),
        )
        function_body_raw.append(verbose_print)

    function_body = cst.IndentedBlock(body=function_body_raw)

    function_def = cst.FunctionDef(
        name=cst.Name(value=f"handle_{function_name}"),
        params=cst.Parameters(
            params=[
                cst.Param(
                    name=cst.Name(value="args"),
                    annotation=cst.Annotation(
                        annotation=cst.Attribute(
                            attr=cst.Name(value="Namespace"),
                            value=cst.Name(value="argparse"),
                        )
                    ),
                )
            ],
        ),
        body=function_body,
        returns=cst.Annotation(annotation=cst.Name(value="None")),
    )
    return function_def


def generate_add_default_arguments() -> cst.FunctionDef:
    function_body = cst.IndentedBlock(
        body=[
            cst.parse_statement(
                'parser.add_argument("--network", required=True, help="Name of brownie network to connect to")'
            ),
            cst.parse_statement(
                'parser.add_argument("--address", required=False, help="Address of deployed contract to connect to")'
            ),
            # TODO(zomglings): The generated code could be confusing for users. Fix this so that it adds additional arguments as part of the "if" statement
            cst.If(
                test=cst.UnaryOperation(
                    operator=cst.Not(), expression=cst.Name(value="transact")
                ),
                body=cst.IndentedBlock(
                    body=[
                        cst.parse_statement(
                            'parser.add_argument("--block-number", required=False, type=int, help="Call at the given block number, defaults to latest")'
                        ),
                        cst.parse_statement("return"),
                    ]
                ),
            ),
            cst.parse_statement(
                'parser.add_argument("--sender", required=True, help="Path to keystore file for transaction sender")'
            ),
            cst.parse_statement(
                'parser.add_argument("--password", required=False, help="Password to keystore file (if you do not provide it, you will be prompted for it)")'
            ),
            cst.parse_statement(
                'parser.add_argument("--gas-price", default=None, help="Gas price at which to submit transaction")'
            ),
            cst.parse_statement(
                'parser.add_argument("--max-fee-per-gas", default=None, help="Max fee per gas for EIP1559 transactions")'
            ),
            cst.parse_statement(
                'parser.add_argument("--max-priority-fee-per-gas", default=None, help="Max priority fee per gas for EIP1559 transactions")'
            ),
            cst.parse_statement(
                'parser.add_argument("--confirmations", type=int, default=None, help="Number of confirmations to await before considering a transaction completed")'
            ),
            cst.parse_statement(
                'parser.add_argument("--nonce", type=int, default=None, help="Nonce for the transaction (optional)")'
            ),
            cst.parse_statement(
                'parser.add_argument("--value", default=None, help="Value of the transaction in wei(optional)")'
            ),
            cst.parse_statement(
                'parser.add_argument("--verbose", action="store_true", help="Print verbose output")'
            ),
        ],
    )
    function_def = cst.FunctionDef(
        name=cst.Name(value="add_default_arguments"),
        params=cst.Parameters(
            params=[
                cst.Param(
                    name=cst.Name(value="parser"),
                    annotation=cst.Annotation(
                        annotation=cst.Attribute(
                            attr=cst.Name(value="ArgumentParser"),
                            value=cst.Name(value="argparse"),
                        )
                    ),
                ),
                cst.Param(
                    name=cst.Name(value="transact"),
                    annotation=cst.Annotation(
                        annotation=cst.Name(value="bool"),
                    ),
                ),
            ],
        ),
        body=function_body,
        returns=cst.Annotation(annotation=cst.Name(value="None")),
    )
    return function_def


def generate_cli_generator(
    abi: List[Dict[str, Any]], contract_name: Optional[str] = None
) -> cst.FunctionDef:
    """
    Generates a generate_cli function that creates a CLI for the generated contract.
    """
    if contract_name is None:
        contract_name = "generated contract"
    statements: List[cst.SimpleStatementLine] = [
        cst.parse_statement(
            f'parser = argparse.ArgumentParser(description="CLI for {contract_name}")'
        ),
        cst.parse_statement("parser.set_defaults(func=lambda _: parser.print_help())"),
        cst.parse_statement("subcommands = parser.add_subparsers()"),
    ]

    constructor_abi = get_constructor(abi)
    constructor_abi["name"] = "deploy"
    constructor_spec = function_spec(constructor_abi)

    verify_contract_spec = {
        "method": "verify_contract",
        "cli": "verify-contract",
        "transact": False,
        "inputs": [],
    }

    specs: List[Dict[str, Any]] = [constructor_spec, verify_contract_spec]
    specs.extend([function_spec(item) for item in abi if item["type"] == "function"])

    for spec in specs:
        subparser_statements: List[SimpleStatementLine] = [cst.Newline()]

        subparser_name = f'{spec["method"]}_parser'

        subparser_statements.append(
            cst.parse_statement(
                f'{subparser_name} = subcommands.add_parser("{spec["cli"]}")'
            )
        )
        subparser_statements.append(
            cst.parse_statement(
                f'add_default_arguments({subparser_name}, {spec["transact"]})'
            )
        )

        for param in spec["inputs"]:
            call_args = [
                cst.Arg(
                    value=cst.SimpleString(value=f'u"{param["cli"]}"'),
                ),
                cst.Arg(
                    keyword=cst.Name(value="required"),
                    value=cst.Name(value="True"),
                ),
                cst.Arg(
                    keyword=cst.Name(value="help"),
                    value=cst.SimpleString(value=f'u"Type: {param["raw_type"]}"'),
                ),
            ]
            if param["cli_type"] is not None:
                call_args.append(
                    cst.Arg(
                        keyword=cst.Name(value="type"),
                        value=cst.Name(param["cli_type"]),
                    ),
                )

            if param["type"] == "List":
                call_args.append(
                    cst.Arg(
                        keyword=cst.Name(value="nargs"),
                        value=cst.SimpleString(value='u"+"'),
                    ),
                )
            elif param["type"] == "bool":
                call_args.append(
                    cst.Arg(
                        keyword=cst.Name(value="type"),
                        value=cst.parse_expression("boolean_argument_type"),
                    ),
                )
            elif param["type"] == "bytes":
                call_args.append(
                    cst.Arg(
                        keyword=cst.Name(value="type"),
                        value=cst.parse_expression("bytes_argument_type"),
                    ),
                )
            elif param["type"] == "tuple":
                call_args.append(
                    cst.Arg(
                        keyword=cst.Name(value="type"),
                        value=cst.parse_expression("eval"),
                    ),
                )

            add_argument_call = cst.Call(
                func=cst.Attribute(
                    attr=cst.Name(value="add_argument"),
                    value=cst.Name(value=subparser_name),
                ),
                args=call_args,
            )
            add_argument_statement = cst.SimpleStatementLine(
                body=[cst.Expr(value=add_argument_call)]
            )
            subparser_statements.append(add_argument_statement)

        subparser_statements.append(
            cst.parse_statement(
                f"{subparser_name}.set_defaults(func=handle_{spec['method']})"
            )
        )
        subparser_statements.append(cst.Newline())
        statements.extend(subparser_statements)

    statements.append(cst.parse_statement("return parser"))

    function_body = cst.IndentedBlock(body=statements)
    function_def = cst.FunctionDef(
        name=cst.Name(value="generate_cli"),
        params=cst.Parameters(params=[]),
        body=function_body,
        returns=cst.Annotation(
            annotation=cst.Attribute(
                attr=cst.Name(value="ArgumentParser"), value=cst.Name(value="argparse")
            )
        ),
    )
    return function_def


def generate_main() -> cst.FunctionDef:
    statements: List[cst.SimpleStatementLine] = [
        cst.parse_statement("parser = generate_cli()"),
        cst.parse_statement("args = parser.parse_args()"),
        cst.parse_statement("args.func(args)"),
    ]
    function_body = cst.IndentedBlock(body=statements)
    function_def = cst.FunctionDef(
        name=cst.Name(value="main"),
        params=cst.Parameters(params=[]),
        body=function_body,
        returns=cst.Annotation(annotation=cst.Name(value="None")),
    )
    return function_def


def generate_runner() -> cst.If:
    module = cst.parse_module(
        """
if __name__ == "__main__":
    main()
    """
    )
    return module.body[0]


def generate_brownie_cli(
    abi: List[Dict[str, Any]], contract_name: str
) -> List[cst.FunctionDef]:
    """
    Generates an argparse CLI to a brownie smart contract using the generated smart contract interface.

    ## Inputs

    1. `abi`: The ABI to the smart contract. This is expected to be the Python representation of a JSON
    list that conforms to the [Solidity ABI specification](https://docs.soliditylang.org/en/v0.8.16/abi-spec.html#json).

    2. `contract_name`: Name for the smart contract

    ## Outputs

    Concrete syntax tree representation of the generated code.
    """
    get_transaction_config_function = generate_get_transaction_config()
    add_default_arguments_function = generate_add_default_arguments()
    add_deploy_handler = generate_deploy_handler(get_constructor(abi), contract_name)
    add_verify_contract_handler = generate_verify_contract_handler(contract_name)
    handlers = [
        get_transaction_config_function,
        add_default_arguments_function,
        add_deploy_handler,
        add_verify_contract_handler,
    ]
    handlers.extend(
        [
            generate_cli_handler(function_abi, contract_name)
            for function_abi in abi
            if function_abi.get("type") == "function"
            and function_abi.get("name") is not None
        ]
    )
    nodes: List[cst.CSTNode] = [handler for handler in handlers if handler is not None]
    nodes.append(generate_cli_generator(abi, contract_name))
    nodes.append(generate_main())
    nodes.append(generate_runner())
    return nodes


def generate_brownie_interface(
    abi: List[Dict[str, Any]],
    contract_build: Dict[str, Any],
    contract_name: str,
    relative_path: str,
    cli: bool = True,
    format: bool = True,
    prod: bool = False,
) -> str:
    """
    Generates Python code which allows you to interact with a smart contract with a given ABI, build data, and a given name.

    The generated code uses the [`brownie`](https://github.com/eth-brownie/brownie) tool to interact with
    the blockchain.

    ## Inputs

    1. `abi`: The ABI to the smart contract. This is expected to be the Python representation of a JSON
    list that conforms to the [Solidity ABI specification](https://docs.soliditylang.org/en/v0.8.16/abi-spec.html#json).

    2. `contract_build`: `brownie` build information for the contract (e.g. its bytecode).

    3. `contract_name`: Name for the smart contract

    4. `relative_path`: Path to brownie project directory (relative to target path for the generated code).

    5. `cli`: Set to True if a CLI should be generated in addition to a Python class.

    6. `format`: If True, uses [`black`](https://github.com/psf/black) to format the generated code before
    returning it.

    7. `prod`: If True, creates a self-contained file. Generated code will not require reference to an
    existing brownie project at its runtime.


    ## Outputs
    The generated code as a string.
    """
    contract_class = generate_brownie_contract_class(abi, contract_name)
    module_body = [contract_class]

    if cli:
        contract_cli_functions = generate_brownie_cli(abi, contract_name)
        module_body.extend(contract_cli_functions)

    contract_body = cst.Module(body=module_body).code
    if prod:
        content = BROWNIE_INTERFACE_PROD_TEMPLATE.format(
            contract_abi=abi,
            contract_build={
                "bytecode": contract_build["bytecode"],
                "abi": contract_build["abi"],
                "contractName": contract_build["contractName"],
            },
            contract_body=contract_body,
            moonworm_version=MOONWORM_VERSION,
        )
    else:
        content = BROWNIE_INTERFACE_TEMPLATE.format(
            contract_body=contract_body,
            moonworm_version=MOONWORM_VERSION,
            relative_path=relative_path,
        )

    if format:
        content = format_code(content)

    return content
