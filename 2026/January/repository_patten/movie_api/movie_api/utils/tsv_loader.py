import os
from typing import List, Dict, Optional
from movie_api.models.movie import Movie

class TSVLoader:
    """Utility to load IMDb TSV format"""
    
    # TSV column mapping - exact order from file
    COLUMNS = {
        'tconst': 0,              # Column 0: IMDb ID (e.g., tt0000001)
        'titleType': 1,           # Column 1: Type: movie, short, tvSeries, etc.
        'primaryTitle': 2,        # Column 2: Main title
        'originalTitle': 3,       # Column 3: Original language title
        'isAdult': 4,             # Column 4: 0 or 1
        'startYear': 5,           # Column 5: Release/start year
        'endYear': 6,             # Column 6: End year (for TV series, \N for movies)
        'runtimeMinutes': 7,      # Column 7: Runtime in minutes
        'genres': 8               # Column 8: Comma-separated genres
    }
    
    @staticmethod
    def parse_value(value: str, field_type: str):
        """Parse TSV value based on field type"""
        if value == '\\N':  # IMDb null marker
            return None
        
        if field_type == 'int':
            try:
                return int(value)
            except ValueError:
                return None
        elif field_type == 'bool':
            return value == '1'
        elif field_type == 'str':
            return value.strip()
        
        return value
    
    @staticmethod
    def load_tsv(file_path: str, 
                 title_types: List[str] = None,
                 skip_adult: bool = True,
                 min_year: int = None,
                 max_rows: int = None) -> List[Movie]:
        """
        Load movies from IMDb TSV file with filtering
        
        Args:
            file_path: Path to title.basics.tsv
            title_types: Filter by type (e.g., ['movie', 'tvMovie'])
            skip_adult: Skip adult content (default True)
            min_year: Only include movies from year onwards
            max_rows: Limit number of rows loaded
        
        Returns:
            List of Movie objects
        """
        
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"TSV file not found: {file_path}")
        
        movies = []
        skipped = 0
        processed = 0
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                # Skip header
                header = f.readline()
                
                for line_num, line in enumerate(f, start=2):
                    if max_rows and processed >= max_rows:
                        break
                    
                    try:
                        line = line.rstrip('\n')
                        if not line:
                            continue
                        
                        fields = line.split('\t')
                        
                        # Validate field count
                        if len(fields) < 9:
                            skipped += 1
                            continue
                        
                        # Parse fields from TSV columns
                        tconst = fields[0].strip()                      # Column 0: tconst
                        title_type = fields[1].strip()                  # Column 1: titleType
                        primary_title = fields[2].strip()               # Column 2: primaryTitle
                        original_title = fields[3].strip()              # Column 3: originalTitle
                        is_adult = fields[4] == '1'                     # Column 4: isAdult
                        start_year_str = fields[5].strip()              # Column 5: startYear
                        end_year_str = fields[6].strip()                # Column 6: endYear
                        runtime_str = fields[7].strip()                 # Column 7: runtimeMinutes
                        genres_str = fields[8].strip()                  # Column 8: genres
                        
                        # Parse numeric fields
                        try:
                            start_year = int(start_year_str) if start_year_str != '\\N' else None
                        except ValueError:
                            start_year = None
                        
                        try:
                            end_year = int(end_year_str) if end_year_str != '\\N' else None
                        except ValueError:
                            end_year = None
                        
                        try:
                            runtime_minutes = int(runtime_str) if runtime_str != '\\N' else None
                        except ValueError:
                            runtime_minutes = None
                        
                        genres = genres_str if genres_str != '\\N' else None
                        
                        # Apply filters
                        if skip_adult and is_adult:
                            skipped += 1
                            continue
                        
                        if title_types and title_type not in title_types:
                            skipped += 1
                            continue
                        
                        if min_year and start_year and start_year < min_year:
                            skipped += 1
                            continue
                        
                        # Create movie object with exact TSV mappings
                        movie = Movie(
                            id=tconst,                      # From column 0 (tconst)
                            title=primary_title,            # From column 2 (primaryTitle)
                            title_type=title_type,          # From column 1 (titleType)
                            year=start_year or 0,           # From column 5 (startYear)
                            rating=0.0,                     # Not in TSV, will be enriched later
                            director='Unknown',             # Not in TSV
                            plot='',                        # Not in TSV
                            imdb_id=tconst,                 # From column 0 (tconst)
                            original_title=original_title,  # From column 3 (originalTitle)
                            is_adult=is_adult,              # From column 4 (isAdult)
                            runtime_minutes=runtime_minutes,# From column 7 (runtimeMinutes)
                            genres=genres,                  # From column 8 (genres)
                            end_year=end_year               # From column 6 (endYear)
                        )
                        
                        movies.append(movie)
                        processed += 1
                        
                        # Progress indicator
                        if processed % 10000 == 0:
                            print(f"  ✓ Loaded {processed} movies...")
                    
                    except Exception as e:
                        skipped += 1
                        if processed < 5:  # Log first few errors only
                            print(f"  ⚠ Skipped line {line_num}: {e}")
                        continue
            
            print(f"✓ Loaded {processed} movies (skipped {skipped})")
            return movies
        
        except Exception as e:
            print(f"✗ Error loading TSV: {e}")
            raise
    
    @staticmethod
    def load_tsv_chunked(file_path: str, 
                        chunk_size: int = 10000,
                        **kwargs) -> List[List[Movie]]:
        """
        Load TSV in chunks (useful for large files)
        
        Yields chunks of movies for memory-efficient processing
        """
        chunks = []
        current_chunk = []
        processed = 0
        
        with open(file_path, 'r', encoding='utf-8') as f:
            f.readline()  # Skip header
            
            for line in f:
                try:
                    fields = line.rstrip('\n').split('\t')
                    if len(fields) < 9:
                        continue
                    
                    # Apply same parsing as load_tsv
                    movie = Movie(
                        id=fields[0],
                        title=fields[2],
                        year=int(fields[5]) if fields[5] != '\\N' else 0,
                        rating=0.0,
                        director='Unknown',
                        plot='',
                        imdb_id=fields[0],
                        title_type=fields[1],
                        original_title=fields[3],
                        is_adult=fields[4] == '1',
                        runtime_minutes=int(fields[7]) if fields[7] != '\\N' else None,
                        genres=fields[8] if fields[8] != '\\N' else '',
                        end_year=int(fields[6]) if fields[6] != '\\N' else None
                    )
                    
                    current_chunk.append(movie)
                    processed += 1
                    
                    if len(current_chunk) >= chunk_size:
                        chunks.append(current_chunk)
                        print(f"  → Chunk {len(chunks)} ready ({processed} total)")
                        current_chunk = []
                
                except Exception:
                    continue
            
            if current_chunk:
                chunks.append(current_chunk)
        
        print(f"✓ Prepared {len(chunks)} chunks")
        return chunks