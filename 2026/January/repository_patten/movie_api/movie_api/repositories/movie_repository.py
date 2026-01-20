import os
from typing import List, Optional, Dict
from datetime import datetime, timedelta
from contextlib import contextmanager
import sqlite3

from movie_api.models.movie import Movie, PaginationParams, PaginatedResult
from movie_api.repositories.base import IRepository
from movie_api.utils.tsv_loader import TSVLoader


class InMemoryMovieRepository(IRepository):
    """loads from TSV"""

    def __init__(self, data_file: str = 'movie_api/data/title.basics.tsv',
                 title_types: List[str] = None,
                 skip_adult: bool = True,
                 min_year: int = 1900,
                 max_rows: int = 50000):
        """
        Initialize repository with TSV data

        Args:
            data_file: Path to TSV file
            title_types: Filter by type (e.g., ['movie', 'tvMovie'])
            skip_adult: Skip adult content
            min_year: Only load movies from this year onwards
            max_rows: Limit rows for testing (None = all)
        """
        self._storage: Dict[str, Movie] = {}
        self._data_file = data_file
        self._load_tsv_data(title_types, skip_adult, min_year, max_rows)

    def _load_tsv_data(self, title_types: List[str], skip_adult: bool, 
                       min_year: int, max_rows: int):
        """Load movies from TSV file"""
        try:
            print(f"\n📂 Loading from: {self._data_file}")
            movies = TSVLoader.load_tsv(
                self._data_file,
                title_types=title_types or ['movie', 'tvMovie'],
                skip_adult=skip_adult,
                min_year=min_year,
                max_rows=max_rows
            )

            for movie in movies:
                self._storage[movie.id] = movie

            print(f"✓ Repository ready with {len(self._storage)} movies\n")

        except FileNotFoundError:
            print(f"⚠ Warning: {self._data_file} not found")
            print(f"  Please download IMDb dataset or create sample TSV")

    def get_by_id(self, movie_id: str) -> Optional[Movie]:
        """Get movie by ID - O(1) lookup"""
        return self._storage.get(movie_id)

    def get_all(self) -> List[Movie]:
        """Get all movies"""
        return list(self._storage.values())
    
    def add(self, movie: Movie) -> Movie:
        """Add new movie"""
        self._storage[movie.id] = movie
        return movie

    def update(self, movie_id: str, movie: Movie) -> Optional[Movie]:
        """Update existing movie"""
        if movie_id in self._storage:
            self._storage[movie_id] = movie
            return movie
        return None

    def delete(self, movie_id: str) -> bool:
        """Delete movie"""
        if movie_id in self._storage:
            del self._storage[movie_id]
            return True
        return False

    def find(self, **criteria) -> List[Movie]:
        """Find movies by criteria"""
        results = []
        for movie in self._storage.values():
            if all(getattr(movie, k, None) == v for k, v in criteria.items()):
                results.append(movie)
        return results

    def find_by_title(self, title: str) -> List[Movie]:
        """Find movies by title (case-insensitive partial match)"""
        query = title.lower()
        return [m for m in self._storage.values() 
                if query in m.title.lower()]

    def find_by_year(self, year: int) -> List[Movie]:
        """Find movies from a specific year"""
        return [m for m in self._storage.values() if m.year == year]

    def find_by_type(self, title_type: str) -> List[Movie]:
        """Find movies by type (movie, tvMovie, short, etc.)"""
        return [m for m in self._storage.values() 
                if m.title_type == title_type]

    def find_by_genre(self, genre: str) -> List[Movie]:
        """Find movies by genre"""
        return [m for m in self._storage.values() 
                if m.matches_genre(genre)]

    def find_by_runtime_range(self, min_minutes: int, 
                             max_minutes: int) -> List[Movie]:
        """Find movies by runtime range"""
        return [m for m in self._storage.values()
               if m.runtime_minutes and 
               min_minutes <= m.runtime_minutes <= max_minutes]


class CachedMovieRepository(InMemoryMovieRepository):
    """Repository with caching layer"""

    def __init__(self, *args, cache_ttl_minutes: int = 5, **kwargs):
        super().__init__(*args, **kwargs)
        self._cache: Dict[str, tuple] = {}
        self._cache_ttl = timedelta(minutes=cache_ttl_minutes)

    def _is_cache_valid(self, key: str) -> bool:
        """Check if cache entry is still valid"""
        if key not in self._cache:
            return False
        data, timestamp = self._cache[key]
        return datetime.now() - timestamp < self._cache_ttl

    def _invalidate_cache(self, pattern: str = None):
        """Invalidate cache entries"""
        if pattern is None:
            self._cache.clear()
        else:
            self._cache = {k: v for k, v in self._cache.items() 
                          if pattern not in k}

    def find_by_genre(self, genre: str) -> List[Movie]:
        """Cached genre search"""
        cache_key = f"genre:{genre.lower()}"
        
        if self._is_cache_valid(cache_key):
            return self._cache[cache_key][0]

        results = super().find_by_genre(genre)
        self._cache[cache_key] = (results, datetime.now())
        return results

    def find_by_title(self, title: str) -> List[Movie]:
        """Cached title search"""
        cache_key = f"title:{title.lower()}"

        if self._is_cache_valid(cache_key):
            return self._cache[cache_key][0]

        results = super().find_by_title(title)
        self._cache[cache_key] = (results, datetime.now())
        return results


class FilteredMovieRepository(CachedMovieRepository):
    """Filtering & pagination"""

    def find_paginated(self, params: PaginationParams, 
                       **filters) -> PaginatedResult:
        """Get paginated results with multiple filters"""
        results = list(self._storage.values())

        # Apply filters
        if 'year' in filters:
            results = [m for m in results if m.year == filters['year']]

        if 'year_min' in filters:
            results = [m for m in results if m.year >= filters['year_min']]

        if 'year_max' in filters:
            results = [m for m in results if m.year <= filters['year_max']]

        if 'title_type' in filters:
            results = [m for m in results 
                      if m.title_type == filters['title_type']]

        if 'genre' in filters:
            genre = filters['genre']
            results = [m for m in results if m.matches_genre(genre)]

        if 'runtime_min' in filters:
            results = [m for m in results 
                      if m.runtime_minutes and 
                      m.runtime_minutes >= filters['runtime_min']]

        if 'runtime_max' in filters:
            results = [m for m in results 
                      if m.runtime_minutes and 
                      m.runtime_minutes <= filters['runtime_max']]

        if 'title_contains' in filters:
            query = filters['title_contains'].lower()
            results = [m for m in results 
                      if query in m.title.lower()]

        total = len(results)

        # Sort
        reverse = params.sort_order == 'desc'
        try:
            results.sort(key=lambda m: getattr(m, params.sort_by, ''), 
                        reverse=reverse)
        except Exception:
            pass

        # Paginate
        start_idx = (params.page - 1) * params.page_size
        end_idx = start_idx + params.page_size
        items = results[start_idx:end_idx]

        return PaginatedResult(
            items=items,
            total=total,
            page=params.page,
            page_size=params.page_size,
            total_pages=(total + params.page_size - 1) // params.page_size
        )

    def find_with_search(self, query: str, 
                        page: int = 1, page_size: int = 10) -> PaginatedResult:
        """Full-text search"""
        query_lower = query.lower()
        results = [m for m in self._storage.values()
                  if query_lower in m.title.lower()]

        total = len(results)
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size

        return PaginatedResult(
            items=results[start_idx:end_idx],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=(total + page_size - 1) // page_size
        )


class AnalyticsMovieRepository(FilteredMovieRepository):
    """aggregation & analytics"""

    def get_genre_stats(self) -> Dict:
        """Genre frequency analysis"""
        stats = {}
        for movie in self._storage.values():
            for genre in movie.get_genres_list():
                if genre not in stats:
                    stats[genre] = {'count': 0, 'avg_runtime': 0}
                stats[genre]['count'] += 1

        # Calculate averages
        for genre in stats:
            movies = [m for m in self._storage.values() 
                     if m.matches_genre(genre)]
            runtimes = [m.runtime_minutes for m in movies 
                       if m.runtime_minutes]
            if runtimes:
                stats[genre]['avg_runtime'] = round(sum(runtimes) / len(runtimes), 1)

        return dict(sorted(stats.items(), 
                          key=lambda x: x[1]['count'], 
                          reverse=True))

    def get_type_stats(self) -> Dict:
        """Title type distribution"""
        stats = {}
        for movie in self._storage.values():
            title_type = movie.title_type or 'unknown'
            stats[title_type] = stats.get(title_type, 0) + 1
        return dict(sorted(stats.items(), key=lambda x: x[1], reverse=True))
    def get_year_stats(self) -> Dict:
        """Movies per year"""
        stats = {}
        for movie in self._storage.values():
            year = movie.year
            if year not in stats:
                stats[year] = {'count': 0, 'avg_runtime': 0}
            stats[year]['count'] += 1
        
        for year in stats:
            movies = [m for m in self._storage.values() if m.year == year]
            runtimes = [m.runtime_minutes for m in movies 
                       if m.runtime_minutes]
            if runtimes:
                stats[year]['avg_runtime'] = round(sum(runtimes) / len(runtimes), 1)

        return dict(sorted(stats.items()))

    def get_runtime_stats(self) -> Dict:
        """Runtime distribution"""
        movies_with_runtime = [m for m in self._storage.values() 
                              if m.runtime_minutes]

        if not movies_with_runtime:
            return {}
        
        runtimes = [m.runtime_minutes for m in movies_with_runtime]

        return {
            'min': min(runtimes),
            'max': max(runtimes),
            'avg': round(sum(runtimes) / len(runtimes), 1),
            'median': sorted(runtimes)[len(runtimes) // 2],
            'total_count': len(movies_with_runtime)
        }


# Database Repositories
class SQLiteMovieRepository(IRepository):
    """SQLite database-backed repository"""
    
    def __init__(self, db_path: str = 'movie_api/data/movies.db',
                 tsv_file: str = None,
                 title_types: List[str] = None,
                 skip_adult: bool = True,
                 min_year: int = 1900,
                 max_rows: int = None):
        """
        Initialize SQLite repository and create schema.
        Args:
            db_path: Path to SQLite database file
            tsv_file: Path to TSV file (optional, for auto-loading)
            title_types: Filter by type when loading
            skip_adult: Skip adult content when loading
            min_year: Minimum year when loading
            max_rows: Maximum rows to load
        """
        import sqlite3
        self.db_path = db_path
        self.tsv_file = tsv_file
        self.title_types = title_types or ['movie', 'tvMovie']
        self.skip_adult = skip_adult
        self.min_year = min_year
        self.max_rows = max_rows
        
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._create_schema()
        
        # Check if database is empty and load from TSV if needed
        self._load_if_empty()
        
        print(f"✓ Connected to SQLite: {db_path}")
    
    def _load_if_empty(self):
        """Load data from TSV if database is empty"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM movies')
        count = cursor.fetchone()[0]
        
        if count == 0:
            if self.tsv_file and os.path.exists(self.tsv_file):
                print(f"\n📂 Database is empty, auto-loading from TSV...")
                self.bulk_insert_from_tsv(
                    self.tsv_file,
                    title_types=self.title_types,
                    skip_adult=self.skip_adult,
                    min_year=self.min_year,
                    max_rows=self.max_rows
                )
            else:
                print(f"\n⚠️ Database is empty and no TSV file provided")
                print(f"   To load data, call: repo.bulk_insert_from_tsv(tsv_path)")
    
    def _create_schema(self):
        """Create database schema if not exists"""
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS movies (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                title_type TEXT,
                year INTEGER,
                rating REAL DEFAULT 0.0,
                director TEXT,
                plot TEXT,
                imdb_id TEXT,
                original_title TEXT,
                is_adult BOOLEAN DEFAULT 0,
                runtime_minutes INTEGER,
                genres TEXT,
                end_year INTEGER,
                poster_url TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create indexes for common queries
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_title ON movies(title)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_year ON movies(year)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_title_type ON movies(title_type)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_rating ON movies(rating)')
        
        self.conn.commit()
        print("✓ SQLite schema created")
    
    def _row_to_movie(self, row) -> Movie:
        """Convert database row to Movie object"""
        if not row:
            return None
        return Movie(
            id=row['id'],
            title=row['title'],
            title_type=row['title_type'],
            year=row['year'],
            rating=row['rating'],
            director=row['director'],
            plot=row['plot'],
            imdb_id=row['imdb_id'],
            original_title=row['original_title'],
            is_adult=bool(row['is_adult']),
            runtime_minutes=row['runtime_minutes'],
            genres=row['genres'],
            end_year=row['end_year'],
            poster_url=row['poster_url']
        )
    
    def get_by_id(self, movie_id: str) -> Optional[Movie]:
        """Get movie by ID"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM movies WHERE id = ?', (movie_id,))
        row = cursor.fetchone()
        return self._row_to_movie(row)
    
    def get_all(self) -> List[Movie]:
        """Get all movies"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM movies')
        rows = cursor.fetchall()
        return [self._row_to_movie(row) for row in rows]
    
    def add(self, movie: Movie) -> Movie:
        """Add new movie"""
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO movies 
            (id, title, title_type, year, rating, director, plot, 
             imdb_id, original_title, is_adult, runtime_minutes, genres, 
             end_year, poster_url)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            movie.id, movie.title, movie.title_type, movie.year,
            movie.rating, movie.director, movie.plot, movie.imdb_id,
            movie.original_title, int(movie.is_adult), movie.runtime_minutes,
            movie.genres, movie.end_year, movie.poster_url
        ))
        self.conn.commit()
        return movie
    
    def update(self, movie_id: str, movie: Movie) -> Optional[Movie]:
        """Update existing movie"""
        cursor = self.conn.cursor()
        cursor.execute('''
            UPDATE movies SET 
            title=?, title_type=?, year=?, rating=?, director=?, plot=?,
            imdb_id=?, original_title=?, is_adult=?, runtime_minutes=?,
            genres=?, end_year=?, poster_url=?
            WHERE id = ?
        ''', (
            movie.title, movie.title_type, movie.year, movie.rating,
            movie.director, movie.plot, movie.imdb_id, movie.original_title,
            int(movie.is_adult), movie.runtime_minutes, movie.genres,
            movie.end_year, movie.poster_url, movie_id
        ))
        self.conn.commit()
        return self.get_by_id(movie_id)
    
    def delete(self, movie_id: str) -> bool:
        """Delete movie"""
        cursor = self.conn.cursor()
        cursor.execute('DELETE FROM movies WHERE id = ?', (movie_id,))
        self.conn.commit()
        return cursor.rowcount > 0
    
    def find(self, **criteria) -> List[Movie]:
        """Find movies by criteria"""
        query = 'SELECT * FROM movies WHERE 1=1'
        params = []
        
        for key, value in criteria.items():
            if key == 'title_contains':
                query += ' AND title LIKE ?'
                params.append(f'%{value}%')
            else:
                query += f' AND {key} = ?'
                params.append(value)
        
        cursor = self.conn.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()
        return [self._row_to_movie(row) for row in rows]
    
    def find_by_title(self, title: str) -> List[Movie]:
        """Find movies by title"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM movies WHERE title LIKE ?', (f'%{title}%',))
        rows = cursor.fetchall()
        return [self._row_to_movie(row) for row in rows]
    
    def find_by_year(self, year: int) -> List[Movie]:
        """Find movies from a specific year"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM movies WHERE year = ?', (year,))
        rows = cursor.fetchall()
        return [self._row_to_movie(row) for row in rows]
    
    def find_by_type(self, title_type: str) -> List[Movie]:
        """Find movies by type"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM movies WHERE title_type = ?', (title_type,))
        rows = cursor.fetchall()
        return [self._row_to_movie(row) for row in rows]
    
    def find_by_genre(self, genre: str) -> List[Movie]:
        """Find movies by genre"""
        cursor = self.conn.cursor()
        genre_lower = genre.lower()
        cursor.execute('SELECT * FROM movies WHERE genres LIKE ?', (f'%{genre}%',))
        rows = cursor.fetchall()
        
        # Filter in Python (genres are comma-separated)
        results = []
        for row in rows:
            movie = self._row_to_movie(row)
            if movie.matches_genre(genre):
                results.append(movie)
        return results
    
    def find_paginated(self, params: PaginationParams, 
                       **filters) -> PaginatedResult:
        """Get paginated results with filtering"""
        query = 'SELECT * FROM movies WHERE 1=1'
        params_list = []
        
        if 'year' in filters:
            query += ' AND year = ?'
            params_list.append(filters['year'])
        
        if 'year_min' in filters:
            query += ' AND year >= ?'
            params_list.append(filters['year_min'])
        
        if 'year_max' in filters:
            query += ' AND year <= ?'
            params_list.append(filters['year_max'])
        
        if 'title_type' in filters:
            query += ' AND title_type = ?'
            params_list.append(filters['title_type'])
        
        if 'title_contains' in filters:
            query += ' AND title LIKE ?'
            params_list.append(f"%{filters['title_contains']}%")
        
        if 'runtime_min' in filters:
            query += ' AND runtime_minutes >= ?'
            params_list.append(filters['runtime_min'])
        
        if 'runtime_max' in filters:
            query += ' AND runtime_minutes <= ?'
            params_list.append(filters['runtime_max'])
        
        # Count total
        cursor = self.conn.cursor()
        count_query = query.replace('SELECT *', 'SELECT COUNT(*)', 1)
        cursor.execute(count_query, params_list)
        total = cursor.fetchone()[0]
        
        # Sort and paginate
        query += f' ORDER BY {params.sort_by} {"DESC" if params.sort_order == "desc" else "ASC"}'
        query += f' LIMIT ? OFFSET ?'
        
        offset = (params.page - 1) * params.page_size
        params_list.extend([params.page_size, offset])
        
        cursor.execute(query, params_list)
        rows = cursor.fetchall()
        items = [self._row_to_movie(row) for row in rows]
        
        return PaginatedResult(
            items=items,
            total=total,
            page=params.page,
            page_size=params.page_size,
            total_pages=(total + params.page_size - 1) // params.page_size
        )
    
    def bulk_insert_from_tsv(self, tsv_file: str, 
                            title_types: List[str] = None,
                            skip_adult: bool = True,
                            min_year: int = 1900,
                            max_rows: int = None):
        """Bulk insert movies from TSV file with optional filters"""
        from movie_api.utils.tsv_loader import TSVLoader
        
        print(f"\n📥 Bulk inserting from {tsv_file}...")
        movies = TSVLoader.load_tsv(
            tsv_file,
            title_types=title_types or self.title_types,
            skip_adult=skip_adult,
            min_year=min_year,
            max_rows=max_rows
        )
        
        cursor = self.conn.cursor()
        for i, movie in enumerate(movies):
            cursor.execute('''
                INSERT OR REPLACE INTO movies 
                (id, title, title_type, year, rating, director, plot, 
                 imdb_id, original_title, is_adult, runtime_minutes, genres, end_year)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                movie.id, movie.title, movie.title_type, movie.year,
                movie.rating, movie.director, movie.plot, movie.imdb_id,
                movie.original_title, int(movie.is_adult), movie.runtime_minutes,
                movie.genres, movie.end_year
            ))
            
            if (i + 1) % 10000 == 0:
                self.conn.commit()
                print(f"  ✓ Inserted {i + 1} movies...")
        
        self.conn.commit()
        print(f"✓ Bulk insert complete: {len(movies)} movies loaded\n")
