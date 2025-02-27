from sqlalchemy.orm import Session
from fastapi import HTTPException, status, UploadFile, File
from uuid import UUID
from typing import List, Optional
from models.auth import UserRegistation
from collections import defaultdict
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



def get_project_metadata(query: str, db: Session):
    """Dynamically searches for documents related to the query across all folders."""

    # Extract query keywords
    query_keywords = extract_keywords(query)

    # Fetch all folders
    folders = db.query(Folder).all()

    if not folders:
        raise HTTPException(status_code=404, detail="No folders found")

    # Initialize result containers
    total_documents = 0
    folder_document_count = defaultdict(int)
    project_documents = defaultdict(list)
    extracted_text = ""
    matched_folder_name = False
    query_lower = query.lower()  # Convert query to lowercase

    for folder in folders:
        folder_name_lower = folder.name.lower()  # Convert folder name to lowercase

        # Match if query contains folder name directly OR any keyword matches
        if folder_name_lower in query_lower or any(keyword.lower() in folder_name_lower for keyword in query_keywords):
            matched_folder_name = True


        documents = db.query(Document).filter(Document.folder_id == folder.id).all()

        if not documents:
            continue

        for document in documents:
            text = ""

            # Handle different file types
            file_path = document.storage_path
            file_ext = os.path.splitext(file_path)[1].lower()

            try:
                if file_ext == ".pdf":
                    text = extract_text_from_pdf(file_path)
                elif file_ext == ".doc":
                    text = extract_text_from_doc(file_path)
                else:
                    encoding = detect_encoding(file_path)
                    with open(file_path, "r", encoding=encoding, errors="replace") as f:
                        text = f.read()
            except Exception as e:
                print(f"Error processing file {file_path}: {e}")
                continue  # Skip the file if there's an error

            if not text.strip():
                continue

            # Extract keywords and check relevance
            doc_keywords = extract_keywords(text)
            if query_keywords & doc_keywords or matched_folder_name:
                project_documents[folder.name].append((document.filename, text[:500]))  # Store preview of text
                folder_document_count[folder.name] += 1
                total_documents += 1
                extracted_text += text + "\n"
    # print("query_keyword :", query_keywords)
    # print("doc_keyword :", doc_keywords)
    print("Matched_folder_name : ",matched_folder_name)
    print(f"Query Keywords: {query_keywords}")
    print(f"Document Keywords: {doc_keywords}")

    # print("Extracted_text : ", extracted_text)
    print("Total Document : ", total_documents)
    if total_documents == 0:
        return {"message": f"No relevant documents found for query: {query}"}

    # Determine response format **ONLY IF FOLDER NAME MATCHES QUERY**
    if matched_folder_name:
        prompt = f"""
        Based on the following query: {query}

        Extract relevant information from project documents, such as:
        - Name of the project
        - Name of the client
        - Project Manager
        - Summary of the project
        - Number of letters found
        - Dates of the letters (if applicable)

        Document Content:
        {extracted_text[:10000]}  # Limiting to first 10000 chars for efficiency

        Provide the response in this structured format:

        Name of the project: [Extracted Project Name]
        Name of the client: [Extracted Client Name]
        Project Manager: [Extracted Manager]
        Summary: [Detailed Summarized Content]
        Total Letters: {total_documents}
        Date of Letters: [List of Dates]
        """

    else:  # If folder name does NOT match, assume dispute letter structure
        prompt = f"""
        Extract information about related letters, such as:
        - How many letters exist
        - Name of the Folder
        - Summary of each letter
        - Date of each letter
        - Sender and Receiver details

        Document Content:
        {extracted_text[:5000]}  # Limiting to first 5000 chars for efficiency

        Provide the response in this structured format:

        Total Letters: {total_documents}
        Folder Name: {folder.name}
        Letters:
        - [Letter 1 Summary, Date, Sender, Receiver]
        - [Letter 2 Summary, Date, Sender, Receiver]
        """

    return call_gemini(prompt)
