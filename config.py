import os
from datetime import timedelta

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = 'yuan_kong_zhi_chuang_secret_2026'

    # 🌟 核心修复：直接使用标准的相对路径，彻底避开 Windows 路径 Bug！
    SQLALCHEMY_DATABASE_URI = 'sqlite:///database.db'

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')