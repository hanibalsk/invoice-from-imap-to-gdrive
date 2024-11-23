from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.exc import SQLAlchemyError
from contextlib import contextmanager

Base = declarative_base()

class ImportedEmail(Base):
    __tablename__ = 'imported_emails'

    id = Column(Integer, primary_key=True, autoincrement=True)
    imap_account = Column(String, nullable=False)
    subject = Column(String, nullable=False)
    sender = Column(String, nullable=False)
    sender_organisation = Column(String, nullable=True)
    date = Column(DateTime, nullable=False)
    is_spam = Column(Boolean, default=False)
    has_attachment = Column(Boolean, default=False)
    attachment_path = Column(String, nullable=True)
    body = Column(Text, nullable=True)
    return_path = Column(String, nullable=True)
    envelope_to = Column(String, nullable=True)
    delivery_date = Column(DateTime, nullable=True)
    received_from = Column(String, nullable=True)
    dkim_signature = Column(Text, nullable=True)
    spam_status = Column(String, nullable=True)
    spam_report = Column(Text, nullable=True)
    organization_name = Column(Text, nullable=True)
    is_invoice = Column(Boolean, default=False)

    @classmethod
    def save_to_database(cls, session, **kwargs):
        try:
            email_instance = ImportedEmail(**kwargs)
            session.add(email_instance)
            session.commit()
        except SQLAlchemyError as e:
            session.rollback()
            raise e

    @classmethod
    def get_by_id(cls, session, email_id):
        try:
            return session.query(cls).filter(cls.id == email_id).first()
        except SQLAlchemyError as e:
            session.rollback()
            raise e

    @classmethod
    def get_all(cls, session):
        try:
            return session.query(cls).all()
        except SQLAlchemyError as e:
            session.rollback()
            raise e

    @classmethod
    def update(cls, session, email_id, **kwargs):
        try:
            email = session.query(cls).filter(cls.id == email_id).first()
            if email:
                for key, value in kwargs.items():
                    if hasattr(email, key):
                        setattr(email, key, value)
                session.commit()
        except SQLAlchemyError as e:
            session.rollback()
            raise e

    @classmethod
    def delete(cls, session, email_id):
        try:
            email = session.query(cls).filter(cls.id == email_id).first()
            if email:
                session.delete(email)
                session.commit()
        except SQLAlchemyError as e:
            session.rollback()
            raise e

    @classmethod
    def filter_emails(cls, session, imap_account=None, date=None, has_attachment=None, is_spam=None):
        try:
            query = session.query(cls)
            if imap_account is not None:
                query = query.filter(cls.imap_account == imap_account)
            if date is not None:
                query = query.filter(cls.date == date)
            if has_attachment is not None:
                query = query.filter(cls.has_attachment == has_attachment)
            if is_spam is not None:
                query = query.filter(cls.is_spam == is_spam)
            return query.all()
        except SQLAlchemyError as e:
            session.rollback()
            raise e


class Db:
    def __init__(self, database_url='sqlite:///emails.db'):
        self.engine = create_engine(database_url)
        Base.metadata.create_all(self.engine)
        self.Session = scoped_session(sessionmaker(bind=self.engine))

    @contextmanager
    def get_session(self):
        session = self.Session()
        try:
            yield session
        finally:
            session.close()