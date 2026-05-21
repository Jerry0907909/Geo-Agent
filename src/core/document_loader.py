"""Document Loader - 基于 LangChain 的文档加载器

使用 LangChain Document 和 DocumentLoader 实现文献加载。
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence

from langchain_core.documents import Document
from langchain_community.document_loaders import (
    DirectoryLoader,
    TextLoader,
    UnstructuredMarkdownLoader,
)

from src.utils.config import get_config

logger = logging.getLogger(__name__)


class LangChainDocumentLoader:
    """基于 LangChain 的文档加载器
    
    支持从目录加载多种格式的文档，使用 LangChain Document 标准格式。
    """

    def __init__(
        self,
        documents_dir: str | Path | List[str | Path],
        glob_pattern: str = "**/*",
        extensions: Optional[Sequence[str]] = None,
    ) -> None:
        """初始化文档加载器
        
        Args:
            documents_dir: 文档目录（支持单个或多个）
            glob_pattern: 文件匹配模式
            extensions: 支持的文件扩展名
        """
        # 支持单个目录或多个目录
        if isinstance(documents_dir, (str, Path)):
            self.documents_dirs = [Path(documents_dir)]
        else:
            self.documents_dirs = [Path(d) for d in documents_dir]
        
        self.glob_pattern = glob_pattern
        self.extensions = set(e.lower().lstrip(".") for e in (extensions or ["txt", "md"]))

    def _get_loader_for_extension(self, ext: str):
        """根据扩展名获取对应的加载器类"""
        loaders = {
            "txt": TextLoader,
            "md": UnstructuredMarkdownLoader,
        }
        return loaders.get(ext.lower(), TextLoader)

    def _iter_files(self) -> Iterable[Path]:
        """遍历所有目录下的匹配文件"""
        files: List[Path] = []
        
        for documents_dir in self.documents_dirs:
            if not documents_dir.exists():
                logger.warning(f"目录不存在: {documents_dir}")
                continue
            
            for path in documents_dir.rglob(self.glob_pattern):
                if path.is_file() and path.suffix.lower().lstrip(".") in self.extensions:
                    files.append(path)
        
        return files

    def load(
        self,
        encoding: str = "utf-8",
        errors: str = "ignore",
    ) -> List[Document]:
        """加载目录下所有文档
        
        Args:
            encoding: 文件编码
            errors: 读取错误处理策略
            
        Returns:
            LangChain Document 列表
        """
        documents: List[Document] = []

        for file_path in self._iter_files():
            try:
                # 读取文件内容
                text = file_path.read_text(encoding=encoding, errors=errors)
                
                if not text.strip():
                    continue
                
                # 确定文件所在的目录
                parent_dir = None
                for doc_dir in self.documents_dirs:
                    try:
                        file_path.relative_to(doc_dir)
                        parent_dir = doc_dir
                        break
                    except ValueError:
                        continue
                
                # 构建元数据
                metadata: Dict[str, Any] = {
                    "source": str(file_path),
                    "file_name": file_path.name,
                    "extension": file_path.suffix.lower().lstrip("."),
                    "relative_path": str(file_path.relative_to(parent_dir)) if parent_dir else file_path.name,
                    "collection": parent_dir.name if parent_dir else "unknown"
                }
                
                # 创建 LangChain Document
                documents.append(Document(page_content=text, metadata=metadata))
                
            except OSError as e:
                logger.warning(f"读取文件失败 {file_path}: {e}")
                continue

        logger.info(f"[文档加载器] 加载了 {len(documents)} 个文档")
        return documents

    def load_files(
        self,
        files: Iterable[str | Path],
        encoding: str = "utf-8",
        errors: str = "ignore",
    ) -> List[Document]:
        """从给定文件列表加载文档
        
        Args:
            files: 文件路径列表
            encoding: 文件编码
            errors: 读取错误处理策略
            
        Returns:
            LangChain Document 列表
        """
        documents: List[Document] = []

        for file in files:
            path = Path(file)
            if not path.is_file():
                continue
            try:
                text = path.read_text(encoding=encoding, errors=errors)
                
                if not text.strip():
                    continue
                
                metadata: Dict[str, Any] = {
                    "source": str(path),
                    "file_name": path.name,
                    "extension": path.suffix.lower().lstrip("."),
                }
                documents.append(Document(page_content=text, metadata=metadata))
                
            except OSError as e:
                logger.warning(f"读取文件失败 {path}: {e}")
                continue

        return documents

    def lazy_load(self) -> Iterable[Document]:
        """惰性加载文档（节省内存）
        
        Yields:
            LangChain Document
        """
        for file_path in self._iter_files():
            try:
                text = file_path.read_text(encoding="utf-8", errors="ignore")
                
                if not text.strip():
                    continue
                
                parent_dir = None
                for doc_dir in self.documents_dirs:
                    try:
                        file_path.relative_to(doc_dir)
                        parent_dir = doc_dir
                        break
                    except ValueError:
                        continue
                
                metadata: Dict[str, Any] = {
                    "source": str(file_path),
                    "file_name": file_path.name,
                    "extension": file_path.suffix.lower().lstrip("."),
                    "relative_path": str(file_path.relative_to(parent_dir)) if parent_dir else file_path.name,
                    "collection": parent_dir.name if parent_dir else "unknown"
                }
                
                yield Document(page_content=text, metadata=metadata)
                
            except OSError:
                continue


# 保留旧类名作为别名
DocumentLoader = LangChainDocumentLoader


def create_document_loader() -> LangChainDocumentLoader:
    """根据配置创建默认的 DocumentLoader
    
    支持多个文献目录，包括主目录和数据集目录。
    """
    config = get_config()
    
    # 支持多目录配置
    docs_dirs = []
    
    # 主文献目录
    main_dir = config.get("data.documents_dir", "./data/documents")
    docs_dirs.append(main_dir)
    
    # 数据集目录（如果存在）
    dataset_dirs = config.get("data.dataset_dirs", [])
    if isinstance(dataset_dirs, str):
        dataset_dirs = [dataset_dirs]
    docs_dirs.extend(dataset_dirs)
    
    # 检查 qq_dataset 目录
    qq_dataset_path = Path("./data/qq_dataset")
    if qq_dataset_path.exists() and str(qq_dataset_path) not in [str(Path(d)) for d in docs_dirs]:
        docs_dirs.append(str(qq_dataset_path))
        logger.info(f"[文档加载器] 自动检测到 qq_dataset 目录")
    
    logger.info(f"[文档加载器] 扫描目录: {docs_dirs}")
    return LangChainDocumentLoader(docs_dirs)
