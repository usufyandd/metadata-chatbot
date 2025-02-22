from sqlalchemy.orm import Session
from fastapi import HTTPException, status, UploadFile, File
from uuid import UUID
from typing import List, Optional
from models.auth import UserRegistation
from tables import *
from utils.folders import *


class FoldersService:
    def __init__(self, db: Session):
        """Initialize the service with a database session."""
        self.db = db

    def create_folder(self, name: str, parent_id: Optional[UUID], tags: Optional[str], owner_id: UUID):
        """Create a new folder and save it to the database."""
        folder = Folder(
            name=name,
            parent_id=parent_id,
            tags=tags,
            owner_id=owner_id,
        )
        self.db.add(folder)
        self.db.commit()
        self.db.refresh(folder)
        return folder

    def update_folder(self, folder_id: UUID, name: Optional[str], parent_id: Optional[UUID], tags: Optional[str]):
        """Update an existing folder in the database."""
        folder = self.db.query(Folder).filter(Folder.id == folder_id).first()
        if not folder:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Folder not found")
        
        if name:
            folder.name = name
        if parent_id:
            folder.parent_id = parent_id
        if tags:
            folder.tags = tags

        self.db.commit()
        self.db.refresh(folder)
        return folder

    def get_folder(self, folder_id: UUID):
        """Retrieve a folder by its ID from the database."""
        folder = self.db.query(Folder).filter(Folder.id == folder_id).first()
        if not folder:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Folder not found")
        return folder

    def list_folders(self, skip: int = 0, limit: int = 10, owner_id: UUID = None) -> List[Folder]:
        """List folders for a specific user or all folders."""
        query = self.db.query(Folder).filter(Folder.owner_id == owner_id) if owner_id else self.db.query(Folder)
        return query.offset(skip).limit(limit).all()


def upload_file_to_folder(folder_id: UUID, file: UploadFile, db: Session, current_user):
    """Uploads a file to a specific subfolder by UUID and generates a summary, updating file count."""
    
    BASE_UPLOAD_DIR = "uploads"
    folder = db.query(Folder).filter(Folder.id == folder_id).first()
    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found.")

    if folder.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Permission denied.")

    # Ensure the folder exists
    folder_path = os.path.join(BASE_UPLOAD_DIR, str(folder_id))
    os.makedirs(folder_path, exist_ok=True)

    # Save file to folder
    file_path = os.path.join(folder_path, file.filename)
    with open(file_path, "wb") as buffer:
        buffer.write(file.file.read())

    # print("File saved to:", file_path)

    # Extract text from PDF or other file formats
    extracted_text = ""
    if file.filename.endswith(".pdf"):
        extracted_text = extract_text_from_pdf(file_path)
    elif file.filename.endswith(".doc"):
        extracted_text = extract_text_from_doc(file_path)
    else:
        encoding = detect_encoding(file_path)
        with open(file_path, "r", encoding=encoding, errors="replace") as f:
            extracted_text = f.read()
            
    # print("Extracted Text:", extracted_text)

    # Generate Summary & Description
    summary = summarize_text(extracted_text) if extracted_text else "No summary available."
    description = f"Document '{file.filename}' uploaded on {datetime.utcnow()}."

    # Add file metadata to DB
    new_file = Files(
        name=file.filename,
        path=file_path,
        folder_id=folder_id,
        owner_id=current_user.id
    )
    db.add(new_file)

    new_document = Document(
        filename=file.filename,
        storage_path=file_path,
        file_type=file.filename.split('.')[-1],
        folder_id=folder_id,
        owner_id=current_user.id,
        description=description,
        summary=summary,
        file_size=os.path.getsize(file_path),
        version=1.0
    )
    
    db.add(new_document)
    
    # Update folder's file count
    folder.file_count = db.query(Files).filter(Files.folder_id == folder_id).count()
    db.commit()
    db.refresh(folder)
    db.refresh(new_document)

    return {
        "message": "File uploaded successfully",
        "file_path": file_path,
        "file_count": folder.file_count
    }
    
    
def get_files_in_folder_service(folder_id: UUID, db: Session, current_user):
    """Fetches a list of files inside a folder given the folder_id."""

    # Check if the folder exists
    folder = db.query(Folder).filter(Folder.id == folder_id).first()
    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found.")
    
    # Check if the user owns the folder
    if folder.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Permission denied.")

    # Fetch all files inside the folder
    files = db.query(Document).filter(Document.folder_id == folder_id).all()

    if not files:
        raise HTTPException(status_code=404, detail="No files found in the folder.")

    return [
        {
            "id": file.id,
            "filename": file.filename,
            "file_type": file.file_type,
            "size": file.file_size,
            "uploaded_at": file.created_at,
            "summary": file.summary
        }
        for file in files
    ]


def get_project_metadata(query: str, db):
    """Retrieves metadata from all documents in the latest folder and updates the summary dynamically."""

    # Fetch the latest folder (most recently created/updated)
    folder = db.query(Folder).order_by(Folder.created_at.desc()).first()
    if not folder:
        raise HTTPException(status_code=404, detail="No folder found")

    # Count the total number of files in this folder
    total_files = db.query(Document).filter(Document.folder_id == folder.id).count()

    # Fetch all documents in the latest folder
    documents = db.query(Document).filter(Document.folder_id == folder.id).all()

    if not documents:
        raise HTTPException(status_code=404, detail="No documents found in the folder")

    extracted_text = ""
    
    for document in documents:
        if document.storage_path.endswith(".pdf"):
            extracted_text += extract_text_from_pdf(document.storage_path) + "\n"
        elif document.storage_path.endswith(".doc"):
            extracted_text += extract_text_from_doc(document.storage_path) + "\n"
        else:
            encoding = detect_encoding(document.storage_path)
            try:
                with open(document.storage_path, "r", encoding=encoding) as f:
                    extracted_text += f.read() + "\n"
            except UnicodeDecodeError:
                with open(document.storage_path, "r", encoding="utf-8", errors="replace") as f:
                    extracted_text += f.read() + "\n"

    if not extracted_text.strip():
        raise HTTPException(status_code=400, detail="No valid text extracted from the documents")

    # Process text using LangChain's text splitter
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    chunks = text_splitter.split_text(extracted_text)

    extracted_dates = extract_dates(extracted_text)

    # Gemini Prompt for Information Extraction
    prompt = f"""
    Based on the following query: {query}

    Extract the following information from the project documents:
    - Name of the project
    - Name of the client
    - Managing Director
    - Summarize the project based on the content of all files in the folder
    - Count the number of files in the folder ({total_files} files detected)
    - Identify only one starting project date. If multiple dates are detected, choose the earliest date.

    Document Content:

    {' '.join(chunks[:5])}  # Take the first 5 chunks to avoid exceeding token limits
    Provide the response in the following structured format:
    ```
    Name of the project: [Project Name]
    Name of the client: [Client Name]
    Managing Director: [Managing Director's Name]
    Project Summary: [Summary based on all files]
    Number of files: {total_files}
    Date of the project
    ```
    """

    return call_gemini(prompt)
