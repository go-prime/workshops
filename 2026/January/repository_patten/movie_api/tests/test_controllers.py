import pytest
from app import create_app

@pytest.fixture
def app():
    """Create test Flask app"""
    app = create_app('testing')
    return app

@pytest.fixture
def client(app):
    """Create test client"""
    return app.test_client()

class TestMovieEndpoints:
    """Test API endpoints"""
    
    def test_get_all_movies(self, client):
        """GET /api/movies/ should return all movies"""
        response = client.get('/api/movies/')
        
        assert response.status_code == 200
        data = response.get_json()
        assert 'data' in data
        assert 'count' in data
        assert data['count'] > 0
    
    def test_get_single_movie(self, client, test_data):
        """GET /api/movies/{id} should return single movie"""
        response = client.get(f"/api/movies/{test_data['shawshank']['id']}")
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['data']['title'] == 'The Shawshank Redemption'
    
    def test_get_nonexistent_movie(self, client):
        """GET /api/movies/{id} should return 404 for invalid ID"""
        response = client.get('/api/movies/tt0000000')
        
        assert response.status_code == 404
        assert 'error' in response.get_json()
    
    def test_search_endpoint(self, client):
        """GET /api/movies/search should search movies"""
        response = client.get('/api/movies/search?q=Godfather')
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['total'] > 0
    
    def test_filter_endpoint(self, client):
        """GET /api/movies/filter should filter with pagination"""
        response = client.get('/api/movies/filter?genre=Drama&page=1&page_size=5')
        
        assert response.status_code == 200
        data = response.get_json()
        assert 'items' in data
        assert 'total' in data
        assert 'page' in data
    
    def test_by_genre_endpoint(self, client):
        """GET /api/movies/by-genre/{genre} should return movies"""
        response = client.get('/api/movies/by-genre/Drama')
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['genre'] == 'Drama'
        assert data['count'] > 0
    
    def test_by_year_endpoint(self, client):
        """GET /api/movies/by-year/{year} should return movies"""
        response = client.get('/api/movies/by-year/1994')
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['year'] == 1994
        assert data['count'] > 0
    
    def test_analytics_endpoint(self, client):
        """GET /api/movies/analytics/* should return stats"""
        endpoints = [
            '/api/movies/analytics/genre-stats',
            '/api/movies/analytics/type-stats',
            '/api/movies/analytics/year-stats',
            '/api/movies/analytics/runtime-stats'
        ]
        
        for endpoint in endpoints:
            response = client.get(endpoint)
            assert response.status_code == 200
    
    def test_create_movie(self, client):
        """POST /api/movies/ should create movie"""
        new_movie = {
            'title': 'Test Movie',
            'title_type': 'movie',
            'year': 2024,
            'director': 'Test Director',
            'plot': 'Test plot',
            'rating': 7.5
        }
        response = client.post('/api/movies/', json=new_movie)
        
        assert response.status_code == 201
        data = response.get_json()
        assert data['data']['title'] == 'Test Movie'
    
    def test_create_movie_validation(self, client):
        """POST /api/movies/ should validate input"""
        invalid_movie = {
            'title': '',  # Invalid - empty
            'year': 2024,
            'director': 'Director',
            'plot': 'Plot',
            'rating': 8.0
        }
        response = client.post('/api/movies/', json=invalid_movie)
        
        assert response.status_code == 400
        assert 'error' in response.get_json()
    
    def test_health_check(self, client):
        """GET /api/movies/health should return status"""
        response = client.get('/api/movies/health')
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'healthy'