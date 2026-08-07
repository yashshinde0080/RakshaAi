"""PDF Ingestion Plugin"""
from typing import Dict, Any, List
import io

from app.plugins.interface import PluginInterface


class PDFIngestionPlugin(PluginInterface):
    """Extract text from PDF files"""
    
    id = "pdf_ingestion"
    name = "PDF Ingestion"
    version = "1.0.0"
    description = "Extract text from PDF documents"
    author = "SovereignAI"
    
    async def initialize(self) -> bool:
        """Initialize plugin"""
        try:
            import pypdf
            self.pypdf = pypdf
            return True
        except ImportError:
            print("pypdf not installed, PDF plugin disabled")
            self.enabled = False
            return False
    
    async def cleanup(self):
        """Cleanup"""
        pass
    
    def get_actions(self) -> List[str]:
        """Get available actions"""
        return ["extract_text", "get_metadata", "get_page_count"]
    
    async def execute(self, action: str, params: Dict[str, Any]) -> Any:
        """Execute action"""
        if action == "extract_text":
            return await self.extract_text(params.get("content"))
        elif action == "get_metadata":
            return await self.get_metadata(params.get("content"))
        elif action == "get_page_count":
            return await self.get_page_count(params.get("content"))
        else:
            raise ValueError(f"Unknown action: {action}")
    
    async def extract_text(self, content: bytes) -> str:
        """Extract text from PDF"""
        if not content:
            return ""
        
        pdf_file = io.BytesIO(content)
        reader = self.pypdf.PdfReader(pdf_file)
        
        text_parts = []
        for page in reader.pages:
            text_parts.append(page.extract_text())
        
        return "\n\n".join(text_parts)
    
    async def get_metadata(self, content: bytes) -> Dict[str, Any]:
        """Get PDF metadata"""
        if not content:
            return {}
        
        pdf_file = io.BytesIO(content)
        reader = self.pypdf.PdfReader(pdf_file)
        
        metadata = reader.metadata
        if metadata:
            return {
                "title": metadata.get("/Title", ""),
                "author": metadata.get("/Author", ""),
                "subject": metadata.get("/Subject", ""),
                "creator": metadata.get("/Creator", ""),
                "pages": len(reader.pages)
            }
        return {"pages": len(reader.pages)}
    
    async def get_page_count(self, content: bytes) -> int:
        """Get page count"""
        if not content:
            return 0
        
        pdf_file = io.BytesIO(content)
        reader = self.pypdf.PdfReader(pdf_file)
        return len(reader.pages)