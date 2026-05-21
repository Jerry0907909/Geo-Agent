"""聊天相关API路由

提供会话管理、消息发送、智能对话等接口。
"""

from datetime import datetime
import asyncio
import time
import json
import logging
from typing import Optional, List, AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException, Path, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from src.api.auth_schemas import (
    ConversationCreate,
    ConversationResponse,
    ConversationListResponse,
    ConversationUpdateRequest,
    ChatRequest,
    ChatResponse,
    MessageResponse,
    MessageListResponse,
)
from src.auth.deps import get_current_active_user, get_optional_user, get_db
from src.database.models import User, Conversation, Message, SearchHistory
from src.database.mysql_manager import get_session_local
from src.rag.chain import create_rag_chain
from src.core.llm_provider import create_llm_provider
from src.core.prompts import (
    get_chat_prompt,
    get_vision_prompt,
    build_chat_prompt_with_context,
)
from src.utils.user_llm import load_user_llm_config

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["聊天"])

MAX_CHAT_HISTORY_MESSAGES = 6
MAX_CHAT_HISTORY_TOTAL_CHARS = 4000
MAX_CHAT_HISTORY_ITEM_CHARS = 1200


def compact_chat_history(
    history: List[dict],
    *,
    max_messages: int = MAX_CHAT_HISTORY_MESSAGES,
    max_total_chars: int = MAX_CHAT_HISTORY_TOTAL_CHARS,
    max_item_chars: int = MAX_CHAT_HISTORY_ITEM_CHARS,
) -> List[dict]:
    """压缩对话历史，避免长会话把普通聊天首 token 拖慢。"""

    compacted_reversed: List[dict] = []
    total_chars = 0

    for msg in reversed(history):
        content = (msg.get("content") or "").strip()
        role = msg.get("role", "user")
        if not content:
            continue

        if len(content) > max_item_chars:
            content = content[: max_item_chars - 3].rstrip() + "..."

        estimated_chars = len(role) + len(content) + 2

        if compacted_reversed and (
            len(compacted_reversed) >= max_messages
            or total_chars + estimated_chars > max_total_chars
        ):
            break

        if not compacted_reversed and estimated_chars > max_total_chars:
            remaining = max(32, max_total_chars - len(role) - 5)
            content = content[:remaining].rstrip() + "..."
            estimated_chars = len(role) + len(content) + 2

        compacted_reversed.append({"role": role, "content": content})
        total_chars += estimated_chars

    return list(reversed(compacted_reversed))


# ==================== 会话管理 ====================


@router.post("/conversations", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    request: ConversationCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """创建新会话
    
    Args:
        request: 创建会话请求
        
    Returns:
        新会话信息
    """
    conversation = Conversation(
        user_id=current_user.id,
        title=request.title or "新对话"
    )
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    
    logger.info(f"用户 {current_user.username} 创建会话 {conversation.id}")
    
    return ConversationResponse(
        id=conversation.id,
        title=conversation.title,
        summary=conversation.summary,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        message_count=0
    )


@router.get("/conversations", response_model=ConversationListResponse)
async def list_conversations(
    limit: int = 20,
    offset: int = 0,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """获取会话列表
    
    Args:
        limit: 返回数量
        offset: 偏移量
        
    Returns:
        会话列表
    """
    conversations = (
        db.query(Conversation)
        .filter(Conversation.user_id == current_user.id, Conversation.is_active == True)
        .order_by(Conversation.updated_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    
    total = (
        db.query(Conversation)
        .filter(Conversation.user_id == current_user.id, Conversation.is_active == True)
        .count()
    )
    
    result = []
    for conv in conversations:
        msg_count = db.query(Message).filter(Message.conversation_id == conv.id).count()
        result.append(ConversationResponse(
            id=conv.id,
            title=conv.title or "新对话",
            summary=conv.summary,
            created_at=conv.created_at,
            updated_at=conv.updated_at,
            message_count=msg_count
        ))
    
    return ConversationListResponse(total=total, conversations=result)


@router.get("/conversations/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: int = Path(..., description="会话ID", ge=1),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """获取会话详情
    
    Args:
        conversation_id: 会话ID
        
    Returns:
        会话详情
    """
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == current_user.id
    ).first()
    
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="会话不存在"
        )
    
    msg_count = db.query(Message).filter(Message.conversation_id == conversation_id).count()
    
    return ConversationResponse(
        id=conversation.id,
        title=conversation.title,
        summary=conversation.summary,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        message_count=msg_count
    )


@router.put("/conversations/{conversation_id}", response_model=ConversationResponse)
async def update_conversation(
    request: ConversationUpdateRequest,
    conversation_id: int = Path(..., description="会话ID", ge=1),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """更新会话
    
    Args:
        conversation_id: 会话ID
        request: 更新请求
        
    Returns:
        更新后的会话
    """
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == current_user.id
    ).first()
    
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="会话不存在"
        )
    
    if request.title is not None:
        conversation.title = request.title
    
    db.commit()
    db.refresh(conversation)
    
    msg_count = db.query(Message).filter(Message.conversation_id == conversation_id).count()
    
    return ConversationResponse(
        id=conversation.id,
        title=conversation.title,
        summary=conversation.summary,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        message_count=msg_count
    )


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: int = Path(..., description="会话ID", ge=1),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """删除会话
    
    Args:
        conversation_id: 会话ID
        
    Returns:
        删除成功消息
    """
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == current_user.id
    ).first()
    
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="会话不存在"
        )
    
    # 软删除
    conversation.is_active = False
    db.commit()
    
    logger.info(f"用户 {current_user.username} 删除会话 {conversation_id}")
    
    return {"message": "会话已删除"}


@router.post("/conversations/batch-delete")
async def batch_delete_conversations(
    conversation_ids: List[int],
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """批量删除会话
    
    Args:
        conversation_ids: 会话ID列表
        
    Returns:
        删除结果
    """
    if not conversation_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="会话ID列表不能为空"
        )
    
    # 查询属于当前用户的会话
    conversations = db.query(Conversation).filter(
        Conversation.id.in_(conversation_ids),
        Conversation.user_id == current_user.id,
        Conversation.is_active == True
    ).all()
    
    deleted_count = 0
    for conversation in conversations:
        conversation.is_active = False
        deleted_count += 1
    
    db.commit()
    
    logger.info(f"用户 {current_user.username} 批量删除 {deleted_count} 个会话")
    
    return {
        "message": f"成功删除 {deleted_count} 个会话",
        "deleted_count": deleted_count,
        "requested_count": len(conversation_ids)
    }


# ==================== 消息管理 ====================


@router.get("/conversations/{conversation_id}/messages", response_model=MessageListResponse)
async def get_messages(
    conversation_id: int = Path(..., description="会话ID", ge=1),
    limit: Optional[int] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """获取会话消息
    
    Args:
        conversation_id: 会话ID
        limit: 返回数量限制
        
    Returns:
        消息列表
    """
    # 验证会话归属
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == current_user.id
    ).first()
    
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="会话不存在"
        )
    
    query = (
        db.query(Message)
        .filter(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
    )
    
    if limit:
        query = query.limit(limit)
    
    messages = query.all()
    
    # 手动构建消息响应，确保字段正确映射
    message_responses = []
    for m in messages:
        message_responses.append(MessageResponse(
            id=m.id,
            conversation_id=m.conversation_id,
            role=m.role,
            content=m.content,
            message_metadata=m.message_metadata,
            created_at=m.created_at
        ))
    
    return MessageListResponse(
        conversation_id=conversation_id,
        messages=message_responses,
        total=len(messages)
    )


# ==================== 智能对话 ====================


@router.post("/send", response_model=ChatResponse)
async def send_message(
    request: ChatRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """发送消息并获取AI回复
    
    支持RAG检索和普通对话两种模式。
    
    Args:
        request: 聊天请求
        
    Returns:
        AI回复和相关信息
    """
    start_time = time.time()
    
    # 获取或创建会话
    if request.conversation_id:
        conversation = db.query(Conversation).filter(
            Conversation.id == request.conversation_id,
            Conversation.user_id == current_user.id
        ).first()
        
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="会话不存在"
            )
    else:
        # 创建新会话
        conversation = Conversation(
            user_id=current_user.id,
            title=request.message[:50] + ("..." if len(request.message) > 50 else "")
        )
        db.add(conversation)
        db.commit()
        db.refresh(conversation)
    
    # 保存用户消息
    user_message = Message(
        conversation_id=conversation.id,
        role="user",
        content=request.message
    )
    db.add(user_message)
    db.commit()
    
    try:
        # 获取历史上下文
        history_messages = (
            db.query(Message)
            .filter(Message.conversation_id == conversation.id)
            .order_by(Message.created_at.desc())
            .limit(10)
            .all()
        )[::-1]  # 反转为时间正序
        
        # 构建上下文
        context_messages = []
        for msg in history_messages[:-1]:  # 排除刚添加的用户消息
            context_messages.append({
                "role": msg.role,
                "content": msg.content
            })
        
        # 执行AI回复
        sources = []
        reasoning_steps = []
        
        if request.mode == "rag":
            # RAG模式 - 文献检索增强生成（用户级隔离 + 用户 LLM 配置）
            user_llm = load_user_llm_config(db, current_user.id)
            if user_llm and request.model_name:
                user_llm = dict(user_llm)
                user_llm["model_name"] = request.model_name
            rag_chain = create_rag_chain(user_llm_config=user_llm)
            result = rag_chain.query(request.message, top_k=request.top_k, user_id=str(current_user.id))
            answer = result.answer
            
            # 提取来源
            if request.return_sources and result.context_documents:
                for doc in result.context_documents:
                    sources.append({
                        "content": doc.page_content[:300],
                        "source": doc.metadata.get("source", "未知来源"),
                        "relevance_score": doc.metadata.get("relevance_score")
                    })
        
        else:
            # 普通对话模式 - 直接使用LLM（用户配置）
            user_llm = load_user_llm_config(db, current_user.id)
            if user_llm and request.model_name:
                user_llm = dict(user_llm)
                user_llm["model_name"] = request.model_name
            llm = create_llm_provider(enable_thinking=False, user_llm_config=user_llm)
            
            # 构建带有历史上下文的提示
            system_prompt = get_chat_prompt()
            
            # 构建对话历史
            messages_for_llm = [{"role": "system", "content": system_prompt}]
            for msg in context_messages[-6:]:  # 最近6条历史消息
                messages_for_llm.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })
            messages_for_llm.append({"role": "user", "content": request.message})
            
            # 使用chat接口如果可用，否则使用generate
            if hasattr(llm, 'chat') and callable(getattr(llm, 'chat')):
                answer = llm.chat(messages_for_llm)
            else:
                # 将消息格式化为文本
                prompt_text = "\n".join([
                    f"{m['role']}: {m['content']}" for m in messages_for_llm
                ]) + "\nassistant:"
                answer = llm.generate(prompt_text)
        
        # 保存AI回复
        assistant_message = Message(
            conversation_id=conversation.id,
            role="assistant",
            content=answer,
            message_metadata={
                "sources": sources,
                "reasoning_steps": reasoning_steps,
                "mode": request.mode
            }
        )
        db.add(assistant_message)
        
        # 更新会话时间
        from datetime import datetime
        conversation.updated_at = datetime.now()
        
        # 记录搜索历史
        search_history = SearchHistory(
            user_id=current_user.id,
            query=request.message,
            result_count=len(sources),
            search_type=request.mode,
            response_time=int((time.time() - start_time) * 1000)
        )
        db.add(search_history)
        
        db.commit()
        db.refresh(assistant_message)
        
        execution_time = time.time() - start_time
        
        return ChatResponse(
            conversation_id=conversation.id,
            message_id=assistant_message.id,
            answer=answer,
            sources=sources,
            reasoning_steps=reasoning_steps,
            execution_time=execution_time
        )
    
    except Exception as e:
        logger.error(f"聊天处理失败: {e}")
        
        # 保存错误消息
        error_message = Message(
            conversation_id=conversation.id,
            role="assistant",
            content=f"抱歉，处理您的请求时出现错误：{str(e)}",
            message_metadata={"error": str(e)}
        )
        db.add(error_message)
        db.commit()
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"处理请求失败: {str(e)}"
        )


@router.post("/quick-query")
async def quick_query(
    request: ChatRequest,
    current_user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db)
):
    """快速查询（无需创建会话）
    
    支持未登录用户进行简单查询。
    
    Args:
        request: 聊天请求
        
    Returns:
        AI回复
    """
    start_time = time.time()
    
    try:
        sources = []
        reasoning_steps = []
        
        if request.mode == "rag":
            # RAG模式（用户级隔离 + 用户 LLM 配置）
            user_llm = load_user_llm_config(db, current_user.id) if current_user else None
            if user_llm and current_user and request.model_name:
                user_llm = dict(user_llm)
                user_llm["model_name"] = request.model_name
            rag_chain = create_rag_chain(user_llm_config=user_llm)
            uid = str(current_user.id) if current_user else None
            result = rag_chain.query(request.message, top_k=request.top_k, user_id=uid)
            answer = result.answer
            
            if request.return_sources and result.context_documents:
                for doc in result.context_documents:
                    sources.append({
                        "content": doc.page_content[:300],
                        "source": doc.metadata.get("source", "未知来源")
                    })
        
        else:
            # 普通对话模式（用户配置）
            user_llm = load_user_llm_config(db, current_user.id) if current_user else None
            if user_llm and current_user and request.model_name:
                user_llm = dict(user_llm)
                user_llm["model_name"] = request.model_name
            llm = create_llm_provider(enable_thinking=False, user_llm_config=user_llm)
            system_prompt = get_chat_prompt()
            prompt = f"{system_prompt}\n\n用户问题: {request.message}\n\n请回答:"
            answer = llm.generate(prompt)
        
        # 如果用户已登录，记录搜索历史
        if current_user:
            search_history = SearchHistory(
                user_id=current_user.id,
                query=request.message,
                result_count=len(sources),
                search_type=request.mode,
                response_time=int((time.time() - start_time) * 1000)
            )
            db.add(search_history)
            db.commit()
        
        return {
            "answer": answer,
            "sources": sources,
            "reasoning_steps": reasoning_steps,
            "mode": request.mode,
            "execution_time": time.time() - start_time
        }
    
    except Exception as e:
        logger.error(f"快速查询失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"查询失败: {str(e)}"
        )


# ==================== 推荐问题生成 ====================

class FollowUpRequest(BaseModel):
    """推荐问题请求"""
    question: str = Field(..., description="用户问题")
    answer: str = Field(..., description="AI回答")


@router.post("/follow-up")
async def generate_follow_up_questions(
    request: FollowUpRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """生成推荐的后续问题
    
    基于用户问题和AI回答，生成相关的后续问题建议。
    """
    try:
        user_llm = load_user_llm_config(db, current_user.id)
        llm = create_llm_provider(enable_thinking=False, user_llm_config=user_llm)

        prompt = f"""基于以下对话内容，生成3个用户可能想要继续追问的问题。

要求：
- 每个问题必须与上述具体对话内容直接相关，不要生成泛泛的问题
- 问题应自然延伸对话，像真人会追问的那样
- 简洁明了，每个问题不超过30字
- 避免生成"能详细解释一下吗"这类笼统问题

用户问题：{request.question}

AI回答：{request.answer[:800]}

请直接输出3个问题，每行一个，不要编号："""
        
        response = llm.generate(prompt)
        
        # 解析响应，提取问题
        questions = []
        for line in response.strip().split('\n'):
            line = line.strip()
            # 移除可能的编号前缀
            if line and len(line) > 5:
                # 移除 "1." "1、" "1)" 等前缀
                import re
                line = re.sub(r'^[\d]+[.、)]\s*', '', line)
                if line:
                    questions.append(line)
        
        return {"questions": questions[:3]}
        
    except Exception as e:
        logger.error(f"生成推荐问题失败: {e}")
        # 返回空列表，让前端使用本地生成
        return {"questions": []}


# ==================== 流式对话 ====================

@router.post("/stream")
async def stream_chat(
    request: ChatRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """流式发送消息并获取AI回复
    
    使用Server-Sent Events (SSE) 流式返回AI回复。
    
    Args:
        request: 聊天请求
        
    Returns:
        StreamingResponse: SSE流式响应
    """
    
    current_user_id = current_user.id

    # 获取或创建会话
    if request.conversation_id:
        conversation = db.query(Conversation).filter(
            Conversation.id == request.conversation_id,
            Conversation.user_id == current_user_id
        ).first()
        
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="会话不存在"
            )
    else:
        # 创建新会话
        title = request.message[:50] + ("..." if len(request.message) > 50 else "")
        conversation = Conversation(
            user_id=current_user_id,
            title=title
        )
        db.add(conversation)
        db.commit()
        db.refresh(conversation)

    conversation_id = conversation.id
    
    # 保存用户消息
    user_message = Message(
        conversation_id=conversation_id,
        role="user",
        content=request.message
    )
    db.add(user_message)
    db.commit()

    history_payload = []
    if request.mode == "chat":
        # 在请求级 session 结束前提取必要上下文，避免流式阶段访问 ORM 实例。
        history_messages = (
            db.query(Message)
            .filter(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.desc())
            .limit(10)
            .all()
        )[::-1]
        history_payload = [
            {"role": msg.role, "content": msg.content}
            for msg in history_messages
        ]
    
    async def generate_stream() -> AsyncGenerator[str, None]:
        """生成SSE流"""
        start_time = time.time()
        full_response = ""
        sources = []

        # 加载用户的 LLM 配置
        user_llm_config = None
        stream_db_llm = get_session_local()()
        try:
            user_llm_config = load_user_llm_config(stream_db_llm, current_user_id)
            # 如果前端请求指定了 model_name，优先使用（覆盖 DB 配置）
            if user_llm_config and request.model_name:
                user_llm_config = dict(user_llm_config)
                user_llm_config["model_name"] = request.model_name
                logger.info(
                    "[Stream] 前端指定 model_name=%s，已覆盖 DB 配置",
                    request.model_name,
                )
            if user_llm_config:
                logger.info(
                    "[Stream] 使用用户 LLM: provider=%s model=%s base_url=%s",
                    user_llm_config.get("provider"),
                    user_llm_config.get("model_name"),
                    user_llm_config.get("base_url"),
                )
            else:
                logger.warning(
                    "[Stream] 未加载到用户 LLM 配置 (user_id=%s)，将回退 config.yaml",
                    current_user_id,
                )
                # 仅在没有配置或需要提示时告知前端
        except Exception:
            logger.exception("[Stream] 加载用户 LLM 配置失败 (user_id=%s)", current_user_id)
        finally:
            stream_db_llm.close()

        try:
            # 发送会话信息
            yield f"data: {json.dumps({'type': 'info', 'conversation_id': conversation_id}, ensure_ascii=False)}\n\n"

            # 提示用户当前使用的模型来源
            if user_llm_config and user_llm_config.get("provider"):
                provider = user_llm_config.get("provider", "")
                model = user_llm_config.get("model_name", "")
                yield f"data: {json.dumps({'type': 'status', 'message': f'当前模型: {provider} / {model}'}, ensure_ascii=False)}\n\n"
            
            if request.mode == "chat":
                # 普通对话模式 - 流式输出
                
                # 检查是否有图像
                has_image = request.image_base64 is not None and len(request.image_base64) > 0
                
                if has_image:
                    # 使用视觉模型处理图像
                    logger.info(f"[Chat Mode] 检测到图像，使用视觉模型")
                    yield f"data: {json.dumps({'type': 'status', 'message': '正在分析图像...'}, ensure_ascii=False)}\n\n"
                    
                    try:
                        from src.core.vision_provider import create_vision_provider
                        import base64
                        
                        vision_provider = create_vision_provider(user_llm_config=user_llm_config)

                        # 解码图像
                        image_data = base64.b64decode(request.image_base64)
                        
                        history = compact_chat_history(history_payload[:-1])
                        
                        system_prompt = get_vision_prompt()
                        
                        yield f"data: {json.dumps({'type': 'status', 'message': '正在生成回答...'}, ensure_ascii=False)}\n\n"
                        
                        # 流式生成
                        async for chunk in vision_provider.astream_analyze_image(
                            image_data=image_data,
                            question=request.message,
                            system_prompt=system_prompt,
                            history=history
                        ):
                            full_response += chunk
                            yield f"data: {json.dumps({'type': 'content', 'content': chunk}, ensure_ascii=False)}\n\n"
                    
                    except Exception as e:
                        logger.error(f"[Chat Mode] 图像分析失败: {e}")
                        import traceback
                        logger.error(traceback.format_exc())
                        yield f"data: {json.dumps({'type': 'error', 'message': f'图像分析失败: {str(e)}'}, ensure_ascii=False)}\n\n"
                        return
                
                else:
                    # 纯文本对话
                    # WebSearch 增强
                    web_context = ""
                    logger.info(f"[Chat Mode] web_search={request.web_search}")
                    
                    if request.web_search:
                        logger.info(f"[Chat Mode] 开始 WebSearch: query='{request.message}'")
                        yield f"data: {json.dumps({'type': 'status', 'message': '正在搜索网络信息...'}, ensure_ascii=False)}\n\n"
                        try:
                            from src.tools.web_search import create_web_search_tool
                            web_tool = create_web_search_tool()
                            web_results = web_tool.search(request.message, max_results=5)
                            
                            logger.info(f"[Chat Mode] WebSearch 返回 {len(web_results)} 条结果")
                            
                            if web_results:
                                web_context = web_tool.format_for_llm(web_results)
                                logger.info(f"[Chat Mode] 格式化后的上下文长度: {len(web_context)}")
                                
                                # 发送网络来源
                                for result in web_results:
                                    sources.append({
                                        "content": result.snippet,
                                        "source": result.title,
                                        "url": result.url,
                                        "type": "web",
                                        "source_type": result.source_type,
                                        "metadata": {}
                                    })
                                yield f"data: {json.dumps({'type': 'sources', 'sources': sources}, ensure_ascii=False)}\n\n"
                                logger.info(f"[Chat Mode] 已发送 {len(sources)} 条网络来源")
                            else:
                                logger.warning(f"[Chat Mode] WebSearch 返回空结果")
                            
                        except Exception as e:
                            logger.error(f"[Chat Mode] WebSearch 失败: {type(e).__name__}: {e}")
                            import traceback
                            logger.error(traceback.format_exc())
                    
                    # 使用默认提示词
                    system_prompt = get_chat_prompt()
                    llm = create_llm_provider(enable_thinking=False, user_llm_config=user_llm_config)
                    
                    if web_context:
                        system_prompt += f"\n\n参考网络信息：\n{web_context}\n\n请基于上述网络信息回答问题，并用【来源X】标注引用。"
                    
                    compact_history = compact_chat_history(history_payload[:-1])
                    context = "\n".join([
                        f"{msg['role']}: {msg['content']}" 
                        for msg in compact_history
                    ])
                    
                    if context:
                        prompt = f"{system_prompt}\n\n历史对话:\n{context}\n\nuser: {request.message}\nassistant:"
                    else:
                        prompt = f"{system_prompt}\n\nuser: {request.message}\nassistant:"
                    
                    yield f"data: {json.dumps({'type': 'status', 'message': '正在生成回答...'}, ensure_ascii=False)}\n\n"
                    
                    # 流式生成
                    llm_start_time = time.time()
                    first_chunk_logged = False
                    async for chunk in llm.astream_generate(prompt):
                        if not first_chunk_logged:
                            logger.info(
                                "[Chat Mode] 首个 token 耗时 %.3fs (history=%d, prompt_chars=%d, web_search=%s)",
                                time.time() - llm_start_time,
                                len(compact_history),
                                len(prompt),
                                request.web_search,
                            )
                            first_chunk_logged = True
                        full_response += chunk
                        yield f"data: {json.dumps({'type': 'content', 'content': chunk}, ensure_ascii=False)}\n\n"
            
            elif request.mode == "rag":
                # RAG模式 — 使用搜索编排器（意图识别 → 并行检索 → 融合 → 生成）
                yield f"data: {json.dumps({'type': 'status', 'message': '正在检索文献...'}, ensure_ascii=False)}\n\n"

                from src.rag.search_orchestrator import create_search_orchestrator
                from src.rag.web_enhanced_retriever import create_web_enhanced_rag_retriever
                from src.tools.web_search import create_web_search_tool

                kb_retriever = create_web_enhanced_rag_retriever(
                    user_llm_config=user_llm_config
                )
                web_tool = create_web_search_tool()
                llm = create_llm_provider(
                    enable_thinking=False, user_llm_config=user_llm_config
                )

                orchestrator = create_search_orchestrator(
                    kb_retriever=kb_retriever,
                    web_search_tool=web_tool,
                    llm_provider=llm,
                )

                result = await orchestrator.execute(
                    request.message,
                    user_id=str(current_user_id),
                    top_k=request.top_k,
                    enable_web=request.web_search,
                    enable_kb=True,
                )

                docs = result.kb_documents
                web_results = result.web_results
                answer = result.answer
                sources_from = result.fusion_sources
                
                # 调试日志
                logger.info(f"RAG 检索: query='{request.message}', top_k={request.top_k}, min_score={request.min_relevance_score}, 结果数={len(docs)}")
                for i, doc in enumerate(docs):
                    logger.info(f"  文档[{i}]: score={doc.metadata.get('relevance_score')}, content={doc.page_content[:100]}...")
                
                # 收集文档关联的图片
                doc_images = []
                seen_image_files = set()
                
                for doc in docs:
                    images_file = doc.metadata.get("images_file")
                    if images_file and images_file not in seen_image_files:
                        seen_image_files.add(images_file)
                        try:
                            from pathlib import Path
                            if Path(images_file).exists():
                                with open(images_file, 'r', encoding='utf-8') as f:
                                    img_data = json.load(f)
                                    images = img_data.get("images", [])
                                    # 限制每个文档最多取3张图片
                                    for img in images[:3]:
                                        doc_images.append({
                                            "base64": img.get("base64"),
                                            "source": img_data.get("source", "未知"),
                                            "page": img.get("page", 0),
                                            "width": img.get("width", 0),
                                            "height": img.get("height", 0)
                                        })
                                logger.info(f"  加载图片: {images_file}, 共 {len(images)} 张")
                        except Exception as e:
                            logger.warning(f"  加载图片失败: {images_file}, 错误: {e}")
                
                # 发送来源信息（文献 + 网络链接）
                if docs:
                    for doc in docs:
                        sources.append({
                            "content": doc.page_content[:300],
                            "source": doc.metadata.get("source", "未知来源"),
                            "relevance_score": doc.metadata.get("relevance_score"),
                            "type": "document",
                            "metadata": {
                                k: v for k, v in doc.metadata.items() 
                                if k not in ["page_content", "chroma_id"]
                            }
                        })
                
                # 添加网络搜索结果
                if web_results:
                    for result in web_results:
                        sources.append({
                            "content": result.snippet,
                            "source": result.title,
                            "url": result.url,
                            "type": "web",
                            "source_type": result.source_type,
                            "metadata": {}
                        })
                
                if sources:
                    yield f"data: {json.dumps({'type': 'sources', 'sources': sources}, ensure_ascii=False)}\n\n"
                
                # 如果有图片，使用视觉模型处理
                if doc_images:
                    logger.info(f"RAG 检测到 {len(doc_images)} 张文档图片，使用视觉模型")
                    yield f"data: {json.dumps({'type': 'status', 'message': f'正在分析 {len(doc_images)} 张文档图片...'}, ensure_ascii=False)}\n\n"
                    
                    try:
                        from src.core.vision_provider import create_vision_provider
                        import base64
                        
                        vision_provider = create_vision_provider(user_llm_config=user_llm_config)
                        
                        # 构建文本上下文
                        doc_context = "\n\n".join([
                            f"【文献{i+1}】{doc.metadata.get('source', '未知来源')}:\n{doc.page_content[:500]}"
                            for i, doc in enumerate(docs)
                        ])
                        
                        # 构建带图片的提示
                        vision_prompt = f"""用户提出了一个问题，已从知识库中检索到相关的文献内容和图片。

## 检索到的文献内容：
{doc_context}

## 用户问题：
{request.message}

请综合分析上述文献内容和图片信息，为用户提供全面、准确的解答。
- 如果图片中包含与问题相关的信息，请详细描述和解读
- 引用文献时用【文献X】标记"""
                        
                        # 限制图片数量（避免超出模型限制）
                        images_to_send = doc_images[:5]
                        
                        # 构建多图消息
                        from langchain_core.messages import HumanMessage, SystemMessage
                        
                        messages = [
                            SystemMessage(content="你是 Geo-Agent，一个 AI 智能助手，擅长分析各种图像和文档内容。")
                        ]
                        
                        # 构建包含多张图片的消息内容
                        content_parts = []
                        for i, img in enumerate(images_to_send):
                            content_parts.append({
                                "type": "image_url",
                                "image_url": {
                                    "url": img["base64"]  # 已经是 data:image/xxx;base64,xxx 格式
                                }
                            })
                        
                        content_parts.append({
                            "type": "text",
                            "text": vision_prompt
                        })
                        
                        messages.append(HumanMessage(content=content_parts))
                        
                        # 流式生成
                        async for chunk in vision_provider._llm.astream(messages):
                            if chunk.content:
                                full_response += chunk.content
                                yield f"data: {json.dumps({'type': 'content', 'content': chunk.content}, ensure_ascii=False)}\n\n"
                    
                    except Exception as e:
                        logger.error(f"视觉模型处理失败: {e}")
                        import traceback
                        logger.error(traceback.format_exc())
                        # 回退到普通文本模式
                        yield f"data: {json.dumps({'type': 'status', 'message': '图片分析失败，使用文本模式...'}, ensure_ascii=False)}\n\n"
                        if isinstance(answer, str):
                            full_response += answer
                            yield f"data: {json.dumps({'type': 'content', 'content': answer}, ensure_ascii=False)}\n\n"
                        else:
                            async for chunk in answer:
                                full_response += chunk
                                yield f"data: {json.dumps({'type': 'content', 'content': chunk}, ensure_ascii=False)}\n\n"
                else:
                    yield f"data: {json.dumps({'type': 'status', 'message': '正在生成回答...'}, ensure_ascii=False)}\n\n"

                    # 编排器返回的是完整字符串，按块发送模拟流式效果
                    if isinstance(answer, str):
                        chunk_size = 30
                        for i in range(0, len(answer), chunk_size):
                            chunk = answer[i:i + chunk_size]
                            full_response += chunk
                            yield f"data: {json.dumps({'type': 'content', 'content': chunk}, ensure_ascii=False)}\n\n"
                            await asyncio.sleep(0.01)
                    else:
                        async for chunk in answer:
                            full_response += chunk
                            yield f"data: {json.dumps({'type': 'content', 'content': chunk}, ensure_ascii=False)}\n\n"
            
            # 保存AI回复
            stream_db = get_session_local()()
            try:
                assistant_message = Message(
                    conversation_id=conversation_id,
                    role="assistant",
                    content=full_response,
                    message_metadata={
                        "sources": sources,
                        "mode": request.mode
                    }
                )
                stream_db.add(assistant_message)

                stream_db.query(Conversation).filter(
                    Conversation.id == conversation_id
                ).update(
                    {Conversation.updated_at: datetime.now()},
                    synchronize_session=False
                )

                search_history = SearchHistory(
                    user_id=current_user_id,
                    query=request.message,
                    result_count=len(sources),
                    search_type=request.mode,
                    response_time=int((time.time() - start_time) * 1000)
                )
                stream_db.add(search_history)
                stream_db.commit()
            except Exception:
                stream_db.rollback()
                raise
            finally:
                stream_db.close()
            
            # 发送完成信号
            execution_time = time.time() - start_time
            yield f"data: {json.dumps({'type': 'done', 'execution_time': execution_time}, ensure_ascii=False)}\n\n"
        
        except Exception as e:
            error_msg = str(e)
            logger.error("流式生成失败: %s", error_msg[:300])

            # 内容安全过滤 → 友好提示
            if "DataInspection" in error_msg or "inappropriate content" in error_msg.lower():
                yield f"data: {json.dumps({'type': 'error', 'message': '联网搜索返回的部分内容触发了模型安全策略，请尝试关闭联网搜索后重试，或更换其他模型'}, ensure_ascii=False)}\n\n"
            # 400 错误 → 可能是参数或内容问题
            elif "400" in error_msg or "Error code: 400" in error_msg:
                yield f"data: {json.dumps({'type': 'error', 'message': f'请求被模型拒绝（可能为内容策略限制），请尝试关闭联网搜索或简化问题。详情: {error_msg[:200]}'}, ensure_ascii=False)}\n\n"
            else:
                yield f"data: {json.dumps({'type': 'error', 'message': f'生成失败: {error_msg[:300]}'}, ensure_ascii=False)}\n\n"
    
    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )
