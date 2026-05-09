"""通用文档导入脚本

将指定目录下的文档导入到 Chroma 向量数据库中。

支持格式: TXT, MD, PDF (需要 PyPDF2)

使用方式:
    python scripts/import_documents.py --input-dir "你的文档目录"
    python scripts/import_documents.py --input-dir "D:/地质文献" --collection geology_literature
"""

import argparse
import logging
import sys
from pathlib import Path
from typing import List

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

from src.core.document_loader import Document
from src.core.text_splitter import create_text_splitter
from src.database.chroma_manager import ChromaManager, list_all_collections

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def load_pdf(file_path: Path) -> str:
    """加载 PDF 文件内容"""
    try:
        from pypdf import PdfReader
    except ImportError:
        try:
            from PyPDF2 import PdfReader
        except ImportError:
            logger.warning(f"需要安装 pypdf 或 PyPDF2 来读取 PDF: pip install pypdf")
            return ""
    
    try:
        reader = PdfReader(str(file_path))
        text_parts = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                text_parts.append(text)
        return "\n\n".join(text_parts)
    except Exception as e:
        logger.error(f"读取 PDF 失败 {file_path}: {e}")
        return ""


def load_document(file_path: Path, encoding: str = "utf-8") -> Document | None:
    """加载单个文档"""
    suffix = file_path.suffix.lower()
    
    try:
        if suffix in [".txt", ".md"]:
            content = file_path.read_text(encoding=encoding, errors="ignore")
        elif suffix == ".pdf":
            content = load_pdf(file_path)
        else:
            logger.warning(f"不支持的文件格式: {file_path}")
            return None
        
        if not content.strip():
            logger.warning(f"文件内容为空: {file_path}")
            return None
        
        return Document(
            page_content=content,
            metadata={
                "source": file_path.name,
                "file_path": str(file_path),
                "file_type": suffix.lstrip("."),
            }
        )
    except Exception as e:
        logger.error(f"加载文件失败 {file_path}: {e}")
        return None


def find_documents(input_dir: Path, extensions: List[str]) -> List[Path]:
    """查找所有文档文件"""
    files = []
    for ext in extensions:
        files.extend(input_dir.rglob(f"*.{ext}"))
    return sorted(files)


def main():
    parser = argparse.ArgumentParser(
        description="将文档导入到 Chroma 向量数据库"
    )
    parser.add_argument(
        "--input-dir",
        type=str,
        required=True,
        help="输入文档目录"
    )
    parser.add_argument(
        "--collection",
        type=str,
        default="geology_literature",  # 使用与 RAG 相同的集合
        help="Chroma 集合名称 (默认: geology_literature)"
    )
    parser.add_argument(
        "--extensions",
        type=str,
        nargs="+",
        default=["txt", "md", "pdf"],
        help="要导入的文件扩展名 (默认: txt md pdf)"
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=1024,
        help="文本分块大小"
    )
    parser.add_argument(
        "--chunk-overlap",
        type=int,
        default=128,
        help="分块重叠大小"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=50,
        help="批量导入大小"
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="重置集合（删除现有数据）"
    )
    parser.add_argument(
        "--list-collections",
        action="store_true",
        help="列出所有集合并退出"
    )
    
    args = parser.parse_args()
    
    # 列出集合
    if args.list_collections:
        collections = list_all_collections()
        print(f"现有集合: {collections}")
        return
    
    # 检查输入目录
    input_dir = Path(args.input_dir)
    if not input_dir.exists():
        logger.error(f"目录不存在: {input_dir}")
        sys.exit(1)
    
    logger.info(f"输入目录: {input_dir}")
    logger.info(f"目标集合: {args.collection}")
    logger.info(f"文件类型: {args.extensions}")
    
    # 查找文档
    doc_files = find_documents(input_dir, args.extensions)
    logger.info(f"找到 {len(doc_files)} 个文档文件")
    
    if not doc_files:
        logger.warning("未找到任何文档")
        sys.exit(0)
    
    # 加载文档
    documents: List[Document] = []
    for file_path in doc_files:
        doc = load_document(file_path)
        if doc:
            documents.append(doc)
            logger.info(f"  已加载: {file_path.name} ({len(doc.page_content)} 字符)")
    
    logger.info(f"成功加载 {len(documents)} 个文档")
    
    if not documents:
        logger.warning("没有可导入的文档")
        sys.exit(0)
    
    # 创建文本分割器
    text_splitter = create_text_splitter(
        chunk_size=args.chunk_size,
        chunk_overlap=args.chunk_overlap
    )
    
    # 分割文档
    all_chunks: List[Document] = []
    for doc in documents:
        chunks = text_splitter.split_documents([doc])
        all_chunks.extend(chunks)
        logger.info(f"  {doc.metadata.get('source', '未知')}: {len(chunks)} 个片段")
    
    logger.info(f"总计 {len(all_chunks)} 个文档片段")
    
    # 创建 Chroma 管理器
    try:
        chroma_manager = ChromaManager(collection_name=args.collection)
        
        # 显示当前状态
        current_count = chroma_manager.collection.count()
        logger.info(f"集合 '{args.collection}' 当前有 {current_count} 个文档")
        
        # 重置集合
        if args.reset:
            logger.warning("正在重置集合...")
            chroma_manager.reset_collection()
            logger.info("集合已重置")
        
        # 批量导入
        logger.info("开始导入文档...")
        total_imported = 0
        
        for i in range(0, len(all_chunks), args.batch_size):
            batch = all_chunks[i:i + args.batch_size]
            try:
                ids = chroma_manager.add_documents(batch)
                total_imported += len(ids)
                logger.info(f"已导入 {total_imported}/{len(all_chunks)} 片段")
            except Exception as e:
                logger.error(f"批量导入失败: {e}")
        
        # 显示最终状态
        final_count = chroma_manager.collection.count()
        logger.info(f"导入完成! 集合 '{args.collection}' 现有 {final_count} 个文档")
        
    except Exception as e:
        logger.error(f"Chroma 操作失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
