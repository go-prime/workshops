from flask import Flask, jsonify
from config import config
import os
from movie_api.repositories.movie_repository import (
    InMemoryMovieRepository,
    CachedMovieRepository,
    FilteredMovieRepository,
    AnalyticsMovieRepository,
    SQLiteMovieRepository
)
from movie_api.services.movie_service import MovieService
from movie_api.controllers.movie_controller import movie_bp, init_controller

def create_app(config_name: str = None):
    """Application factory"""
    
    if config_name is None:
        config_name = os.getenv('FLASK_ENV', 'development')
    
    app = Flask(__name__)
    cfg = config[config_name]
    app.config.from_object(cfg)
    
    print("\n" + "="*60)
    print(f"🎬 IMDb Movie API - Repository Pattern Workshop")
    print(f"   Environment: {config_name.upper()}")
    print(f"   Data: {cfg.TSV_FILE_PATH}")
    print("="*60)
    
    # Initialize repository with TSV data
    # Uncomment one to use different repository
    
    # repository = InMemoryMovieRepository(          
    #     cfg.TSV_FILE_PATH,
    #     title_types=cfg.TSV_TITLE_TYPES,
    #     skip_adult=cfg.TSV_SKIP_ADULT,
    #     min_year=cfg.TSV_MIN_YEAR,
    #     max_rows=cfg.TSV_MAX_ROWS
    # )

    repository = CachedMovieRepository(
        cfg.TSV_FILE_PATH,
        title_types=cfg.TSV_TITLE_TYPES,
        skip_adult=cfg.TSV_SKIP_ADULT,
        min_year=cfg.TSV_MIN_YEAR,
        max_rows=cfg.TSV_MAX_ROWS
    )

    # repository = FilteredMovieRepository(          # Example 3 (with filtering)
    #     cfg.TSV_FILE_PATH,
    #     title_types=cfg.TSV_TITLE_TYPES,
    #     skip_adult=cfg.TSV_SKIP_ADULT,
    #     min_year=cfg.TSV_MIN_YEAR,
    #     max_rows=cfg.TSV_MAX_ROWS
    # )

    # repository = AnalyticsMovieRepository(         # Example 5 (with analytics)
    #     cfg.TSV_FILE_PATH,
    #     title_types=cfg.TSV_TITLE_TYPES,
    #     skip_adult=cfg.TSV_SKIP_ADULT,
    #     min_year=cfg.TSV_MIN_YEAR,
    #     max_rows=cfg.TSV_MAX_ROWS
    # )

    # repository = SQLiteMovieRepository(
    #     db_path='movie_api/data/movies.db',
    #     tsv_file=cfg.TSV_FILE_PATH,
    #     title_types=cfg.TSV_TITLE_TYPES,
    #     skip_adult=cfg.TSV_SKIP_ADULT,
    #     min_year=cfg.TSV_MIN_YEAR,
    #     max_rows=cfg.TSV_MAX_ROWS
    # )

    # Create service with repository
    service = MovieService(repository)

    # Initialize controller with service
    init_controller(service)

    # Register blueprints
    app.register_blueprint(movie_bp)

    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        return {'error': 'Endpoint not found'}, 404
    
    @app.errorhandler(500)
    def internal_error(error):
        return {'error': 'Internal server error'}, 500
    
    # Root endpoint
    @app.route('/')
    def index():
        return {
            'name': 'IMDb Movie API',
            'version': '1.0.0',
            'description': 'Repository Pattern Workshop',
            'endpoints': {
                'search': '/api/movies/search?q=query',
                'filter': '/api/movies/filter?year_min=2000&genre=Action',
                'by_year': '/api/movies/by-year/2020',
                'by_type': '/api/movies/by-type/movie',
                'by_genre': '/api/movies/by-genre/Action',
                'by_runtime': '/api/movies/by-runtime?min=90&max=120',
                'analytics_genres': '/api/movies/analytics/genre-stats',
                'analytics_types': '/api/movies/analytics/type-stats',
                'analytics_years': '/api/movies/analytics/year-stats',
                'analytics_runtime': '/api/movies/analytics/runtime-stats'
            }
        }, 200
    
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, port=5000)