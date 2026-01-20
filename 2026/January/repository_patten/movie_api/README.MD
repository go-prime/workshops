
  

A structural design pattern that advocates for the abstraction of data access and operations to manipulate that data. This enables better code reusability, testability, and creates one source of truth with respect to the data layer in your application.

  

## Key Ideas

  

### Decoupling

  

Business logic and the data layer are separated by an intermediary layer, (the repository) which provides a standardized way to access and manage data. Ensuring that changes in the data layer don't ripple throught the codebase.

**Add example of tightly-coupled code and Django MVT MTV design as a philosophy to compare against.**

  

### Abstraction

  

The business logic does not need to understand the details of the data layer beyond the interface it uses to connect to it. The interface acts as a contract between the layers, allowing the implementation to change as long as the contract remains unchanged.

**Expand on last point of a typical change one would make and how we can do it using the Movie API as an example.**

  

### Swappable

  

Once a contract or intermediary layer is defined, you should be able to swap data sources with minimal effort. This is valuablle things like:

  

1. Unit Testing

2. Database Migration

3. and Performance Optimization

  

## Flask Project - Movie Database API

  

To explore these ideas, we have a minimal flask application that provides endpoints to read and manage movie data from `IMDB`. This project reflects implementation of some core ideas of th Repository Design Pattern.

  

- Multiple repository implementations.

- Clear separation of concerns. **Explain how we have separated them**

- Performance differences

- Uniform behavior of endpoints

  

We have 4 main in-memory repository classes:

Data from the TSV file is stored in memory. They all inherit at least the base repository with `InMemoryMovieRepository `being the uppermost in the structure,

  

-  **`InMemoryMovieRepository`** - Reading directly from the TSV file and loads into a python dictionary. Relatively fast on medium datasets. Data is lost on restart. Use cases include development and prototyping.

-  **`CachedMovieRepository`** - Extends `InMemoryMovieRepository` but is additionally a caching-layer repository. Faster queries and improvement on repeated queries. Useful for performance testing.

-  **`FilteredMovieRepository`**- Extends `CachedMovieRepository`with added functionality for filtering - for querying multiple parameters and pagination for more efficient and managaeble response.

-  **`AnalyticsMovieRepository`**- Extends `FilteredMovieRepository` and implements aggregation and analytics.

  

-  **`SQLiteMovieRepository`** - Directly extends base repository. A full sql repository that provides persistence and production level querying.

  

### Project Structure

  

movie_api/

├── models/

│ └── movie.py # models (Movie, Review)

├── repositories/

│ ├── base.py # abstract base class

│ └── movie_repository.py # repository implementations

├── services/

│ └── movie_service.py # logic layer

├── controllers/

│ └── movie_controller.py # Flask routers

├── utils/

│ └── tsv_loader.py # TSV file parser

├── data/

│ └── titles.tsv # Movie dataset

├── app.py # Flask app

├── config.py # Configs (dev/test/prod)

└── requirements.txt # dependencies

tests - # Pyttest files

  

## Setting Up Flask Project

  

1. CD into movie_api folder

	`cd movie_api`

2. Create virtual environment
`python -m venv env`
3. Activate and install dependencies
```
soure env\bin\activate
pip install -r requiremenents
```
4. Download and unpack movie data title.basics.tsv.gz at [IMDb Data Files Download](https://datasets.imdbws.com/). Place csv file data folder.

  

## The Repository Classes

  

The InMemoryMovieRepository class takes around 30 seconds to load all 50000 movie records and 137 milliseconds to filter search records with the word 'Biography'. This is the amount of time it takes to parse the records from the TSV file. Shifting to the CachedMovieRepository, the genre filter search is about 10ms faster. Marginal gains of 12% that may translate better on larger datasets.

  

### Database Repositories

  

AnalyticsMovieRepository, FilteredMovieRepository, CachedMovieRepository, and CachedMovieRepository are all in-memory repositories that inherit from the InMemoryMovieRepositor . However, what this design pattern enables us to do is also implement repositories for Databases.

  

#### SQLiteMovieRepository

  

This is a top-level implementation of the base class that incorporates all the functionality of the in-memory classes. Initially imports all the records from the TSV file and implements all the class methods spread across the in-memory classes.

  

## Testing Strategy

The ephemeral nature of the `InMemoryMovieRepository` repository makes it the prime candidate for use in testing as a 'mock repository'. We will use a smaller sample for test data and start fresh with clean context for every test run. We have a small sample of 10 movies on which we will perform a few operations and a few asserts to see what's working.

```

Traditional Testing: Repository Pattern Testing:

Models → Mock DB → Service Models → InMemory Repo → Service

(Complex setup) (Simple, clean)

  

@mock.patch('database') repo = InMemoryMovieRepository(test_data.tsv)

@mock.patch('query') service = MovieService(repo)

# Lots of boilerplate # Ready to test

```

### Test Suite

  

1. Repository Tests

2. Service Tests

3. Controller Tests

  

### Libraries - Pytest

We use pytest to run tests.

```

# run all tests

pytests tests/

```

Run specific test

`pytest tests/<test-file>.py`