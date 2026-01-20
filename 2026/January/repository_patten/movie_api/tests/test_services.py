import pytest

class TestMovieService:
    """Test service/business logic layer"""
    
    def test_service_initialization(self, test_service, test_repository):
        """Service should initialize with repository"""
        assert test_service.repository == test_repository
    
    def test_get_movie(self, test_service, test_data):
        """Should retrieve single movie through service"""
        movie = test_service.get_movie(test_data['shawshank']['id'])
        
        assert movie is not None
        assert movie.title == test_data['shawshank']['title']
    
    def test_list_all_movies(self, test_service):
        """Should list all movies"""
        movies = test_service.list_all_movies()
        
        assert len(movies) == 10
        assert all(hasattr(m, 'title') for m in movies)
    
    def test_search_movies(self, test_service):
        """Should search movies by query"""
        result = test_service.search_movies('Dark')
        
        assert result.total > 0
        assert any('Dark' in m.title for m in result.items)
    
    def test_get_top_movies(self, test_service):
        """Should get top-rated movies"""
        top_movies = test_service.get_top_movies(5)
        
        # Should return at most 5 movies
        assert len(top_movies) <= 5
    
    def test_add_movie_validation(self, test_service):
        """Should validate movie on creation"""
        # Test invalid title
        with pytest.raises(ValueError):
            test_service.add_movie('', 2024, 'Director', 'Plot', 8.0)
        
        # Test invalid rating
        with pytest.raises(ValueError):
            test_service.add_movie('Valid Title', 2024, 'Director', 'Plot', 11.0)
        
        # Test invalid year
        with pytest.raises(ValueError):
            test_service.add_movie('Valid Title', 1700, 'Director', 'Plot', 8.0)
    
    def test_add_movie_success(self, test_service):
        """Should add valid movie"""
        movie = test_service.add_movie(
            'New Movie',
            2024,
            'Test Director',
            'Test plot',
            7.5
        )
        
        assert movie.title == 'New Movie'
        assert movie.year == 2024
        assert movie.rating == 7.5
    
    def test_delete_movie(self, test_service, test_data):
        """Should delete movie through service"""
        success = test_service.delete_movie(test_data['shawshank']['id'])
        
        assert success is True
        assert test_service.get_movie(test_data['shawshank']['id']) is None
    
    def test_repository_swapping(self, test_data_path):
        """Should work identically with different repositories"""
        from movie_api.repositories.movie_repository import (
            InMemoryMovieRepository,
            CachedMovieRepository,
            FilteredMovieRepository
        )
        from movie_api.services.movie_service import MovieService
        
        # Test with 3 different repositories
        repos = [
            InMemoryMovieRepository(data_file=test_data_path, max_rows=None),
            CachedMovieRepository(data_file=test_data_path, max_rows=None),
            FilteredMovieRepository(data_file=test_data_path, max_rows=None),
        ]
        print('Repos')
        for repo in repos:
            service = MovieService(repo)
            test_data = repo.get_all()
            assert 1 == 1
            # Same test, all should pass
            movie = service.get_movie(test_data[0].id)
            assert movie.title == 'The Shawshank Redemption'
            
            all_movies = service.list_all_movies()
            assert len(all_movies) == 10