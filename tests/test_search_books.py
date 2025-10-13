import pytest
import json
import pytest
import sqlite3
import library_service
import database
from datetime import datetime, timedelta

class NonClosingConnection:
    def __init__(self, conn):
        self._conn = conn

    def __getattr__(self, name):
        # Delegate all attribute access to the original connection
        return getattr(self._conn, name)

    def close(self):
        # Ignore close calls during tests
        pass
@pytest.fixture
def in_memory_db(monkeypatch):
    """Provide a single in-memory SQLite DB instead of the real library.db."""
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row

    # Create tables
    conn.execute('''CREATE TABLE books (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        author TEXT NOT NULL,
        isbn TEXT UNIQUE NOT NULL,
        total_copies INTEGER NOT NULL,
        available_copies INTEGER NOT NULL
    )''')

    conn.execute('''CREATE TABLE borrow_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        patron_id TEXT NOT NULL,
        book_id INTEGER NOT NULL,
        borrow_date TEXT NOT NULL,
        due_date TEXT NOT NULL,
        return_date TEXT,
        FOREIGN KEY (book_id) REFERENCES books (id)
    )''')

    # Insert sample books and borrow records
    sample_books = [
        ('The Great Gatsby', 'F. Scott Fitzgerald', '9780743273565', 3),
        ('To Kill a Mockingbird', 'Harper Lee', '9780061120084', 2),
        ('1984', 'George Orwell', '9780451524935', 1),
        ('Pride and Prejudice', 'Jane Austen', '9781503290563', 4),
        ('Moby Dick', 'Herman Melville', '9781503280786', 2),
        ('The Catcher in the Rye', 'J.D. Salinger', '9780316769488', 5)
    ]
    for title, author, isbn, copies in sample_books:
        conn.execute('''
            INSERT INTO books (title, author, isbn, total_copies, available_copies)
            VALUES (?, ?, ?, ?, ?)
        ''', (title, author, isbn, copies, copies))

    conn.execute('''
        INSERT INTO borrow_records (patron_id, book_id, borrow_date, due_date)
        VALUES (?, ?, ?, ?)
    ''', ('123456', 3,
          (datetime.now() - timedelta(days=5)).isoformat(),
          (datetime.now() + timedelta(days=9)).isoformat()))
    conn.execute('''
        INSERT INTO borrow_records (patron_id, book_id, borrow_date, due_date)
        VALUES (?, ?, ?, ?)
    ''', ('999999', 6,
          (datetime.now() - timedelta(days=30)).isoformat(),
          (datetime.now() - timedelta(days=16)).isoformat()))

    conn.execute('UPDATE books SET available_copies = 0 WHERE id = 3')
    conn.execute('UPDATE books SET available_copies = 4 WHERE id = 6')

    conn.commit()

    # Patch get_db_connection to **always return the same connection**
    monkeypatch.setattr(database, "get_db_connection", lambda: NonClosingConnection(conn))

    yield conn  # keep connection alive during test
    conn.close()
"""assume the function has been implemented
with returned value in list of dict(keys: ID,Titile,Author,ISBN,Availability)
"""
# made changes to the key of dict
def test_search_book_with_ISBN(in_memory_db):
    """Test search book with valid ISBN"""
    result = library_service.search_books_in_catalog("9780061120084", "isbn")
    
    assert result[0]['isbn'] == '9780061120084'
    assert result[0]['title'] == 'To Kill a Mockingbird'
    assert result[0]['author'] == 'Harper Lee'

def test_search_book_with_short_ISBN(in_memory_db):
    """Test search book with invalid ISBN that is too short"""
    result = library_service.search_books_in_catalog("978006", "isbn")

    assert len(result) == 0

def test_search_book_with_title(in_memory_db):
    """Test search book with valid title"""
    result = library_service.search_books_in_catalog("1984", "title")
    
    assert result[0]['isbn'] == '9780451524935'
    assert result[0]['title'] == '1984'
    assert result[0]['author'] == 'George Orwell'

def test_search_book_with_author(in_memory_db):
    """Test search book with valid title"""
    result = library_service.search_books_in_catalog("F. Scott Fitzgerald", "author")
    
    assert result[0]['isbn'] == '9780743273565'
    assert result[0]['title'] == 'The Great Gatsby'
    assert result[0]['author'] == 'F. Scott Fitzgerald'

def test_search_book_with_author_lowercase(in_memory_db):
    """Test search book with valid author in lowercase and uppercase"""
    result1 = library_service.search_books_in_catalog("f. scott fitzgerald", "author")
    result2 = library_service.search_books_in_catalog("F. Scott Fitzgerald", "author")
    
    assert result1 == result2

def test_search_book_with_ISBN_type(in_memory_db):
    """Test if returned list have all wanted elements"""
    result = library_service.search_books_in_catalog("9780061120084", "isbn")
    
    assert "id" in result[0]
    assert "author" in result[0]
    assert "isbn" in result[0]
    assert "available_copies" in result[0]

