from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker
from chatbot_app.startup import CONNECTION_STRING
from sqlalchemy.engine.url import make_url

url = make_url(CONNECTION_STRING)

connect_args = {}
if url.drivername.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(CONNECTION_STRING, connect_args=connect_args)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()
