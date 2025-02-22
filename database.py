from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from settings import settings
from tables import *


DATABASE_URL = "{db_driver}://{db_user}:{db_password}@{db_instance}:{db_port}/{db_database}".format(
    db_driver=settings.db_driver,
    db_user=settings.db_user,
    db_password=settings.db_password,
    db_instance=settings.db_instance,
    db_port=settings.db_port,
    db_database=settings.db_database,
)


def get_engine():
    return create_engine(DATABASE_URL, client_encoding="utf8")


engine = get_engine()

Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_session():
    session = Session()
    try:
        yield session
    finally:
        session.close()
        
def get_db():
    db = Session()
    try:
        yield db
    finally:
        db.close()
