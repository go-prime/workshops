from dataclasses import dataclass, asdict
from typing import Optional, List
from datetime import datetime

from dataclasses import dataclass, asdict
from typing import Optional, List
from datetime import datetime


@dataclass
class Movie:
    """Movie domain model - IMDb compatible"""
    id: str                          # tconst (IMDb ID)
    title: str                       # primaryTitle
    title_type: str                  # movie, tvMovie, tvSeries, short, etc.
    year: int                        # startYear
    rating: float = 0.0              # IMDb rating (will be 0 initially)
    director: str = 'Unknown'        # director name
    plot: str = ''                   # plot summary

    # IMDb specific fields
    imdb_id: Optional[str] = None
    original_title: Optional[str] = None
    is_adult: bool = False
    runtime_minutes: Optional[int] = None
    genres: Optional[str] = None      # comma-separated
    end_year: Optional[int] = None    # for TV series
    
    # Metadata
    poster_url: Optional[str] = None
    created_at: Optional[datetime] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        data = asdict(self)
        data['created_at'] = self.created_at.isoformat() if self.created_at else None
        return data
    
    def get_genres_list(self) -> List[str]:
        """Parse comma-separated genres"""
        if not self.genres:
            return []
        return [g.strip() for g in self.genres.split(',')]
    
    def matches_genre(self, genre: str) -> bool:
        """Check if movie has a specific genre"""
        return genre.lower() in [g.lower() for g in self.get_genres_list()]

@dataclass
class Review:
    """Review domain model"""
    id: str
    movie_id: str
    user_id: str
    rating: int
    comment: str
    created_at: Optional[datetime] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
    
    def to_dict(self):
        data = asdict(self)
        data['created_at'] = self.created_at.isoformat() if self.created_at else None
        return data


@dataclass
class PaginationParams:
    """Pagination parameters"""
    page: int = 1
    page_size: int = 10
    sort_by: str = 'title'
    sort_order: str = 'asc'

@dataclass
class PaginatedResult:
    """Paginated result wrapper"""
    items: List[Movie]
    total: int
    page: int
    page_size: int
    total_pages: int
    
    def to_dict(self):
        return {
            'items': [item.to_dict() for item in self.items],
            'total': self.total,
            'page': self.page,
            'page_size': self.page_size,
            'total_pages': self.total_pages
        }