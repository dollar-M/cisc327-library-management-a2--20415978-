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
    monkeypatch.setattr(library_service, "get_db_connection", lambda: NonClosingConnection(conn))
    
    yield conn  # keep connection alive during test
    conn.close()


"""assume the function has been implemented"""
def test_status_report__valid_patron(in_memory_db):
    """Test if the status report have needed element"""
    result = library_service.get_patron_status_report("123456")
    assert "borrowed_book_with_due_date" in result # List[Dict]
    assert "fee_amount" in result 
    assert "currently_borrowed_number" in result
    assert "history" in result # List[Dict]

def test_status_report__valid_patron_type(in_memory_db):
    """Test if the status report have element of correct type"""
    result = library_service.get_patron_status_report("123456")

    assert isinstance(result['borrowed_book_with_due_date'],list) 
    assert isinstance(result['fee_amount'],float)
    assert isinstance(result['currently_borrowed_number'],int)
    assert isinstance(result['history'],list)   

def test_status_report_two_same_valid_patron(in_memory_db):
    """Test same valid patron should give same detail"""
    result2 = library_service.get_patron_status_report("123456")
    result1 = library_service.get_patron_status_report("123456")

    assert result1 == result2

def test_status_report_patron_too_long(in_memory_db):
    """Test with patron that is too long, returned dict should be empty"""
    result = library_service.get_patron_status_report("1234565678")

    assert len(result) == 0

def test_status_report_patron_too_short(in_memory_db):
    """Test with patron that is too short, returned dict should be empty"""
    result = library_service.get_patron_status_report("1")

    assert len(result) == 0

def test_status_report_non_numeric_patron(in_memory_db):
    """Test with patron that is non-numeric, returned dict should be empty"""
    result = library_service.get_patron_status_report("hello")

    assert len(result) == 1

