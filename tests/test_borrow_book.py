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
        ('1984', 'George Orwell', '9780451524935', 3),
        ('Pride and Prejudice', 'Jane Austen', '9781503290563', 4),
        ('Moby Dick', 'Herman Melville', '9781503280786', 2),
        ('The Catcher in the Rye', 'J.D. Salinger', '9780316769488', 5),
        ('The Hobbit', 'J.R.R. Tolkien', '9780345339683', 4),
        ('Fahrenheit 451', 'Ray Bradbury', '9781451673319', 2),
        ('Brave New World', 'Aldous Huxley', '9780060850524', 1)
    ]
    for title, author, isbn, copies in sample_books:
        conn.execute('''
            INSERT INTO books (title, author, isbn, total_copies, available_copies)
            VALUES (?, ?, ?, ?, ?)
        ''', (title, author, isbn, copies, copies))
    conn.execute('''
        INSERT INTO borrow_records (patron_id, book_id, borrow_date, due_date)
        VALUES (?, ?, ?, ?)
    ''', ('999999', 6,
          (datetime.now() - timedelta(days=30)).isoformat(),
          (datetime.now() - timedelta(days=16)).isoformat()))
    conn.execute('''
        INSERT INTO borrow_records (patron_id, book_id, borrow_date, due_date)
        VALUES (?, ?, ?, ?)
    ''', ('000000', 9,
          (datetime.now() - timedelta(days=30)).isoformat(),
          (datetime.now() - timedelta(days=16)).isoformat()))
    borrowed_book_ids = [1, 2, 4, 5, 7]
    for book_id in borrowed_book_ids:
        conn.execute('''
            INSERT INTO borrow_records (patron_id, book_id, borrow_date, due_date)
            VALUES (?, ?, ?, ?)
        ''', ('123456', book_id,
            (datetime.now() - timedelta(days=5)).isoformat(),
            (datetime.now() + timedelta(days=9)).isoformat()))
        conn.execute('UPDATE books SET available_copies = available_copies - 1 WHERE id = ?', (book_id,))
        conn.execute('UPDATE books SET available_copies = 4 WHERE id = 6')
        conn.execute('UPDATE books SET available_copies = 0 WHERE id = 9')
    conn.commit()

    # Patch get_db_connection to **always return the same connection**
    monkeypatch.setattr(database, "get_db_connection", lambda: NonClosingConnection(conn))

    yield conn  # keep connection alive during test
    conn.close()

def test_borrow_book_by_valid_patron(in_memory_db):
    """Test borrowing a book by a patron."""

    success, message = library_service.borrow_book_by_patron("111111", 7)

    assert success == True
    assert "Successfully borrowed" in message

def test_borrow_book_by_short_patron(in_memory_db):
    """Test borrwing a book with patron too short."""
    success, message = library_service.borrow_book_by_patron("1", 2)
    
    assert success == False
    assert "6 digits" in message

def test_borrow_book_by_invalid_book_id(in_memory_db):
    """Test borrwing a book non-exist book id."""
    success, message = library_service.borrow_book_by_patron("012345", -1)
    
    assert success == False
    assert "not found" in message

def test_borrow_book_by_wrong_type_patron_str(in_memory_db):
    """Test borrwing a book with str type patron."""
    success, message = library_service.borrow_book_by_patron("somewe", 6)
    
    assert success == False
    assert "Invalid patron ID" in message

def test_borrow_book_by_wrong_type_patron_None(in_memory_db):
    """Test borrwing a book with None patron."""
    success, message = library_service.borrow_book_by_patron(None, 6)
    
    assert success == False
    assert "Invalid patron ID" in message

def test_borrow_book_reach_limit(in_memory_db):
    """Test borrwing a patron id that borrowed more than 5 books."""
    """assume patron id 123456 has borrowed 5 books"""
    success, message = library_service.borrow_book_by_patron("123456", 3)
    assert "maximum" in message
    assert success == False
    assert "maximum" in message
    #book id 4 is test book with 6 copies

# added test case
def test_borrow_book_with_no_copies(in_memory_db):
    """Test borrowing a book that has no available copies."""
    success, message = library_service.borrow_book_by_patron("444444", 9)
    assert success == False
    assert "not available" in message

def test_borrow_book_twice_same_book(in_memory_db):
    """Test borrwing a patron id that borrowed the same book twice."""
    success, message = library_service.borrow_book_by_patron("999999", 6)
    assert success == False
    assert "once" in message

def test_borrow_insert_fail(in_memory_db,monkeypatch):
    monkeypatch.setattr(library_service, "insert_borrow_record", lambda *args, **kwargs: False)
    monkeypatch.setattr(library_service, "update_book_availability", lambda *args, **kwargs: True)
    
    success, message = library_service.borrow_book_by_patron("111111", 1)
    
    assert success == False
    assert "creating" in message

def test_borrow_update_fail(in_memory_db,monkeypatch):
    monkeypatch.setattr(library_service, "update_book_availability", lambda *args, **kwargs: False)
    monkeypatch.setattr(library_service, "insert_borrow_record", lambda *args, **kwargs: True)
    
    success, message = library_service.borrow_book_by_patron("111111", 1)
    
    assert success == False
    assert "updating" in message