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
          (datetime.now() - timedelta(days=20)).isoformat(),
          (datetime.now() - timedelta(days=34)).isoformat()))

    conn.execute('UPDATE books SET available_copies = 0 WHERE id = 3')
    conn.execute('UPDATE books SET available_copies = 4 WHERE id = 6')

    conn.commit()

    # Patch get_db_connection to **always return the same connection**
    monkeypatch.setattr(database, "get_db_connection", lambda: NonClosingConnection(conn))

    yield conn  # keep connection alive during test
    conn.close()

def test_return_book_by_valid_patron(in_memory_db): #msg change
    """Test returning a book by a patron."""
    success, message = library_service.return_book_by_patron("123456", 3)

    assert success == True
    assert "amount" in message

def test_return_book_by_valid_patron_with_wrong_book_id(in_memory_db):
    """Test returning a book with valid patron that does not borrow book id 5."""
    success, message = library_service.return_book_by_patron("222222", 6)

    assert success == False
    assert "not borrowed by patron" in message

def test_return_book_by_short_patron(in_memory_db):
    """Test returning a book with patron too short."""
    success, message = library_service.return_book_by_patron("1", 2)
    
    assert success == False
    assert "6 digits" in message

def test_return_book_by_invalid_book_id(in_memory_db):
    """Test returning a book non-exist book id."""
    success, message = library_service.return_book_by_patron("012345", 0)
    
    assert success == False
    assert "not found" in message

def test_return_book_to_books_not_borrowed(in_memory_db):
    """Test returning a book that was not borrowed."""
    success, message = library_service.return_book_by_patron("999999", 1)
    
    assert success == False
    assert "full availability" in message

## newly added tests
def test_return_book_by_checking_amount(in_memory_db):
    """Test returning a book by a patron."""
    success, message = library_service.return_book_by_patron("999999", 6)

    assert success == True
    assert "amount" in message
    assert "15" in message # can be wrong if date calculation is different


