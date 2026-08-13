"""会话管理路由。"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from src.api.deps import get_db
from src.data.repositories import ConversationRepository, MessageRepository
from src.data.schemas.conversation import (
    ConversationCreate,
    ConversationDetail,
    ConversationListResponse,
    ConversationResponse,
    ConversationUpdate,
)
from src.data.schemas.message import MessageListResponse, MessageResponse
from src.data.services import ConversationService

router = APIRouter(prefix="/conversations", tags=["会话管理"])


@router.post("/", response_model=ConversationResponse, status_code=201)
def create_conversation(body: ConversationCreate, db: Session = Depends(get_db)):
    """创建会话。"""
    service = ConversationService(db)
    created = service.create_conversation(body)
    return created


@router.get("/", response_model=ConversationListResponse)
def list_conversations(
    project_id: int | None = Query(default=None, description="按项目筛选"),
    status: int | None = Query(default=1, description="状态筛选: 1-正常, 0-删除"),
    page: int = Query(default=1, ge=1, description="页码"),
    page_size: int = Query(default=20, ge=1, le=100, description="每页数量"),
    db: Session = Depends(get_db),
):
    """查询会话列表（分页）。"""
    repo = ConversationRepository(db)
    conversations = repo.list_by_project(project_id, status)

    total = len(conversations)
    start = (page - 1) * page_size
    items = conversations[start : start + page_size]
    return ConversationListResponse(
        items=[ConversationResponse.model_validate(c) for c in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{conversation_id}", response_model=ConversationDetail)
def get_conversation(conversation_id: int, db: Session = Depends(get_db)):
    """获取会话详情（含消息列表）。"""
    repo = ConversationRepository(db)
    conversation = repo.get_with_messages(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="会话不存在")

    detail = ConversationDetail.model_validate(conversation)
    detail.messages = sorted(detail.messages, key=lambda m: (m.created_at, m.id))
    return detail


@router.get("/{conversation_id}/messages", response_model=MessageListResponse)
def list_messages(conversation_id: int, db: Session = Depends(get_db)):
    """获取会话的消息列表（按时间升序）。"""
    conv_repo = ConversationRepository(db)
    if conv_repo.get_by_id(conversation_id) is None:
        raise HTTPException(status_code=404, detail="会话不存在")

    msg_repo = MessageRepository(db)
    messages = msg_repo.list_by_conversation(conversation_id)
    return MessageListResponse(
        items=[MessageResponse.model_validate(m) for m in messages],
        total=len(messages),
    )


@router.put("/{conversation_id}", response_model=ConversationResponse)
def update_conversation(conversation_id: int, body: ConversationUpdate, db: Session = Depends(get_db)):
    """更新会话（重命名 / 改模式 / 改状态）。"""
    repo = ConversationRepository(db)
    conversation = repo.get_by_id(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="会话不存在")

    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(conversation, field, value)
    updated = repo.update_entity(conversation)
    return updated


@router.delete("/{conversation_id}", status_code=204)
def delete_conversation(conversation_id: int, db: Session = Depends(get_db)):
    """删除会话及其关联的消息。"""
    repo = ConversationRepository(db)
    success = repo.delete_by_id(conversation_id)
    if not success:
        raise HTTPException(status_code=404, detail="会话不存在")
