from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from core.auth import get_current_user
from handlers.admin_handler import check_super_admin
from db import blog_repository

router = APIRouter(tags=["blogs"])

class BlogCreateRequest(BaseModel):
    title: str
    content: str
    summary: Optional[str] = None
    author: Optional[str] = "BlinkBot Team"
    read_time: Optional[str] = "5 min read"
    cover_image: Optional[str] = None
    is_published: Optional[bool] = True

class BlogUpdateRequest(BaseModel):
    title: str
    content: str
    summary: Optional[str] = None
    author: Optional[str] = "BlinkBot Team"
    read_time: Optional[str] = "5 min read"
    cover_image: Optional[str] = None
    is_published: Optional[bool] = True

# --- Public Endpoints ---

@router.get("/api/blogs")
async def get_published_blogs():
    """
    Get all published blogs. Used by the frontend client.
    """
    try:
        return await blog_repository.get_all_blogs(only_published=True)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/blogs/{blog_id}")
async def get_single_blog(blog_id: str):
    """
    Get a single blog post by its ID.
    """
    try:
        blog = await blog_repository.get_blog_by_id(blog_id)
        if not blog:
            raise HTTPException(status_code=404, detail="Blog post not found")
        return blog
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- Admin Endpoints (Super Admin Only) ---

@router.get("/admin/blogs")
async def get_all_blogs_admin(current_user: dict = Depends(get_current_user)):
    """
    Get all blogs (including unpublished) for admin management.
    """
    user_id = current_user["sub"]
    await check_super_admin(user_id)
    try:
        return await blog_repository.get_all_blogs(only_published=False)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/admin/blogs")
async def create_new_blog(req: BlogCreateRequest, current_user: dict = Depends(get_current_user)):
    """
    Create a new blog post.
    """
    user_id = current_user["sub"]
    await check_super_admin(user_id)
    try:
        blog = await blog_repository.create_blog(
            title=req.title,
            content=req.content,
            summary=req.summary,
            author=req.author,
            read_time=req.read_time,
            cover_image=req.cover_image,
            is_published=req.is_published
        )
        return blog
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/admin/blogs/{blog_id}")
async def update_existing_blog(blog_id: str, req: BlogUpdateRequest, current_user: dict = Depends(get_current_user)):
    """
    Update an existing blog post.
    """
    user_id = current_user["sub"]
    await check_super_admin(user_id)
    try:
        updated = await blog_repository.update_blog(
            blog_id=blog_id,
            title=req.title,
            content=req.content,
            summary=req.summary,
            author=req.author,
            read_time=req.read_time,
            cover_image=req.cover_image,
            is_published=req.is_published
        )
        if not updated:
            raise HTTPException(status_code=404, detail="Blog post not found")
        return updated
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/admin/blogs/{blog_id}")
async def delete_existing_blog(blog_id: str, current_user: dict = Depends(get_current_user)):
    """
    Delete a blog post.
    """
    user_id = current_user["sub"]
    await check_super_admin(user_id)
    try:
        deleted = await blog_repository.delete_blog(blog_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Blog post not found")
        return {"status": "success", "message": "Blog post deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
