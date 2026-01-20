from typing import List, Dict, Optional
from movie_api.models.movie import Movie, PaginationParams, PaginatedResult
from movie_api.repositories.base import IRepository

class MovieService:
    """Business logic layer - uses repositories"""
    
    def __init__(self, repository: IRepository):
        self.repository = repository
    
    def get_movie(self, movie_id: str) -> Optional[Movie]:
        """Get single movie"""
        return self.repository.get_by_id(movie_id)
    
    def list_all_movies(self) -> List[Movie]:
        """Get all movies"""
        return self.repository.get_all()
    
    def search_movies(self, query: str, page: int = 1, 
                     page_size: int = 10) -> PaginatedResult:
        """Search movies by title/plot/director"""
        if hasattr(self.repository, 'find_with_search'):
            return self.repository.find_with_search(query, page, page_size)
        
        # Fallback for basic repos
        all_movies = self.repository.get_all()
        query_lower = query.lower()
        results = [m for m in all_movies
                  if query_lower in m.title.lower() 
                  or query_lower in m.plot.lower()]
        
        total = len(results)
        start = (page - 1) * page_size
        end = start + page_size
        
        return PaginatedResult(
            items=results[start:end],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=(total + page_size - 1) // page_size
        )
    
    def get_filtered_movies(self, params: PaginationParams, 
                           **filters) -> PaginatedResult:
        """Get filtered and paginated movies"""
        if hasattr(self.repository, 'find_paginated'):
            return self.repository.find_paginated(params, **filters)
        
        return PaginatedResult([], 0, 1, 10, 0)
    
    def get_top_movies(self, limit: int = 10) -> List[Movie]:
        """Get best-rated movies"""
        if hasattr(self.repository, 'get_top_rated'):
            return self.repository.get_top_rated(limit)
        
        all_movies = self.repository.get_all()
        return sorted(all_movies, key=lambda m: m.rating, reverse=True)[:limit]
    
    def get_movies_by_director(self, director: str) -> List[Movie]:
        """Get all movies by a director"""
        if hasattr(self.repository, 'find_by_director'):
            return self.repository.find_by_director(director)
        
        return self.repository.find(director=director)
    
    def get_director_analysis(self) -> Dict:
        """Get analytics for directors"""
        if hasattr(self.repository, 'get_director_stats'):
            return self.repository.get_director_stats()
        
        return {}
    
    def get_rating_distribution(self) -> Dict:
        """Get rating distribution"""
        if hasattr(self.repository, 'get_rating_distribution'):
            return self.repository.get_rating_distribution()
        
        return {}
    
    def get_recommendations(self, movie_id: str) -> List[Movie]:
        """Get similar movies"""
        if hasattr(self.repository, 'find_similar_movies'):
            return self.repository.find_similar_movies(movie_id)
        
        movie = self.repository.get_by_id(movie_id)
        if not movie:
            return []
        
        if hasattr(self.repository, 'find_by_director'):
            return self.repository.find_by_director(movie.director)
        
        return []
    
    def add_movie(self, title: str, year: int, director: str, 
                 plot: str, rating: float, title_type='movie') -> Movie:
        """Create movie with validation"""
        if not title or len(title) < 2:
            raise ValueError("Title must be at least 2 characters")
        if not (0 <= rating <= 10):
            raise ValueError("Rating must be between 0-10")
        if year < 1800 or year > 2100:
            raise ValueError("Year must be reasonable")
        
        movie = Movie(
            id=f"movie_{len(self.repository.get_all()) + 1}",
            title=title,
            year=year,
            director=director,
            plot=plot,
            rating=rating,
            title_type=title_type
        )
        return self.repository.add(movie)
    
    def update_movie(self, movie_id: str, **kwargs) -> Optional[Movie]:
        """Update movie fields"""
        movie = self.repository.get_by_id(movie_id)
        if not movie:
            return None
        
        for key, value in kwargs.items():
            if hasattr(movie, key):
                setattr(movie, key, value)
        
        return self.repository.update(movie_id, movie)
    
    def delete_movie(self, movie_id: str) -> bool:
        """Delete movie"""
        return self.repository.delete(movie_id)
