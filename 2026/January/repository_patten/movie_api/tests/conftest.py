import pytest
import os
from movie_api.repositories.movie_repository import InMemoryMovieRepository
from movie_api.services.movie_service import MovieService

@pytest.fixture
def test_data_path():
    """Path to test TSV file"""
    return os.path.join(os.path.dirname(__file__), 'data', 'test_movies.tsv')

@pytest.fixture
def test_repository(test_data_path):
    """In-memory repository with test data"""
    repo = InMemoryMovieRepository(
        data_file=test_data_path,
        title_types=['movie'],
        skip_adult=True,
        min_year=1900,
        max_rows=None
    )
    return repo

@pytest.fixture
def test_service(test_repository):
    """test repository"""
    return MovieService(test_repository)

@pytest.fixture
def test_data():
    """Known test data for assertions"""
    return {
        'shawshank': {
            'id': 'tt0111161',
            'title': 'The Shawshank Redemption',
            'year': 1994,
            'genres': 'Drama'
        },
        'godfather': {
            'id': 'tt0068646',
            'title': 'The Godfather',
            'year': 1972,
            'genres': 'Crime,Drama'
        },
        'dark_knight': {
            'id': 'tt0468569',
            'title': 'The Dark Knight',
            'year': 2008,
            'genres': 'Action,Crime,Drama'
        }
    }