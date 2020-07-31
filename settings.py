import sqlalchemy
from sqlalchemy.orm import sessionmaker

db_engine = sqlalchemy.create_engine('sqlite:///.notebook/catalog.sqlite', convert_unicode=True)
Session = sessionmaker(bind=db_engine)
