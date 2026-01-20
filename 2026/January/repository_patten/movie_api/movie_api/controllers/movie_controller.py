from flask import Blueprint, request, jsonify
from movie_api.services.movie_service import MovieService
from movie_api.models.movie import PaginationParams

movie_bp = Blueprint('movies', __name__, url_prefix='/api/movies')
_service: MovieService = None

def init_controller(service: MovieService):
    """Initialize controller with service"""
    global _service
    _service = service


@movie_bp.route('/<movie_id>', methods=['GET', 'POST', 'PUT', 'DELETE'])
def get_movie(movie_id):
    """Get single movie by IMDb ID - supports both GET and POST"""
    movie = _service.get_movie(movie_id)
    if not movie:
        return {'error': 'Movie not found'}, 404
    return {'data': movie.to_dict()}, 200


@movie_bp.route('/', methods=['GET'])
def list_movies():
    """List all movies"""
    movies = _service.list_all_movies()
    return {
        'data': [m.to_dict() for m in movies],
        'count': len(movies)
    }, 200


@movie_bp.route('/search', methods=['GET'])
def search():
    """Full-text search by title"""
    query = request.args.get('q', '')
    page = request.args.get('page', 1, type=int)
    page_size = request.args.get('page_size', 10, type=int)
    
    result = _service.search_movies(query, page, page_size)
    return result.to_dict(), 200


@movie_bp.route('/filter', methods=['GET'])
def filter_movies():
    """Advanced filtering with pagination"""
    page = request.args.get('page', 1, type=int)
    page_size = request.args.get('page_size', 10, type=int)
    sort_by = request.args.get('sort_by', 'title')
    sort_order = request.args.get('sort_order', 'asc')
    
    filters = {}
    if request.args.get('year'):
        filters['year'] = int(request.args.get('year'))
    if request.args.get('year_min'):
        filters['year_min'] = int(request.args.get('year_min'))
    if request.args.get('year_max'):
        filters['year_max'] = int(request.args.get('year_max'))
    if request.args.get('type'):
        filters['title_type'] = request.args.get('type')
    if request.args.get('genre'):
        filters['genre'] = request.args.get('genre')
    if request.args.get('runtime_min'):
        filters['runtime_min'] = int(request.args.get('runtime_min'))
    if request.args.get('runtime_max'):
        filters['runtime_max'] = int(request.args.get('runtime_max'))
    if request.args.get('title_contains'):
        filters['title_contains'] = request.args.get('title_contains')
    
    params = PaginationParams(page=page, page_size=page_size, 
                             sort_by=sort_by, sort_order=sort_order)
    result = _service.get_filtered_movies(params, **filters)
    return result.to_dict(), 200


@movie_bp.route('/by-year/<int:year>', methods=['GET'])
def by_year(year):
    """Get all movies from a specific year"""
    if hasattr(_service.repository, 'find_by_year'):
        movies = _service.repository.find_by_year(year)
    else:
        movies = []
    
    return {
        'year': year,
        'data': [m.to_dict() for m in movies],
        'count': len(movies)
    }, 200

@movie_bp.route('/by-type/<title_type>', methods=['GET'])
def by_type(title_type):
    """Get movies by type (movie, tvMovie, short, etc.)"""
    if hasattr(_service.repository, 'find_by_type'):
        movies = _service.repository.find_by_type(title_type)
    else:
        movies = []
    
    return {
        'type': title_type,
        'data': [m.to_dict() for m in movies],
        'count': len(movies)
    }, 200

@movie_bp.route('/by-genre/<genre>', methods=['GET'])
def by_genre(genre):
    """Get all movies with a specific genre"""
    print(f"\n🎬 Searching for genre: {genre}")
    
    if hasattr(_service.repository, 'find_by_genre'):
        movies = _service.repository.find_by_genre(genre)
        print(f"✓ Found {len(movies)} movies with genre: {genre}\n")
    else:
        movies = []
    
    return {
        'genre': genre,
        'data': [m.to_dict() for m in movies],
        'count': len(movies)
    }, 200

@movie_bp.route('/by-runtime', methods=['GET'])
def by_runtime():
    """Get movies by runtime range"""
    min_minutes = request.args.get('min', 0, type=int)
    max_minutes = request.args.get('max', 500, type=int)
    
    if hasattr(_service.repository, 'find_by_runtime_range'):
        movies = _service.repository.find_by_runtime_range(min_minutes, max_minutes)
    else:
        movies = []
    
    return {
        'range': f"{min_minutes}-{max_minutes} minutes",
        'data': [m.to_dict() for m in movies],
        'count': len(movies)
    }, 200


@movie_bp.route('/analytics/genre-stats', methods=['GET'])
def genre_stats():
    """Genre frequency and statistics"""
    if hasattr(_service.repository, 'get_genre_stats'):
        stats = _service.repository.get_genre_stats()
    else:
        stats = {}
    
    return {'data': stats}, 200

@movie_bp.route('/analytics/type-stats', methods=['GET'])
def type_stats():
    """Title type distribution"""
    if hasattr(_service.repository, 'get_type_stats'):
        stats = _service.repository.get_type_stats()
    else:
        stats = {}
    
    return {'data': stats}, 200

@movie_bp.route('/analytics/year-stats', methods=['GET'])
def year_stats():
    """Movies per year"""
    if hasattr(_service.repository, 'get_year_stats'):
        stats = _service.repository.get_year_stats()
    else:
        stats = {}
    
    return {'data': stats}, 200

@movie_bp.route('/analytics/runtime-stats', methods=['GET'])
def runtime_stats():
    """Runtime distribution statistics"""
    if hasattr(_service.repository, 'get_runtime_stats'):
        stats = _service.repository.get_runtime_stats()
    else:
        stats = {}
    
    return {'data': stats}, 200

@movie_bp.route('/health', methods=['GET'])
def health():
    """Health check with dataset info"""
    movies = _service.list_all_movies()
    return {
        'status': 'healthy',
        'total_movies': len(movies),
        'dataset': 'IMDb TSV'
    }, 200