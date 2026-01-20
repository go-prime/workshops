import pytest
from movie_api.models.movie import Movie

class TestInMemoryRepository:
    """Test basic in-memory repository functionality"""
    
    def test_repository_loads_data(self, test_repository):
        """Repository should load test data"""
        all_movies = test_repository.get_all()
        assert len(all_movies) == 10
    
    def test_get_by_id(self, test_repository, test_data):
        """Should retrieve movie by ID"""
        movie = test_repository.get_by_id(test_data['shawshank']['id'])
        
        assert movie is not None
        assert movie.id == test_data['shawshank']['id']
        assert movie.title == test_data['shawshank']['title']
    
    def test_get_by_id_not_found(self, test_repository):
        """Should return None for non-existent movie"""
        movie = test_repository.get_by_id('tt0000000')
        assert movie is None
    
    def test_find_by_title(self, test_repository, test_data):
        """Should find movie by partial title match"""
        movies = test_repository.find_by_title('Shawshank')
        
        assert len(movies) >= 1
        assert movies[0].id == test_data['shawshank']['id']
    
    def test_find_by_year(self, test_repository):
        """Should find movies from specific year"""
        movies_1994 = test_repository.find_by_year(1994)
        
        assert len(movies_1994) >= 3  # Shawshank, Pulp Fiction, Forrest Gump
        assert all(m.year == 1994 for m in movies_1994)
    
    def test_find_by_genre(self, test_repository):
        """Should find movies by genre"""
        drama_movies = test_repository.find_by_genre('Drama')
        
        assert len(drama_movies) > 0
        assert all(m.matches_genre('Drama') for m in drama_movies)
    
    def test_find_by_genre_case_insensitive(self, test_repository):
        """Genre search should be case-insensitive"""
        drama_lower = test_repository.find_by_genre('drama')
        drama_upper = test_repository.find_by_genre('DRAMA')
        
        assert len(drama_lower) == len(drama_upper)
    
    def test_find_by_type(self, test_repository):
        """Should find movies by type"""
        movies = test_repository.find_by_type('movie')
        
        assert len(movies) == 10  # All test data are movies
        assert all(m.title_type == 'movie' for m in movies)
    
    def test_add_movie(self, test_repository):
        """Should add new movie to repository"""
        initial_count = len(test_repository.get_all())
        
        new_movie = Movie(
            id='tt9999999',
            title='Test Movie',
            title_type='movie',
            year=2024,
            rating=8.5,
            director='Test Director',
            plot='Test plot'
        )
        test_repository.add(new_movie)
        
        assert len(test_repository.get_all()) == initial_count + 1
        assert test_repository.get_by_id('tt9999999') == new_movie
    
    def test_update_movie(self, test_repository, test_data):
        """Should update existing movie"""
        movie = test_repository.get_by_id(test_data['shawshank']['id'])
        original_title = movie.title
        
        movie.title = 'Updated Title'
        test_repository.update(test_data['shawshank']['id'], movie)
        
        updated = test_repository.get_by_id(test_data['shawshank']['id'])
        assert updated.title == 'Updated Title'
        assert updated.title != original_title
    
    def test_delete_movie(self, test_repository, test_data):
        """Should delete movie from repository"""
        test_repository.delete(test_data['shawshank']['id'])
        
        movie = test_repository.get_by_id(test_data['shawshank']['id'])
        assert movie is None
    
    def test_find_with_criteria(self, test_repository):
        """Should find movies with multiple criteria"""
        results = test_repository.find(title_type='movie', year=1994)
        
        assert len(results) > 0
        assert all(m.title_type == 'movie' and m.year == 1994 for m in results)


class TestCachedRepository:
    """Test caching layer functionality"""
    
    def test_cache_hit_on_second_query(self):
        """Should return cached result on second query"""
        from movie_api.repositories.movie_repository import CachedMovieRepository
        import os
        
        test_path = os.path.join(os.path.dirname(__file__), 'data', 'test_movies.tsv')
        repo = CachedMovieRepository(data_file=test_path, max_rows=None)
        
        # First query - populates cache
        results1 = repo.find_by_genre('Drama')
        # Second query - should be cached
        results2 = repo.find_by_genre('Drama')
        
        assert len(results1) == len(results2)
        assert results1 == results2
    
    def test_cache_invalidation_on_add(self):
        """Cache should be invalidated when data is added"""
        from movie_api.repositories.movie_repository import CachedMovieRepository
        import os
        
        test_path = os.path.join(os.path.dirname(__file__), 'data', 'test_movies.tsv')
        repo = CachedMovieRepository(data_file=test_path, max_rows=None)
        
        # Query and cache result
        before = repo.find_by_genre('Drama')
        
        # Add new movie
        new_movie = Movie(
            id='tt8888888',
            title='New Drama',
            title_type='movie',
            year=2024,
            rating=7.0,
            director='Test',
            plot='Test',
            genres='Drama'
        )
        repo.add(new_movie)
        
        # Query again - should get fresh result
        after = repo.find_by_genre('Drama')
        
        assert len(after) == len(before) + 1


class TestFilteredRepository:
    """Test filtering and pagination"""
    
    def test_pagination(self):
        """Should paginate results correctly"""
        from movie_api.repositories.movie_repository import FilteredMovieRepository
        from movie_api.models.movie import PaginationParams
        import os
        
        test_path = os.path.join(os.path.dirname(__file__), 'data', 'test_movies.tsv')
        repo = FilteredMovieRepository(data_file=test_path, max_rows=None)
        
        params = PaginationParams(page=1, page_size=3)
        result = repo.find_paginated(params)
        
        assert len(result.items) <= 3
        assert result.page == 1
        assert result.page_size == 3
        assert result.total == 10
    
    def test_pagination_second_page(self):
        """Should get second page of results"""
        from movie_api.repositories.movie_repository import FilteredMovieRepository
        from movie_api.models.movie import PaginationParams
        import os
        
        test_path = os.path.join(os.path.dirname(__file__), 'data', 'test_movies.tsv')
        repo = FilteredMovieRepository(data_file=test_path, max_rows=None)
        
        page1_params = PaginationParams(page=1, page_size=3)
        page1 = repo.find_paginated(page1_params)
        
        page2_params = PaginationParams(page=2, page_size=3)
        page2 = repo.find_paginated(page2_params)
        
        # Different results
        page1_ids = {m.id for m in page1.items}
        page2_ids = {m.id for m in page2.items}
        assert page1_ids.isdisjoint(page2_ids)
    
    def test_filter_by_year_range(self):
        """Should filter by year range"""
        from movie_api.repositories.movie_repository import FilteredMovieRepository
        from movie_api.models.movie import PaginationParams
        import os
        
        test_path = os.path.join(os.path.dirname(__file__), 'data', 'test_movies.tsv')
        repo = FilteredMovieRepository(data_file=test_path, max_rows=None)
        
        params = PaginationParams()
        result = repo.find_paginated(params, year_min=1990, year_max=2000)
        
        assert len(result.items) > 0
        assert all(1990 <= m.year <= 2000 for m in result.items)
    
    def test_filter_by_genre(self):
        """Should filter paginated results by genre"""
        from movie_api.repositories.movie_repository import FilteredMovieRepository
        from movie_api.models.movie import PaginationParams
        import os
        
        test_path = os.path.join(os.path.dirname(__file__), 'data', 'test_movies.tsv')
        repo = FilteredMovieRepository(data_file=test_path, max_rows=None)
        
        params = PaginationParams()
        result = repo.find_paginated(params, genre='Action')
        
        assert len(result.items) > 0
        assert all(m.matches_genre('Action') for m in result.items)


class TestAnalyticsRepository:
    """Test analytics and aggregation"""

    def test_genre_stats(self):
        """Should calculate genre statistics"""
        from movie_api.repositories.movie_repository import AnalyticsMovieRepository
        import os

        test_path = os.path.join(os.path.dirname(__file__), 'data', 'test_movies.tsv')
        repo = AnalyticsMovieRepository(data_file=test_path, max_rows=None)

        stats = repo.get_genre_stats()

        assert 'Drama' in stats
        assert stats['Drama']['count'] > 0

    def test_type_stats(self):
        """Should calculate type distribution"""
        from movie_api.repositories.movie_repository import AnalyticsMovieRepository
        import os
        
        test_path = os.path.join(os.path.dirname(__file__), 'data', 'test_movies.tsv')
        repo = AnalyticsMovieRepository(data_file=test_path, max_rows=None)
        
        stats = repo.get_type_stats()

        assert 'movie' in stats
        assert stats['movie'] == 10

    def test_year_stats(self):
        """Should calculate movies per year"""
        from movie_api.repositories.movie_repository import AnalyticsMovieRepository
        import os

        test_path = os.path.join(os.path.dirname(__file__), 'data', 'test_movies.tsv')
        repo = AnalyticsMovieRepository(data_file=test_path, max_rows=None)

        stats = repo.get_year_stats()

        assert 1994 in stats
        assert stats[1994]['count'] >= 3