"""API 路由定义

定义所有的 API 端点和处理逻辑。
"""

import time
from typing import List, Optional
from pathlib import Path
import tempfile

from fastapi import APIRouter, HTTPException, Path as PathParam, Query, status, UploadFile, File, Form

from src.api.schemas import (
    DocumentListResponse,
    DocumentSource,
    DocumentUploadRequest,
    DocumentUploadResponse,
    IndexRebuildRequest,
    IndexRebuildResponse,
    RAGQueryRequest,
    RAGQueryResponse,
)
from src.core.document_loader import Document
import chromadb
from chromadb.config import Settings
from src.database.chroma_manager import create_chroma_manager, list_all_collections
from src.utils.config import get_config
from src.rag.chain import create_rag_chain

# 创建路由器
router = APIRouter()


# ==================== 文件解析工具函数 ====================


def parse_pdf_content(file_path: str) -> str:
    """解析 PDF 文件内容（仅文本）"""
    try:
        from pypdf import PdfReader
        reader = PdfReader(file_path)
        text_parts = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                text_parts.append(text)
        return "\n\n".join(text_parts)
    except Exception as e:
        raise ValueError(f"PDF 解析失败: {str(e)}")


def parse_pdf_with_images(file_path: str) -> dict:
    """解析 PDF 文件，提取文本和图片
    
    Returns:
        dict: {
            "text": 完整文本内容,
            "pages": [
                {
                    "page_num": 页码,
                    "text": 该页文本,
                    "images": [{"base64": base64编码, "width": 宽, "height": 高}]
                }
            ],
            "images": [所有图片的base64列表],
            "image_count": 图片总数
        }
    """
    import base64
    import io
    
    try:
        import fitz  # pymupdf
        
        doc = fitz.open(file_path)
        result = {
            "text": "",
            "pages": [],
            "images": [],
            "image_count": 0
        }
        
        all_text_parts = []
        
        for page_num, page in enumerate(doc):
            page_data = {
                "page_num": page_num + 1,
                "text": "",
                "images": []
            }
            
            # 提取文本
            text = page.get_text()
            if text:
                page_data["text"] = text
                all_text_parts.append(f"[第{page_num + 1}页]\n{text}")
            
            # 提取图片
            image_list = page.get_images(full=True)
            for img_index, img_info in enumerate(image_list):
                try:
                    xref = img_info[0]
                    base_image = doc.extract_image(xref)
                    image_bytes = base_image["image"]
                    image_ext = base_image["ext"]
                    width = base_image.get("width", 0)
                    height = base_image.get("height", 0)
                    
                    # 过滤太小的图片（可能是图标或装饰）
                    if width < 50 or height < 50:
                        continue
                    
                    # 转为 base64
                    b64_data = base64.b64encode(image_bytes).decode('utf-8')
                    mime_type = f"image/{image_ext}" if image_ext else "image/png"
                    
                    image_data = {
                        "base64": f"data:{mime_type};base64,{b64_data}",
                        "width": width,
                        "height": height,
                        "page": page_num + 1,
                        "index": img_index
                    }
                    
                    page_data["images"].append(image_data)
                    result["images"].append(image_data)
                    
                except Exception as e:
                    # 单个图片提取失败不影响整体
                    continue
            
            result["pages"].append(page_data)
        
        doc.close()
        
        result["text"] = "\n\n".join(all_text_parts)
        result["image_count"] = len(result["images"])
        
        return result
        
    except ImportError:
        # 如果没有 pymupdf，回退到纯文本解析
        return {
            "text": parse_pdf_content(file_path),
            "pages": [],
            "images": [],
            "image_count": 0
        }
    except Exception as e:
        raise ValueError(f"PDF 解析失败: {str(e)}")


def parse_docx_content(file_path: str) -> str:
    """解析 Word (.docx) 文件内容"""
    try:
        from docx import Document as DocxDocument
        doc = DocxDocument(file_path)
        text_parts = []
        for para in doc.paragraphs:
            if para.text.strip():
                text_parts.append(para.text)
        for table in doc.tables:
            for row in table.rows:
                row_text = " | ".join(cell.text.strip() for cell in row.cells if cell.text.strip())
                if row_text:
                    text_parts.append(row_text)
        return "\n\n".join(text_parts)
    except Exception as e:
        raise ValueError(f"Word 文档解析失败: {str(e)}")


def parse_file_content(file_path: str, filename: str) -> str:
    """根据文件类型解析内容"""
    filename_lower = filename.lower()
    
    if filename_lower.endswith('.pdf'):
        return parse_pdf_content(file_path)
    elif filename_lower.endswith('.docx'):
        return parse_docx_content(file_path)
    elif filename_lower.endswith('.doc'):
        raise ValueError("暂不支持 .doc 格式，请转换为 .docx 后上传")
    else:
        encodings = ['utf-8', 'gbk', 'gb2312', 'utf-16', 'latin-1']
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    return f.read()
            except (UnicodeDecodeError, UnicodeError):
                continue
        raise ValueError("无法识别文件编码，请确保文件为有效的文本文件")


def get_file_type(filename: str) -> str:
    """根据文件名获取文件类型"""
    if not filename:
        return "other"
    
    filename_lower = filename.lower()
    if filename_lower.endswith('.md'):
        return "markdown"
    elif filename_lower.endswith('.pdf'):
        return "pdf"
    elif filename_lower.endswith(('.doc', '.docx')):
        return "word"
    elif filename_lower.endswith('.txt'):
        return "txt"
    elif filename_lower.endswith(('.xls', '.xlsx')):
        return "excel"
    elif filename_lower.endswith(('.ppt', '.pptx')):
        return "ppt"
    else:
        return "other"


# ==================== RAG 相关路由 ====================


@router.post("/rag/query", response_model=RAGQueryResponse)
async def rag_query(request: RAGQueryRequest):
    """RAG 检索与生成"""
    try:
        rag_chain = create_rag_chain()
        start_time = time.time()
        result = rag_chain.query(request.query, top_k=request.top_k)
        total_time = time.time() - start_time
        
        sources = [
            DocumentSource(
                content=doc.page_content[:300],
                source=doc.metadata.get("source") or doc.metadata.get("file_name", "未知来源"),
                relevance_score=doc.metadata.get("relevance_score"),
                metadata=doc.metadata,
            )
            for doc in result.context_documents
        ]
        
        return RAGQueryResponse(
            query=result.question,
            answer=result.answer,
            sources=sources,
            retrieval_time=total_time * 0.3,
            generation_time=total_time * 0.7,
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"RAG 查询失败: {str(e)}")


# ==================== 文献管理相关路由 ====================


@router.post("/documents/upload", response_model=DocumentUploadResponse)
async def upload_document(request: DocumentUploadRequest):
    """上传新文献（JSON 方式，用于纯文本）"""
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        from src.core.text_splitter import create_text_splitter
        
        logger.info(f"[文档上传] 开始上传: filename={request.filename}, content_length={len(request.content)}")
        
        chroma_manager = create_chroma_manager()
        text_splitter = create_text_splitter()
        
        metadata = dict(request.metadata)
        if request.filename:
            metadata["file_name"] = request.filename
            metadata["source"] = request.filename
        
        doc = Document(page_content=request.content, metadata=metadata)
        chunks = text_splitter.split_documents([doc])
        doc_ids = chroma_manager.add_documents(chunks)
        
        return DocumentUploadResponse(
            success=True,
            message=f"文档上传成功，共生成 {len(chunks)} 个片段",
            document_id=doc_ids[0] if doc_ids else None,
            num_chunks=len(chunks),
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"文档上传失败: {str(e)}")


@router.post("/documents/upload-file", response_model=DocumentUploadResponse)
async def upload_document_file(
    file: UploadFile = File(...),
    collection: Optional[str] = Form(None)
):
    """上传文件（支持 PDF、Word、Markdown、TXT 等格式）
    
    对于 PDF 文件，会自动提取图片并保存。
    
    Args:
        file: 上传的文件
        collection: 可选的目标知识库名称
    """
    import logging
    import os
    import json
    logger = logging.getLogger(__name__)
    
    try:
        from src.core.text_splitter import create_text_splitter
        
        filename = file.filename or "unknown"
        logger.info(f"[文件上传] 开始处理: {filename}, 目标集合: {collection or '默认'}")
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(filename).suffix) as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name
        
        try:
            # 判断是否为 PDF 文件
            is_pdf = filename.lower().endswith('.pdf')
            images_data = []
            
            if is_pdf:
                # PDF 文件：提取文本和图片
                pdf_result = parse_pdf_with_images(tmp_path)
                text_content = pdf_result["text"]
                images_data = pdf_result["images"]
                image_count = pdf_result["image_count"]
                logger.info(f"[文件上传] PDF 解析完成，文本长度: {len(text_content)}，图片数: {image_count}")
            else:
                # 其他文件：仅提取文本
                text_content = parse_file_content(tmp_path, filename)
                image_count = 0
            
            if not text_content.strip():
                raise ValueError("文件内容为空")
            
            # 使用指定的集合或默认集合
            chroma_manager = create_chroma_manager(collection_name=collection) if collection else create_chroma_manager()
            
            text_splitter = create_text_splitter()
            
            # 构建元数据，包含图片信息和上传时间
            from datetime import datetime
            upload_date = datetime.now().strftime("%Y-%m-%d")
            
            metadata = {
                "file_name": filename, 
                "source": filename, 
                "date": upload_date,
                "upload_time": datetime.now().isoformat(),
                "has_images": image_count > 0,
                "image_count": image_count,
            }
            
            # 如果有图片，将图片数据保存到单独的文档中
            if images_data:
                # 保存图片数据到文件系统（避免向量库存储过大）
                images_dir = Path("./data/document_images")
                images_dir.mkdir(parents=True, exist_ok=True)
                
                # 使用文件名作为图片目录
                safe_filename = "".join(c if c.isalnum() or c in '-_.' else '_' for c in filename)
                images_file = images_dir / f"{safe_filename}.json"
                
                with open(images_file, 'w', encoding='utf-8') as f:
                    json.dump({
                        "source": filename,
                        "images": images_data,
                        "image_count": image_count
                    }, f, ensure_ascii=False)
                
                metadata["images_file"] = str(images_file)
                logger.info(f"[文件上传] 图片数据已保存到: {images_file}")
            
            doc = Document(page_content=text_content, metadata=metadata)
            chunks = text_splitter.split_documents([doc])
            doc_ids = chroma_manager.add_documents(chunks)
            
            target_collection = collection or "默认知识库"
            
            message = f"文件上传成功，已添加到「{target_collection}」，共生成 {len(chunks)} 个片段"
            if image_count > 0:
                message += f"，提取了 {image_count} 张图片"
            
            return DocumentUploadResponse(
                success=True,
                message=message,
                document_id=doc_ids[0] if doc_ids else None,
                num_chunks=len(chunks),
            )
        finally:
            try:
                os.unlink(tmp_path)
            except:
                pass
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"[文件上传] 失败: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"文件上传失败: {str(e)}")


@router.get("/documents/list", response_model=DocumentListResponse)
async def list_documents(
    collection: Optional[str] = Query(None, description="指定集合名称"),
    file_type: Optional[str] = Query(None, description="按文件类型过滤")
):
    """列出所有文献"""
    try:
        sources = {}
        
        if collection:
            collections_to_query = [collection]
        else:
            collections_to_query = list_all_collections()
        
        for coll_name in collections_to_query:
            try:
                chroma_manager = create_chroma_manager(collection_name=coll_name)
                coll = chroma_manager.collection
                result = coll.get()
                metadatas = result.get("metadatas", [])
                
                for meta in metadatas:
                    if meta:
                        source = meta.get("source") or meta.get("file_name", "未知")
                        key = f"{coll_name}::{source}"
                        if key not in sources:
                            detected_type = get_file_type(source)
                            sources[key] = {
                                "source": source,
                                "collection": coll_name,
                                "author": meta.get("author"),
                                "date": meta.get("date"),
                                "type": meta.get("type", "document"),
                                "file_type": detected_type,
                                "chunks": 0,
                            }
                        sources[key]["chunks"] += 1
            except Exception as e:
                import logging
                logging.warning(f"查询集合 {coll_name} 失败: {e}")
                continue
        
        documents = list(sources.values())
        
        if file_type:
            documents = [doc for doc in documents if doc.get("file_type") == file_type]
        
        return DocumentListResponse(total=len(documents), documents=documents)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"获取文献列表失败: {str(e)}")


@router.get("/documents/content/{source_name:path}")
async def get_document_content(
    source_name: str = PathParam(..., description="文档来源名称"),
    collection: Optional[str] = Query(None, description="指定集合名称")
):
    """获取文献的完整内容"""
    import logging
    import json
    logger = logging.getLogger(__name__)
    
    try:
        if collection:
            collections_to_query = [collection]
        else:
            collections_to_query = list_all_collections()
        
        all_chunks = []
        doc_metadata = None
        images_data = []
        
        for coll_name in collections_to_query:
            try:
                chroma_manager = create_chroma_manager(collection_name=coll_name)
                coll = chroma_manager.collection
                
                result = coll.get(
                    where={"$or": [{"source": source_name}, {"file_name": source_name}]},
                    include=["documents", "metadatas"]
                )
                
                documents = result.get("documents", [])
                metadatas = result.get("metadatas", [])
                
                for i, doc_content in enumerate(documents):
                    meta = metadatas[i] if i < len(metadatas) else {}
                    chunk_id = meta.get("chunk_id", i)
                    all_chunks.append({"chunk_id": chunk_id, "content": doc_content, "metadata": meta})
                    
                    if doc_metadata is None and meta:
                        doc_metadata = {
                            "source": meta.get("source", source_name),
                            "file_name": meta.get("file_name", source_name),
                            "collection": coll_name,
                            "date": meta.get("date"),
                            "author": meta.get("author"),
                            "has_images": meta.get("has_images", False),
                            "image_count": meta.get("image_count", 0),
                        }
                        
                        # 如果有图片文件，加载图片数据
                        images_file = meta.get("images_file")
                        if images_file and Path(images_file).exists():
                            try:
                                with open(images_file, 'r', encoding='utf-8') as f:
                                    img_data = json.load(f)
                                    images_data = img_data.get("images", [])
                            except Exception as e:
                                logger.warning(f"加载图片数据失败: {e}")
                        
            except Exception as e:
                logger.warning(f"在集合 {coll_name} 中查询失败: {e}")
                continue
        
        if not all_chunks:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"未找到文献: {source_name}")
        
        all_chunks.sort(key=lambda x: x.get("chunk_id", 0))
        full_content = "\n\n".join([chunk["content"] for chunk in all_chunks])
        
        return {
            "source": source_name,
            "content": full_content,
            "chunks": all_chunks,
            "chunk_count": len(all_chunks),
            "metadata": doc_metadata or {"source": source_name},
            "images": images_data,
            "image_count": len(images_data)
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"获取文献内容失败: {str(e)}")


from src.api.schemas import DocumentUpdateRequest

@router.put("/documents/content/{source_name:path}")
async def update_document_content(
    source_name: str = PathParam(..., description="文档来源名称"),
    request: DocumentUpdateRequest = None
):
    """更新文献内容"""
    import logging
    logger = logging.getLogger(__name__)
    
    content = request.content
    collection = request.collection

    try:
        from src.core.text_splitter import create_text_splitter
        
        target_collection = collection
        if not target_collection:
            for coll_name in list_all_collections():
                try:
                    chroma_manager = create_chroma_manager(collection_name=coll_name)
                    result = chroma_manager.collection.get(
                        where={"$or": [{"source": source_name}, {"file_name": source_name}]}
                    )
                    if result.get("ids"):
                        target_collection = coll_name
                        break
                except:
                    continue
        
        if not target_collection:
            config = get_config()
            target_collection = config.get_chroma_config().get("collection_name", "geology_literature")
        
        chroma_manager = create_chroma_manager(collection_name=target_collection)
        
        try:
            result = chroma_manager.collection.get(
                where={"$or": [{"source": source_name}, {"file_name": source_name}]}
            )
            old_ids = result.get("ids", [])
            if old_ids:
                chroma_manager.delete(old_ids)
        except Exception as e:
            logger.warning(f"删除旧片段时出错: {e}")
        
        text_splitter = create_text_splitter()
        from datetime import datetime
        metadata = {"source": source_name, "file_name": source_name, "date": datetime.now().strftime("%Y-%m-%d")}
        doc = Document(page_content=content, metadata=metadata)
        chunks = text_splitter.split_documents([doc])
        doc_ids = chroma_manager.add_documents(chunks)
        
        return {
            "success": True,
            "message": f"文档更新成功，共生成 {len(chunks)} 个片段",
            "source": source_name,
            "collection": target_collection,
            "num_chunks": len(chunks)
        }
    except Exception as e:
        logger.error(f"[文档更新] 失败: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"更新文献失败: {str(e)}")


@router.delete("/documents/{doc_id}")
async def delete_document(doc_id: str = PathParam(..., description="文档ID")):
    """删除指定文献"""
    try:
        chroma_manager = create_chroma_manager()
        chroma_manager.delete([doc_id])
        return {"success": True, "message": f"文档 {doc_id} 删除成功"}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"删除文档失败: {str(e)}")


@router.delete("/documents/by-source/{source_name:path}")
async def delete_document_by_source(
    source_name: str = PathParam(..., description="文档来源名称"),
    collection: Optional[str] = Query(None, description="指定集合名称")
):
    """按来源名称删除文献的所有片段"""
    try:
        import logging
        logger = logging.getLogger(__name__)
        
        if collection:
            collections_to_query = [collection]
        else:
            collections_to_query = list_all_collections()
        
        total_deleted = 0
        
        for coll_name in collections_to_query:
            try:
                chroma_manager = create_chroma_manager(collection_name=coll_name)
                coll = chroma_manager.collection
                
                result = coll.get(where={"$or": [{"source": source_name}, {"file_name": source_name}]})
                ids_to_delete = result.get("ids", [])
                if ids_to_delete:
                    coll.delete(ids=ids_to_delete)
                    total_deleted += len(ids_to_delete)
            except Exception as e:
                logger.warning(f"在集合 {coll_name} 中删除失败: {e}")
                continue
        
        return {"success": True, "message": f"文档删除成功，共删除 {total_deleted} 个片段", "deleted_count": total_deleted}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"删除文档失败: {str(e)}")


@router.post("/documents/rebuild_index", response_model=IndexRebuildResponse)
async def rebuild_index(request: IndexRebuildRequest):
    """重建向量索引"""
    try:
        rag_chain = create_rag_chain()
        stats = rag_chain.build_index(rebuild=request.rebuild)
        return IndexRebuildResponse(
            success=True,
            message="索引重建成功",
            num_documents=stats.num_source_documents,
            num_chunks=stats.num_chunks,
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"索引重建失败: {str(e)}")


@router.get("/documents/collections")
async def list_collections():
    """列出所有知识库集合"""
    try:
        collections = list_all_collections()
        result = []
        
        for coll_name in collections:
            try:
                chroma_manager = create_chroma_manager(collection_name=coll_name)
                count = chroma_manager.collection.count()
                result.append({"name": coll_name, "count": count})
            except Exception as e:
                result.append({"name": coll_name, "count": 0, "error": str(e)})
        
        return {"total": len(result), "collections": result}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"获取集合列表失败: {str(e)}")


@router.get("/documents/file-types")
async def get_file_type_stats():
    """获取文件类型统计"""
    try:
        type_stats = {
            "markdown": {"count": 0, "label": "Markdown", "icon": "markdown", "extensions": [".md"]},
            "pdf": {"count": 0, "label": "PDF", "icon": "pdf", "extensions": [".pdf"]},
            "word": {"count": 0, "label": "Word", "icon": "word", "extensions": [".doc", ".docx"]},
            "txt": {"count": 0, "label": "文本", "icon": "txt", "extensions": [".txt"]},
            "excel": {"count": 0, "label": "Excel", "icon": "excel", "extensions": [".xls", ".xlsx"]},
            "ppt": {"count": 0, "label": "PPT", "icon": "ppt", "extensions": [".ppt", ".pptx"]},
            "other": {"count": 0, "label": "其他", "icon": "other", "extensions": []},
        }
        
        seen_sources = set()
        collections_to_query = list_all_collections()
        
        for coll_name in collections_to_query:
            try:
                chroma_manager = create_chroma_manager(collection_name=coll_name)
                coll = chroma_manager.collection
                result = coll.get()
                metadatas = result.get("metadatas", [])
                
                for meta in metadatas:
                    if meta:
                        source = meta.get("source") or meta.get("file_name", "未知")
                        key = f"{coll_name}::{source}"
                        if key not in seen_sources:
                            seen_sources.add(key)
                            file_type = get_file_type(source)
                            if file_type in type_stats:
                                type_stats[file_type]["count"] += 1
            except Exception as e:
                import logging
                logging.warning(f"统计集合 {coll_name} 失败: {e}")
                continue
        
        stats_list = [{"type": k, **v} for k, v in type_stats.items()]
        total = sum(s["count"] for s in stats_list)
        
        return {"total": total, "stats": stats_list}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"获取文件类型统计失败: {str(e)}")


@router.delete("/documents/collections/{collection_name}")
async def delete_collection(collection_name: str = PathParam(..., description="集合名称")):
    """删除整个知识库集合"""
    try:
        import logging
        logger = logging.getLogger(__name__)
        
        from src.database.chroma_manager import get_chroma_client
        client = get_chroma_client()
        
        existing = [c.name for c in client.list_collections()]
        if collection_name not in existing:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"集合 '{collection_name}' 不存在")
        
        client.delete_collection(collection_name)
        return {"success": True, "message": f"集合 '{collection_name}' 已成功删除"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"删除集合失败: {str(e)}")


@router.post("/documents/collections")
async def create_collection(request: dict):
    """创建新的知识库集合"""
    try:
        import logging
        logger = logging.getLogger(__name__)
        
        name = request.get("name", "").strip()
        if not name:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="集合名称不能为空")
        
        # 验证名称格式（只允许字母、数字、下划线、中划线）
        import re
        if not re.match(r'^[\w\-]+$', name):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="集合名称只能包含字母、数字、下划线和中划线")
        
        from src.database.chroma_manager import get_chroma_client
        client = get_chroma_client()
        
        # 检查是否已存在
        existing = [c.name for c in client.list_collections()]
        if name in existing:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"集合 '{name}' 已存在")
        
        # 创建集合
        client.create_collection(name=name)
        logger.info(f"成功创建集合: {name}")
        
        return {"success": True, "message": f"集合 '{name}' 创建成功", "name": name}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"创建集合失败: {str(e)}")


@router.put("/documents/collections/{collection_name}")
async def rename_collection(
    collection_name: str = PathParam(..., description="原集合名称"),
    request: dict = None
):
    """重命名知识库集合"""
    try:
        import logging
        logger = logging.getLogger(__name__)
        
        new_name = request.get("new_name", "").strip() if request else ""
        if not new_name:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="新名称不能为空")
        
        # 验证名称格式
        import re
        if not re.match(r'^[\w\-]+$', new_name):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="集合名称只能包含字母、数字、下划线和中划线")
        
        from src.database.chroma_manager import get_chroma_client
        client = get_chroma_client()
        
        # 检查原集合是否存在
        existing = [c.name for c in client.list_collections()]
        if collection_name not in existing:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"集合 '{collection_name}' 不存在")
        
        # 检查新名称是否已存在
        if new_name in existing:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"集合 '{new_name}' 已存在")
        
        # ChromaDB 不支持直接重命名，需要复制数据到新集合再删除旧集合
        old_collection = client.get_collection(name=collection_name)
        
        # 获取旧集合的所有数据
        old_data = old_collection.get(include=["documents", "metadatas", "embeddings"])
        
        # 创建新集合
        new_collection = client.create_collection(name=new_name)
        
        # 如果有数据，复制到新集合
        if old_data.get("ids") and len(old_data["ids"]) > 0:
            new_collection.add(
                ids=old_data["ids"],
                documents=old_data.get("documents"),
                metadatas=old_data.get("metadatas"),
                embeddings=old_data.get("embeddings")
            )
        
        # 删除旧集合
        client.delete_collection(collection_name)
        
        logger.info(f"成功重命名集合: {collection_name} -> {new_name}")
        
        return {
            "success": True, 
            "message": f"集合已重命名为 '{new_name}'",
            "old_name": collection_name,
            "new_name": new_name
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"重命名集合失败: {str(e)}")


# ==================== 系统相关路由 ====================


@router.get("/health")
async def health_check():
    """健康检查"""
    try:
        components = {}
        
        try:
            chroma_manager = create_chroma_manager()
            collection = chroma_manager.collection
            components["chroma"] = "healthy"
        except Exception as e:
            components["chroma"] = f"error: {str(e)}"
        
        try:
            from src.core.llm_provider import create_llm_provider
            llm = create_llm_provider()
            components["llm"] = "healthy"
        except Exception as e:
            components["llm"] = f"error: {str(e)}"
        
        try:
            from src.core.embedding_provider import create_embedding_provider
            embedding = create_embedding_provider()
            components["embedding"] = "healthy"
        except Exception as e:
            components["embedding"] = f"error: {str(e)}"
        
        try:
            from src.database.mysql_manager import check_database_connection
            if check_database_connection():
                components["mysql"] = "healthy"
            else:
                components["mysql"] = "not_configured"
        except Exception as e:
            components["mysql"] = f"error: {str(e)}"
        
        all_healthy = all(status == "healthy" for status in components.values())
        overall_status = "healthy" if all_healthy else "degraded"
        
        return {"status": overall_status, "version": "1.0.0", "components": components}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=f"健康检查失败: {str(e)}")


@router.get("/")
async def root():
    """根路径"""
    return {
        "service": "地质文献智能体 API",
        "version": "1.0.0",
        "description": "基于 RAG 和 Agent 的地质文献检索系统",
        "endpoints": {
            "rag": "/api/rag/query",
            "agent": "/api/agent/query",
            "documents": "/api/documents/*",
            "auth": "/api/auth/*",
            "chat": "/api/chat/*",
            "health": "/api/health",
            "docs": "/docs",
        },
    }
