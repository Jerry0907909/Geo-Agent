"""聊天相关API路由

提供会话管理、消息发送、智能对话等接口。
"""

import time
import json
import logging
from typing import Optional, List, AsyncGenerator, Any

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
from src.agent.runtime import create_agent_runtime
from src.agent.schemas import AgentConstraints, AgentSessionState
from src.rag.chain import create_rag_chain
from src.rag.unified_retrieval import create_unified_retrieval_service
from src.core.llm_provider import create_llm_provider
from src.core.prompts import (
    get_chat_prompt,
    get_vision_prompt,
    build_chat_prompt_with_context,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["聊天"])


def _build_agent_constraints(request: ChatRequest) -> AgentConstraints:
    """将聊天请求收敛为 Agent 运行约束。"""
    return AgentConstraints(
        max_iterations=8,
        max_failures=2,
        timeout_seconds=300,
        top_k=request.top_k,
        allow_web_search=request.web_search,
        read_only_tools=True,
        retrieval_mode=request.retrieval_mode if request.web_search else "local",
    )


def _serialize_agent_sources(sources: List[dict[str, Any]]) -> List[dict[str, Any]]:
    serialized = []
    for source in sources:
        serialized.append(
            {
                "content": source.get("content", ""),
                "source": source.get("source", "未知来源"),
                "relevance_score": source.get("relevance_score"),
                "url": source.get("url"),
                "type": source.get("type"),
                "source_type": source.get("source_type"),
                "metadata": source.get("metadata", {}),
            }
        )
    return serialized


def _serialize_agent_steps(state: AgentSessionState) -> List[dict[str, Any]]:
    return [
        {
            "step_id": step.step_id,
            "title": step.title,
            "goal": step.goal,
            "tool_name": step.tool_name,
            "tool_input": step.tool_input,
            "expected_output": step.expected_output,
            "reasoning_summary": step.reasoning_summary,
            "status": step.status,
            "observation": step.observation,
            "sources": _serialize_agent_sources(step.sources),
            "latency_ms": step.latency_ms,
        }
        for step in state.steps
    ]


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

    conversation_id = conversation.id
    user_id = current_user.id
    request_message = request.message
    request_mode = request.mode
    request_top_k = request.top_k
    request_min_relevance_score = request.min_relevance_score
    request_web_search = request.web_search
    request_image_base64 = request.image_base64
    
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
        
        if request.mode == "agent":
            runtime = create_agent_runtime()
            state = runtime.run_task(
                task=request.message,
                conversation_id=conversation.id,
                constraints=_build_agent_constraints(request),
            )

            if state.status != "completed":
                raise RuntimeError(state.error.message if state.error else "Agent 执行失败")

            answer = state.final_answer or "未生成最终答案"
            sources = _serialize_agent_sources(state.sources)
            reasoning_steps = _serialize_agent_steps(state)
        elif request.mode == "rag":
            # RAG模式 - 文献检索增强生成
            rag_chain = create_rag_chain()
            result = rag_chain.query(
                request.message,
                top_k=request.top_k,
                retrieval_mode=request.retrieval_mode,
                min_relevance_score=request.min_relevance_score,
            )
            answer = result.answer
            
            # 提取来源
            if request.return_sources and result.sources:
                for source in result.sources:
                    sources.append({
                        "content": str(source.get("content", ""))[:300],
                        "source": source.get("source", "未知来源"),
                        "relevance_score": source.get("relevance_score"),
                        "url": source.get("url"),
                        "type": source.get("type"),
                        "source_type": source.get("source_type"),
                        "metadata": source.get("metadata", {}),
                    })
        
        else:
            # 普通对话模式 - 直接使用LLM
            llm = create_llm_provider()
            
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
        
        if request.mode == "agent":
            runtime = create_agent_runtime()
            state = runtime.run_task(
                task=request.message,
                conversation_id=None,
                constraints=_build_agent_constraints(request),
            )
            if state.status != "completed":
                raise RuntimeError(state.error.message if state.error else "Agent 执行失败")

            answer = state.final_answer or "未生成最终答案"
            sources = _serialize_agent_sources(state.sources)
            reasoning_steps = _serialize_agent_steps(state)
        elif request.mode == "rag":
            # RAG模式
            rag_chain = create_rag_chain()
            result = rag_chain.query(
                request.message,
                top_k=request.top_k,
                retrieval_mode=request.retrieval_mode,
                min_relevance_score=request.min_relevance_score,
            )
            answer = result.answer
            
            if request.return_sources and result.sources:
                for source in result.sources:
                    sources.append({
                        "content": str(source.get("content", ""))[:300],
                        "source": source.get("source", "未知来源"),
                        "relevance_score": source.get("relevance_score"),
                        "url": source.get("url"),
                        "type": source.get("type"),
                        "source_type": source.get("source_type"),
                        "metadata": source.get("metadata", {}),
                    })
        
        else:
            # 普通对话模式
            llm = create_llm_provider()
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
):
    """生成推荐的后续问题
    
    基于用户问题和AI回答，生成相关的后续问题建议。
    """
    try:
        llm = create_llm_provider()
        
        prompt = f"""基于以下对话，生成3个用户可能感兴趣的后续问题。
问题要简洁、具体，与原问题相关但有所延伸。

用户问题：{request.question}

AI回答：{request.answer[:500]}...

请直接输出3个问题，每行一个，不要编号，不要其他内容："""
        
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
        title = request.message[:50] + ("..." if len(request.message) > 50 else "")
        conversation = Conversation(
            user_id=current_user.id,
            title=title
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

    conversation_id = conversation.id
    user_id = current_user.id
    request_message = request.message
    request_mode = request.mode
    request_top_k = request.top_k
    request_min_relevance_score = request.min_relevance_score
    request_web_search = request.web_search
    request_image_base64 = request.image_base64
    
    async def generate_stream() -> AsyncGenerator[str, None]:
        """生成SSE流"""
        start_time = time.time()
        full_response = ""
        sources = []
        
        try:
            # 发送会话信息
            yield f"data: {json.dumps({'type': 'info', 'conversation_id': conversation_id}, ensure_ascii=False)}\n\n"
            
            if request_mode == "chat":
                # 普通对话模式 - 流式输出
                
                # 检查是否有图像
                has_image = request_image_base64 is not None and len(request_image_base64) > 0
                
                if has_image:
                    # 使用视觉模型处理图像
                    logger.info(f"[Chat Mode] 检测到图像，使用视觉模型")
                    yield f"data: {json.dumps({'type': 'status', 'message': '正在分析图像...'}, ensure_ascii=False)}\n\n"
                    
                    try:
                        from src.core.vision_provider import create_vision_provider
                        import base64
                        
                        vision_provider = create_vision_provider()
                        
                        # 解码图像
                        image_data = base64.b64decode(request_image_base64)
                        
                        # 获取历史上下文
                        history_messages = (
                            db.query(Message)
                            .filter(Message.conversation_id == conversation_id)
                            .order_by(Message.created_at.desc())
                            .limit(6)
                            .all()
                        )[::-1]
                        
                        history = [
                            {"role": msg.role, "content": msg.content}
                            for msg in history_messages[:-1]
                        ]
                        
                        system_prompt = get_vision_prompt()
                        
                        yield f"data: {json.dumps({'type': 'status', 'message': '正在生成回答...'}, ensure_ascii=False)}\n\n"
                        
                        # 流式生成
                        async for chunk in vision_provider.astream_analyze_image(
                            image_data=image_data,
                            question=request_message,
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
                    llm = create_llm_provider()
                    
                    # WebSearch 增强
                    web_context = ""
                    logger.info(f"[Chat Mode] web_search={request_web_search}")
                    
                    if request_web_search:
                        logger.info(f"[Chat Mode] 开始 WebSearch: query='{request_message}'")
                        yield f"data: {json.dumps({'type': 'status', 'message': '正在搜索网络信息...'}, ensure_ascii=False)}\n\n"
                        try:
                            from src.tools.web_search import create_web_search_tool
                            web_tool = create_web_search_tool()
                            web_results = web_tool.search(request_message, max_results=3)
                            
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
                    
                    # 获取历史上下文
                    history_messages = (
                        db.query(Message)
                        .filter(Message.conversation_id == conversation_id)
                        .order_by(Message.created_at.desc())
                        .limit(10)
                        .all()
                    )[::-1]
                    
                    # 使用默认提示词
                    system_prompt = get_chat_prompt()
                    llm = create_llm_provider()
                    
                    if web_context:
                        system_prompt += f"\n\n参考网络信息：\n{web_context}\n\n请基于上述网络信息回答问题，并用【来源X】标注引用。"
                    
                    context = "\n".join([
                        f"{msg.role}: {msg.content}" 
                        for msg in history_messages[:-1]
                    ])
                    
                    if context:
                        prompt = f"{system_prompt}\n\n历史对话:\n{context}\n\nuser: {request_message}\nassistant:"
                    else:
                        prompt = f"{system_prompt}\n\nuser: {request_message}\nassistant:"
                    
                    yield f"data: {json.dumps({'type': 'status', 'message': '正在生成回答...'}, ensure_ascii=False)}\n\n"
                    
                    # 流式生成
                    async for chunk in llm.astream_generate(prompt):
                        full_response += chunk
                        yield f"data: {json.dumps({'type': 'content', 'content': chunk}, ensure_ascii=False)}\n\n"
            
            elif request_mode == "rag":
                # RAG模式 - 使用统一检索服务
                yield f"data: {json.dumps({'type': 'status', 'message': '正在检索文献...'}, ensure_ascii=False)}\n\n"

                retrieval_mode = request.retrieval_mode
                if request_web_search and retrieval_mode == "local":
                    retrieval_mode = "hybrid"

                retrieval_service = create_unified_retrieval_service()
                answer, retrieval = retrieval_service.answer(
                    query=request_message,
                    top_k=request_top_k,
                    retrieval_mode=retrieval_mode,
                    min_relevance_score=request_min_relevance_score,
                )
                docs = retrieval.documents
                logger.info(
                    "RAG 检索: query='%s', mode=%s, top_k=%s, min_score=%s, local_docs=%s, total_sources=%s",
                    request_message,
                    retrieval_mode,
                    request_top_k,
                    request_min_relevance_score,
                    len(docs),
                    len(retrieval.sources),
                )
                
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
                
                # 发送来源信息（本地 / 外部 / 混合）
                sources = _serialize_agent_sources(retrieval.sources)
                
                if sources:
                    yield f"data: {json.dumps({'type': 'sources', 'sources': sources}, ensure_ascii=False)}\n\n"
                
                # 如果有图片，使用视觉模型处理
                if doc_images:
                    logger.info(f"RAG 检测到 {len(doc_images)} 张文档图片，使用视觉模型")
                    yield f"data: {json.dumps({'type': 'status', 'message': f'正在分析 {len(doc_images)} 张文档图片...'}, ensure_ascii=False)}\n\n"
                    
                    try:
                        from src.core.vision_provider import create_vision_provider
                        import base64
                        
                        vision_provider = create_vision_provider()
                        
                        # 构建文本上下文
                        doc_context = "\n\n".join([
                            f"【文献{i+1}】{doc.metadata.get('source', '未知来源')}:\n{doc.page_content[:500]}"
                            for i, doc in enumerate(docs)
                        ])
                        
                        # 构建带图片的提示
                        vision_prompt = f"""你是一名专业的地质学文献分析助手。用户提出了一个问题，我已经从知识库中检索到了相关的文献内容和图片。

## 检索到的文献内容：
{doc_context}

## 用户问题：
{request_message}

请综合分析上述文献内容和图片信息，为用户提供全面、准确的解答。
- 如果图片中包含与问题相关的图表、地图、数据等，请详细描述和解读
- 引用文献时用【文献X】标记
- 如果图片信息与文献内容相互印证，请指出关联"""
                        
                        # 限制图片数量（避免超出模型限制）
                        images_to_send = doc_images[:5]
                        
                        # 构建多图消息
                        from langchain_core.messages import HumanMessage, SystemMessage
                        
                        messages = [
                            SystemMessage(content="你是一名专业的地质学文献分析助手，擅长分析地质图表、地图和科研数据。")
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
                        async for chunk in answer_stream:
                            full_response += chunk
                            yield f"data: {json.dumps({'type': 'content', 'content': chunk}, ensure_ascii=False)}\n\n"
                else:
                    yield f"data: {json.dumps({'type': 'status', 'message': '正在生成回答...'}, ensure_ascii=False)}\n\n"
                    
                sources = _serialize_agent_sources(retrieval.sources)
                if sources:
                    yield f"data: {json.dumps({'type': 'sources', 'sources': sources}, ensure_ascii=False)}\n\n"
                full_response = answer
                yield f"data: {json.dumps({'type': 'content', 'content': answer}, ensure_ascii=False)}\n\n"
            elif request_mode == "agent":
                runtime = create_agent_runtime()
                state = runtime.create_run_state(
                    task=request_message,
                    conversation_id=conversation_id,
                    constraints=_build_agent_constraints(request),
                )

                for event in runtime.iter_state_events(state):
                    event_payload = {
                        "type": event.type.value,
                        "run_id": event.run_id,
                        "timestamp": event.timestamp,
                        **event.payload,
                    }

                    if event.type.value == "info":
                        status_value = event.payload.get("status")
                        if status_value == "planning":
                            yield f"data: {json.dumps({'type': 'status', 'message': '正在规划执行步骤...'}, ensure_ascii=False)}\n\n"
                        elif status_value == "running":
                            yield f"data: {json.dumps({'type': 'status', 'message': '正在执行工具...'}, ensure_ascii=False)}\n\n"
                        elif status_value == "cancelled":
                            yield f"data: {json.dumps({'type': 'status', 'message': '任务已取消'}, ensure_ascii=False)}\n\n"
                        yield f"data: {json.dumps(event_payload, ensure_ascii=False)}\n\n"
                        continue

                    if event.type.value == "route":
                        yield f"data: {json.dumps({'type': 'status', 'message': event.payload.get('summary', '正在分析任务类型...')}, ensure_ascii=False)}\n\n"
                        yield f"data: {json.dumps(event_payload, ensure_ascii=False)}\n\n"
                        continue

                    if event.type.value in {"plan", "thought", "step_start", "tool_call", "tool_result", "replan", "content"}:
                        yield f"data: {json.dumps(event_payload, ensure_ascii=False)}\n\n"
                        if event.type.value == "tool_result" and event.payload.get("sources"):
                            sources = _serialize_agent_sources(event.payload.get("sources", []))
                        if event.type.value == "content":
                            full_response += event.payload.get("content", "")
                        continue

                    if event.type.value == "final":
                        full_response = event.payload.get("final_answer", "")
                        sources = _serialize_agent_sources(event.payload.get("sources", []))
                        if sources:
                            yield f"data: {json.dumps({'type': 'sources', 'sources': sources}, ensure_ascii=False)}\n\n"
                        yield f"data: {json.dumps(event_payload, ensure_ascii=False)}\n\n"
                        if full_response:
                            yield f"data: {json.dumps({'type': 'content', 'content': full_response}, ensure_ascii=False)}\n\n"
                        continue

                    if event.type.value == "error":
                        raise RuntimeError(event.payload.get("message", "Agent 执行失败"))

            # 保存AI回复
            assistant_message = Message(
                conversation_id=conversation_id,
                role="assistant",
                content=full_response,
                message_metadata={
                    "sources": sources,
                    "mode": request_mode,
                    "reasoning_steps": _serialize_agent_steps(state) if request_mode == "agent" else [],
                }
            )
            db.add(assistant_message)
            
            # 更新会话时间
            from datetime import datetime
            conversation_row = db.query(Conversation).filter(Conversation.id == conversation_id).first()
            if conversation_row:
                conversation_row.updated_at = datetime.now()
            
            # 记录搜索历史
            search_history = SearchHistory(
                user_id=user_id,
                query=request_message,
                result_count=len(sources),
                search_type=request_mode,
                response_time=int((time.time() - start_time) * 1000)
            )
            db.add(search_history)
            db.commit()
            
            # 发送完成信号
            execution_time = time.time() - start_time
            yield f"data: {json.dumps({'type': 'done', 'execution_time': execution_time}, ensure_ascii=False)}\n\n"
        
        except Exception as e:
            logger.error(f"流式生成失败: {e}")
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)}, ensure_ascii=False)}\n\n"
    
    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )
