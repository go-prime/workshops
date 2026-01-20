import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Base configuration"""
    FLASK_APP = 'app.py'
    FLASK_ENV = os.getenv('FLASK_ENV', 'development')
    DEBUG = FLASK_ENV == 'development'
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-key-change-in-production')
    CACHE_TTL_MINUTES = 30
    
    # TSV Loading config
    TSV_FILE_PATH = os.getenv('TSV_FILE_PATH', 'movie_api/data/title.basics.tsv')
    TSV_TITLE_TYPES = ['movie', 'tvMovie']  # Filter by type
    TSV_SKIP_ADULT = True
    TSV_MIN_YEAR = 1900
    TSV_MAX_ROWS = None  # None = load all
    
class DevelopmentConfig(Config):
    """Development configuration - load fewer rows for speed"""
    DEBUG = True
    TESTING = False
    TSV_MAX_ROWS = 50000  # Limit for development

class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    DEBUG = True
    TSV_MAX_ROWS = 1000  # Very small for unit tests

class ProductionConfig(Config):
    """Production configuration - load everything"""
    DEBUG = False
    TESTING = False
    TSV_MAX_ROWS = None  # Load all data

config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}