from crewai.tools import BaseTool
from typing import Type, List, Dict, Any, Optional, Union
from pydantic import BaseModel, Field
import requests
from bs4 import BeautifulSoup
import json
import re

class ClarityDocScraperInput(BaseModel):
    """Input schema for ClarityDocScraper."""
    topic: str = Field(..., description="The Clarity documentation topic to search for.")

class ClarityDocScraper(BaseTool):
    name: str = "Clarity Documentation Scraper"
    description: str = (
        "A tool for scraping and retrieving information from the Clarity language documentation. "
        "Useful for finding best practices, syntax, and examples for Clarity smart contract development."
    )
    args_schema: Type[BaseModel] = ClarityDocScraperInput

    def _run(self, topic: str) -> str:
        try:
            # Define documentation URLs
            urls = [
                f"https://book.clarity-lang.org/ch{i:02d}-{topic.lower().replace(' ', '-')}.html"
                for i in range(1, 13)
            ]
            urls.extend([
                "https://docs.stacks.co/docs/clarity/",
                "https://docs.stacks.co/docs/write-smart-contracts/"
            ])
            
            results = []
            for url in urls:
                try:
                    response = requests.get(url, timeout=5)
                    if response.status_code == 200:
                        soup = BeautifulSoup(response.text, 'html.parser')
                        
                        # Find code examples
                        code_blocks = soup.find_all(['pre', 'code'])
                        for block in code_blocks:
                            code = block.get_text(strip=True)
                            if any(keyword in code for keyword in ['define-', 'contract-call?', topic.lower()]):
                                results.append({
                                    "type": "example",
                                    "content": code
                                })
                        
                        # Find explanations
                        explanations = soup.find_all(['p', 'div'], class_=['content', 'explanation'])
                        for exp in explanations:
                            text = exp.get_text(strip=True)
                            if topic.lower() in text.lower():
                                results.append({
                                    "type": "explanation",
                                    "content": text
                                })
                except:
                    continue
            
            return json.dumps(results, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)})

class SmartContractGeneratorInput(BaseModel):
    """Input schema for SmartContractGenerator."""
    contract_name: str = Field(..., description="Name of the smart contract to generate.")
    features: List[str] = Field(..., description="List of features to include in the contract.")
    data_vars: Optional[List[Dict[str, str]]] = Field(default_factory=list, description="List of data variables to include.")
    maps: Optional[List[Dict[str, str]]] = Field(default_factory=list, description="List of maps to include.")
    functions: Optional[List[Dict[str, Any]]] = Field(default_factory=list, description="List of functions to implement.")
    error_codes: Optional[List[Dict[str, str]]] = Field(default_factory=list, description="List of error codes to define.")

class SmartContractGenerator(BaseTool):
    name: str = "Smart Contract Generator"
    description: str = (
        "A tool for generating Clarity smart contract code based on specified features and requirements. "
        "Generates contract scaffolding with proper syntax and best practices."
    )
    args_schema: Type[BaseModel] = SmartContractGeneratorInput

    def _run(
        self,
        contract_name: str,
        features: List[str],
        data_vars: Optional[List[Dict[str, str]]] = None,
        maps: Optional[List[Dict[str, str]]] = None,
        functions: Optional[List[Dict[str, Any]]] = None,
        error_codes: Optional[List[Dict[str, str]]] = None
    ) -> str:
        contract_parts = [
            f";; {contract_name}",
            ";; Generated smart contract based on Clarity documentation patterns",
            ""
        ]

        # Add data vars
        if data_vars:
            contract_parts.extend([";; Data vars"])
            for var in data_vars:
                if not isinstance(var, dict) or 'name' not in var or 'type' not in var:
                    continue
                contract_parts.append(f"(define-data-var {var['name']} {var['type']} {var.get('initial', 'false')})")
            contract_parts.append("")

        # Add maps
        if maps:
            contract_parts.extend([";; Maps"])
            for map_def in maps:
                if not isinstance(map_def, dict) or 'name' not in map_def:
                    continue
                key_type = map_def.get('key_type', map_def.get('key', 'principal'))
                value_type = map_def.get('value_type', map_def.get('value', 'bool'))
                contract_parts.append(f"(define-map {map_def['name']} {key_type} {value_type})")
            contract_parts.append("")

        # Add functions
        if functions:
            contract_parts.extend([";; Functions"])
            for func in functions:
                if not isinstance(func, dict) or 'name' not in func:
                    continue
                
                # Handle both parameter formats
                if 'parameters' in func:
                    args_str = " ".join([f"({param['name']} {param['type']})" for param in func.get('parameters', [])])
                elif 'args' in func:
                    args_str = " ".join([f"({arg['name']} {arg['type']})" for arg in func.get('args', [])])
                else:
                    args_str = ""
                
                func_type = "define-read-only" if func.get('is_read_only', False) else "define-public"
                body = func.get('body', '(ok true)')
                
                contract_parts.extend([
                    f"(define-{func_type} ({func['name']} {args_str})",
                    f"    {body}",
                    ")",
                    ""
                ])

        # Add error codes
        if error_codes:
            contract_parts.extend([";; Error codes"])
            for error in error_codes:
                if not isinstance(error, dict) or 'name' not in error or 'code' not in error:
                    continue
                if 'message' in error:
                    contract_parts.append(f";; {error['message']}")
                contract_parts.append(f"(define-constant {error['name']} (err u{error['code']}))")
            contract_parts.append("")

        return "\n".join(contract_parts)

class TestGeneratorInput(BaseModel):
    """Input schema for TestGenerator."""
    contract_name: str = Field(..., description="Name of the smart contract to test.")
    contract_description: str = Field(..., description="Description of what the contract does.")
    functions: List[Dict[str, Any]] = Field(..., description="List of functions to test with their signatures, descriptions, and expected behaviors.")
    test_scenarios: Optional[List[Dict[str, str]]] = Field(default_factory=list, description="List of specific test scenarios to include.")

class TestGenerator(BaseTool):
    name: str = "Test Generator"
    description: str = (
        "A tool for generating TypeScript test cases for Clarity smart contracts using the latest Clarinet SDK. "
        "Creates comprehensive test suites covering main functionality and edge cases."
    )
    args_schema: Type[BaseModel] = TestGeneratorInput

    def _get_latest_test_patterns(self) -> Dict[str, Any]:
        docs_urls = [
            "https://docs.hiro.so/stacks/clarinet-js-sdk/guides/unit-testing",
            "https://docs.hiro.so/stacks/clarinet-js-sdk/guides/integration-testing",
            "https://docs.hiro.so/stacks/clarinet-js-sdk/guides/migrate-to-the-clarinet-sdk"
        ]
        
        patterns = {
            "imports": [],
            "test_setup": [],
            "assertions": [],
            "examples": []
        }
        
        for url in docs_urls:
            try:
                response = requests.get(url, timeout=10)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # Find code blocks
                    code_blocks = soup.find_all(['pre', 'code'])
                    for block in code_blocks:
                        code = block.get_text(strip=True)
                        
                        # Categorize code examples
                        if 'import' in code.lower():
                            patterns["imports"].append(code)
                        elif any(setup in code.lower() for setup in ['beforeeach', 'beforeall', 'aftereach', 'afterall']):
                            patterns["test_setup"].append(code)
                        elif any(assert_key in code.lower() for assert_key in ['assert', 'expect', 'tobe', 'equal']):
                            patterns["assertions"].append(code)
                        elif any(test_key in code.lower() for test_key in ['describe', 'it(', 'test(', 'should']):
                            patterns["examples"].append(code)
            except:
                continue
        
        return patterns

    def _generate_test_description(self, func: Dict[str, Any]) -> str:
        """Generate a descriptive test name based on function metadata."""
        desc = func.get('description', '')
        name = func.get('name', '').replace('-', ' ')
        expected = func.get('expected_behavior', '')
        
        if desc:
            return f"should {desc.lower()}"
        elif expected:
            return f"should {expected.lower()}"
        else:
            return f"should execute {name} successfully"

    def _generate_test_assertions(self, func: Dict[str, Any], patterns: Dict[str, List[str]]) -> List[str]:
        """Generate appropriate assertions based on function type and expected behavior."""
        assertions = []
        expected_result = func.get('expected_result', '(ok true)')
        expected_behavior = func.get('expected_behavior', '')
        
        # Get relevant assertion patterns
        assertion_patterns = [p for p in patterns["assertions"] if any(
            key in p.lower() for key in ['expect', 'assert', func.get('name', '').lower()]
        )]
        
        if assertion_patterns:
            # Use the most relevant pattern
            base_assertion = assertion_patterns[0]
        else:
            base_assertion = "expect(receipt.result).toBe(types.ok(true));"

        # Add basic result assertion
        assertions.append(f"      {base_assertion}")
        
        # Add additional assertions based on expected behavior
        if expected_behavior:
            if 'error' in expected_behavior.lower():
                assertions.append(f"      expect(receipt.result).toHaveProperty('error');")
            if 'return' in expected_behavior.lower():
                assertions.append(f"      expect(receipt.result).not.toBeNull();")
            if 'state' in expected_behavior.lower():
                assertions.append(f"      // Verify state changes")
                assertions.append(f"      const state = chain.getAssetsMaps();")
                assertions.append(f"      expect(state).toBeDefined();")

        return assertions

    def _run(
        self,
        contract_name: str,
        contract_description: str,
        functions: List[Dict[str, Any]],
        test_scenarios: Optional[List[Dict[str, str]]] = None
    ) -> str:
        # Get latest patterns from docs
        patterns = self._get_latest_test_patterns()
        
        # Use the latest import pattern or fall back to default
        latest_import = next((imp for imp in patterns["imports"] if '@stacks/blockchain-api-client' in imp), 
            "import { Chain, Clarinet, Tx, types } from '@stacks/blockchain-api-client';\n" +
            "import { describe, expect, it, beforeEach } from 'vitest';")

        test_parts = [
            latest_import,
            "",
            f"describe('{contract_name}', () => {{",
            f"  // {contract_description}",
            "  let chain: Chain;",
            "  let accounts: Map<string, Account>;",
            "",
            "  beforeEach(() => {",
            "    chain = new Chain();",
            "    accounts = new Map();",
            "    accounts.set('deployer', new Account('ST1PQHQKV0RJXZFY1DGX8MNSNYVE3VGZJSRTPGZGM'));",
            "    accounts.set('wallet_1', new Account('ST1SJ3DTE5DN7X54YDH5D64R3BCB6A2AG2ZQ8YPD5'));",
            "  });",
            ""
        ]

        # Add function tests using latest patterns
        for func in functions:
            if not isinstance(func, dict) or 'name' not in func:
                continue
            
            test_description = self._generate_test_description(func)
            assertions = self._generate_test_assertions(func, patterns)
            
            test_parts.extend([
                f"  describe('{func['name']}', () => {{",
                f"    it('{test_description}', () => {{",
                "      const deployer = accounts.get('deployer')!;",
                f"      const receipt = chain.mineBlock([",
                f"        Tx.contractCall(",
                f"          '{contract_name}',",
                f"          '{func['name']}',",
                f"          [{', '.join(func.get('args', []))}],",
                f"          deployer.address",
                "        )",
                "      ]).receipts[0];",
                ""
            ])
            
            test_parts.extend(assertions)
            test_parts.extend([
                "    });",
                "  });",
                ""
            ])

        # Add specific test scenarios
        if test_scenarios:
            for scenario in test_scenarios:
                if not isinstance(scenario, dict) or 'description' not in scenario:
                    continue
                
                # Find relevant example pattern from docs
                example_pattern = next(
                    (pattern for pattern in patterns["examples"] 
                     if any(key in pattern.lower() for key in scenario['description'].lower().split())),
                    None
                )
                
                test_parts.extend([
                    f"  describe('Scenario: {scenario['description']}', () => {{",
                    "    it('should handle the scenario correctly', () => {",
                ])
                
                if example_pattern:
                    # Adapt the example pattern to our scenario
                    adapted_pattern = example_pattern.replace(
                        'contract-name', contract_name
                    ).replace(
                        'function-name', scenario.get('function', 'test-function')
                    )
                    test_parts.append(f"      {adapted_pattern}")
                else:
                    test_parts.append(scenario.get('test_code', '      // Add test implementation'))
                
                test_parts.extend([
                    "    });",
                    "  });",
                    ""
                ])

        test_parts.extend([
            "});"
        ])

        return "\n".join(test_parts)
