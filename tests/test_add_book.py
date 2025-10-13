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


def test_add_book_valid_input(in_memory_db):
    """Test adding a book with valid input."""
    """'The book' will be added into catelog with avalibility of 10"""
    success, message = library_service.add_book_to_catalog("The Book", "The Author", "1234567890986", 10)
    
    assert success == True
    assert "successfully added" in message

def test_add_book_invalid_isbn_too_short(in_memory_db):
    """Test adding a book with ISBN too short."""
    success, message = library_service.add_book_to_catalog("Test Book", "Test Author", "123456789", 6)
    
    assert success == False
    assert "13 digits" in message

def test_add_book_invalid_isbn_too_long(in_memory_db):
    """Test adding a book with ISBN too long."""
    success, message = library_service.add_book_to_catalog("Test Book", "Test Author", "123456786667901234", 5)

    assert success == False
    assert "13 digits" in message

def test_add_book_empty_title():
    """Test adding a book with an empty title."""
    success, message = library_service.add_book_to_catalog("", "Test Author", "1234567890123", 5)
    
    assert success == False
    assert "Title is required" in message

def test_add_book_negative_copies(in_memory_db):
    """Test adding a book with a negative number of copies."""
    success, message = library_service.add_book_to_catalog("Test Book", "Test Author", "1234567890123", -5)

    assert success == False
    assert "positive integer" in message

# test cases
def test_add_book_zero_copies(in_memory_db):
    """Test adding a book with zero copies."""
    success, message = library_service.add_book_to_catalog("separate", "Test separate", "7777777777777", 5)

    assert success == True
    assert "successfully added" in message

# test cases added
def test_add_book_invalid_author(in_memory_db):
    """Test adding a book with an invalid author."""
    success, message = library_service.add_book_to_catalog("Test Book", "", "1234567890123", 5)

    assert success == False
    assert "Author is required" in message

def test_add_book_duplicate_isbn(in_memory_db):
    """Test adding a book with a duplicate ISBN."""
    success, message = library_service.add_book_to_catalog("Another Book", "Another Author", "9780451524935", 3)

    assert success == False
    assert "already exists" in message

def test_add_book_with_title_length_too_long(in_memory_db):
    """Test adding a book with a title that is too long."""
    long_title = "A" * 201
    success, message = library_service.add_book_to_catalog(long_title, "Test Author", "1234567890123", 5)

    assert success == False
    assert "less than 200" in message

def test_add_book_with_author_length_too_long(in_memory_db):
    """Test adding a book with an author name that is too long."""
    long_author = "A" * 101
    success, message = library_service.add_book_to_catalog("Test Book", long_author, "1234567890123", 5)

    assert success == False
    assert "less than 100" in message

def test_borrow_insert_fail(monkeypatch):
    monkeypatch.setattr(library_service, "insert_book", lambda *args, **kwargs: False)    
    success, message = library_service.add_book_to_catalog("Fail Book", "Fail Author", "9999999999999", 5)
    
    assert success == False
    assert "adding" in message

