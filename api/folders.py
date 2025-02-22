from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from typing import List
import uuid
from uuid import UUID
from services.folders import FoldersService, upload_file_to_folder, get_project_metadata, get_files_in_folder_service
from models.folders import FolderCreate, FolderUpdate, FolderResponse
from tables import Folder
from database import get_session
from models.auth import UserRegistation
from tables import User
from fastapi import Depends
from core.security import get_current_user
from database import get_db


router = APIRouter(
    prefix="/api/folders",
    tags=["Folders"],
)

@router.post("/", response_model=FolderResponse)
def create_folder(
    folder_data: FolderCreate,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Create a new folder."""
    folders_service = FoldersService(db)

    parent_folder = None
    if folder_data.parent_id:
        try:
            parent_folder = db.query(Folder).filter(Folder.id == folder_data.parent_id).first()
            if not parent_folder:
                parent_folder_id = uuid.uuid4()
                parent_folder = folders_service.create_folder(
                    name=f"Parent folder {parent_folder_id}",
                    parent_id=None,
                    owner_id=current_user.id,
                    tags=None
                )
                db.commit()
                db.refresh(parent_folder)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid parent_id format. Must be a valid UUID.")

    new_folder = folders_service.create_folder(
        name=folder_data.name,
        parent_id=parent_folder.id if parent_folder else None,
        owner_id=current_user.id,
        tags=folder_data.tags or None
    )
    if parent_folder:
        parent_folder.folder_count += 1
        db.commit()
        db.refresh(parent_folder)
    return new_folder


@router.put("/{folder_id}", response_model=FolderResponse)
def update_folder(
    folder_id: UUID,
    folder_data: FolderUpdate,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Update an existing folder."""
    folders_service = FoldersService(db)
    folder = folders_service.update_folder(
        folder_id=folder_id,
        name=folder_data.name,
        parent_id=folder_data.parent_id,
        tags=folder_data.tags,
    )
    return folder

@router.get("/", response_model=List[FolderResponse])
def list_folders(
    skip: int = 0,
    limit: int = 10,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """List all folders for the current user."""
    folders_service = FoldersService(db)
    folders = folders_service.list_folders(skip=skip, limit=limit, owner_id=current_user.id)
    return folders


@router.get("/{folder_id}", response_model=FolderResponse)
def get_folder(
    folder_id: UUID,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Get details of a specific folder."""
    folders_service = FoldersService(db)
    folder = folders_service.get_folder(folder_id=folder_id)
    return folder


@router.post("/upload/{folder_id}")
def upload_file(
    folder_id: UUID,
    file: UploadFile = File(...),
    db: Session = Depends(get_session),
    current_user: UserRegistation = Depends(get_current_user)
):
    """Upload a file to a specific subfolder by UUID."""
    return upload_file_to_folder(folder_id, file, db, current_user)

@router.get("/{folder_id}/files", response_model=List[dict])
def get_files_in_folder(folder_id: UUID, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    """API endpoint to retrieve files inside a folder by providing folder_id."""
    return get_files_in_folder_service(folder_id, db, current_user)


@router.post("/query-metadata")
def query_metadata(query: str, db: Session = Depends(get_db)):
    try:
        metadata = get_project_metadata(query, db)
        return {"response": metadata}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
