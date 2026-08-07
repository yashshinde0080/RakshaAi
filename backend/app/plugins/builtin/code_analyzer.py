"""Code Analyzer Plugin"""
from typing import Dict, Any, List
import ast
import re


class CodeAnalyzerPlugin:
    """Analyze code structure and complexity"""
    
    id = "code_analyzer"
    name = "Code Analyzer"
    version = "1.0.0"
    description = "Analyze Python code structure and metrics"
    author = "SovereignAI"
    
    def __init__(self):
        self.enabled = True
    
    async def initialize(self) -> bool:
        return True
    
    async def cleanup(self):
        pass
    
    def get_actions(self) -> List[str]:
        return ["analyze", "get_functions", "get_classes", "count_lines"]
    
    async def execute(self, action: str, params: Dict[str, Any]) -> Any:
        code = params.get("code", "")
        
        if action == "analyze":
            return await self.analyze(code)
        elif action == "get_functions":
            return await self.get_functions(code)
        elif action == "get_classes":
            return await self.get_classes(code)
        elif action == "count_lines":
            return await self.count_lines(code)
        else:
            raise ValueError(f"Unknown action: {action}")
    
    async def analyze(self, code: str) -> Dict[str, Any]:
        """Full code analysis"""
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return {"error": f"Syntax error: {e}"}
        
        functions = []
        classes = []
        imports = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                functions.append({
                    "name": node.name,
                    "args": len(node.args.args),
                    "line": node.lineno
                })
            elif isinstance(node, ast.ClassDef):
                classes.append({
                    "name": node.name,
                    "methods": len([n for n in node.body if isinstance(n, ast.FunctionDef)]),
                    "line": node.lineno
                })
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                imports.append(f"{node.module}")
        
        lines = code.split("\n")
        
        return {
            "functions": functions,
            "classes": classes,
            "imports": imports,
            "total_lines": len(lines),
            "code_lines": len([l for l in lines if l.strip() and not l.strip().startswith("#")]),
            "comment_lines": len([l for l in lines if l.strip().startswith("#")])
        }
    
    async def get_functions(self, code: str) -> List[Dict[str, Any]]:
        """Get function definitions"""
        analysis = await self.analyze(code)
        return analysis.get("functions", [])
    
    async def get_classes(self, code: str) -> List[Dict[str, Any]]:
        """Get class definitions"""
        analysis = await self.analyze(code)
        return analysis.get("classes", [])
    
    async def count_lines(self, code: str) -> Dict[str, int]:
        """Count lines of code"""
        lines = code.split("\n")
        return {
            "total": len(lines),
            "code": len([l for l in lines if l.strip() and not l.strip().startswith("#")]),
            "comments": len([l for l in lines if l.strip().startswith("#")]),
            "blank": len([l for l in lines if not l.strip()])
        }
    
    def get_info(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "author": self.author,
            "enabled": self.enabled,
            "actions": self.get_actions()
        }