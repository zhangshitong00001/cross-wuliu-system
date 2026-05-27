"""
基础数据模型
"""
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Column, Integer, DateTime, String, Text, func

db = SQLAlchemy()


class BaseModel:
    """基础模型类，提供通用字段和方法"""
    id = Column(Integer, primary_key=True, autoincrement=True)
    created_at = Column(DateTime, default=datetime.now, comment='创建时间')
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')
    is_deleted = Column(Integer, default=0, comment='是否删除：0-否，1-是')
    remark = Column(Text, nullable=True, comment='备注')

    def save(self):
        db.session.add(self)
        db.session.commit()
        return self

    def delete(self):
        self.is_deleted = 1
        db.session.commit()

    def to_dict(self, exclude=None):
        """转换为字典"""
        exclude = exclude or []
        result = {}
        for column in self.__table__.columns:
            if column.name not in exclude:
                value = getattr(self, column.name)
                if isinstance(value, datetime):
                    value = value.strftime('%Y-%m-%d %H:%M:%S')
                result[column.name] = value
        return result

    def update(self, **kwargs):
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        db.session.commit()
        return self