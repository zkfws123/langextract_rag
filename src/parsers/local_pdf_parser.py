"""
本地 PDF 解析器 - 使用 PyMuPDF (fitz) 作为 MinerU 的备选方案
"""

from pathlib import Path
from typing import Optional

try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False


class LocalPDFParser:
    """
    Local PDF parser using PyMuPDF.
    Fallback option when MinerU API is unavailable.
    """
    
    def __init__(self):
        if not PYMUPDF_AVAILABLE:
            raise ImportError("pymupdf is not installed. Run: pip install pymupdf")
    
    def parse_pdf(self, pdf_path: Path) -> Optional[str]:
        """
        Parse PDF to text using PyMuPDF.
        
        Note: This is a simple text extraction, not as advanced as MinerU.
        Tables and complex layouts may not be preserved.
        
        Args:
            pdf_path: Path to local PDF file
            
        Returns:
            Extracted text as markdown-like format
        """
        pdf_file = Path(pdf_path)
        if not pdf_file.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        
        doc = fitz.open(pdf_file)
        page_count = len(doc)  # Save page count before closing
        
        text_parts = []
        text_parts.append(f"# {pdf_file.stem}\n")
        
        for page_num, page in enumerate(doc, 1):
            text_parts.append(f"\n## 第 {page_num} 页\n")
            
            # Extract text
            text = page.get_text("text")
            if text.strip():
                text_parts.append(text)
            
            # Extract tables (basic detection)
            tables = page.find_tables()
            if tables:
                for table in tables:
                    text_parts.append("\n**[表格]**\n")
                    try:
                        df = table.to_pandas()
                        text_parts.append(df.to_markdown(index=False))
                    except:
                        # Fallback to raw extraction
                        for row in table.extract():
                            text_parts.append(" | ".join(str(cell) for cell in row))
                            text_parts.append("\n")
        
        doc.close()
        
        markdown_text = "\n".join(text_parts)
        print(f"[LocalPDF] Extracted {len(markdown_text):,} chars from {page_count} pages")
        
        return markdown_text
