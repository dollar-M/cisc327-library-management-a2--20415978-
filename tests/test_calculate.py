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
    ''', ('111111', 5,
          (datetime.now() - timedelta(days=18)).isoformat(),
          (datetime.now() - timedelta(days=4)).isoformat()))
    conn.execute('''
        INSERT INTO borrow_records (patron_id, book_id, borrow_date, due_date)
        VALUES (?, ?, ?, ?)
    ''', ('999999', 6,
          (datetime.now() - timedelta(days=30)).isoformat(),
          (datetime.now() - timedelta(days=16)).isoformat()))

    conn.execute('UPDATE books SET available_copies = 0 WHERE id = 3')
    conn.execute('UPDATE books SET available_copies = 4 WHERE id = 6')
    conn.execute('UPDATE books SET available_copies = 1 WHERE id = 5')
    conn.commit()

    # Patch get_db_connection to **always return the same connection**
    monkeypatch.setattr(database, "get_db_connection", lambda: NonClosingConnection(conn))

    yield conn  # keep connection alive during test
    conn.close()


"""assume the function has been implemented"""
def test_caluculate_fee_with_valid_input(in_memory_db):
    """Test if the returned result is with the correct type"""
    result = json.loads(library_service.calculate_late_fee_for_book("123456", 4))
    assert "fee_amount" in result
    assert "days_overdue" in result
    assert "status" in result
    assert isinstance(result['fee_amount'],float)
    assert isinstance(result['days_overdue'],int)
    assert isinstance(result['status'],str)    

def test_calculate_fee_with_not_borrowed_book(in_memory_db):
    """Test calculated fee with book that is not borrowed"""
    result = json.loads(library_service.calculate_late_fee_for_book("123456",5))
    assert result['fee_amount']==0.0
    assert result['days_overdue']==0

def test_calculate_fee_with_borrowed_book(in_memory_db):
    """Test fee with borreowed book """
    # chnaged book id from 5 to 1
    result = json.loads(library_service.calculate_late_fee_for_book("999999", 6))
    assert result['fee_amount']!=0.0
    assert result['days_overdue']!=0

def test_calculate_empty_patron_id(in_memory_db):
    """Test calculate fee for a book with empty patron id."""
    result = json.loads(library_service.calculate_late_fee_for_book("", 1))

    assert "invalid patron id" in result['status']

def test_calculate_invalid_book_id(in_memory_db):
    """Test calculate fee fro a book with invalid book id."""
    result = json.loads(library_service.calculate_late_fee_for_book("123456", -1))

    assert "invalid book id" in result['status']

# added test case
def test_calculate_book_overdue_fee(in_memory_db):
    """Test calculate fee for a book that is overdue for patron id 111111 that overdue for 4 days."""
    result = json.loads(library_service.calculate_late_fee_for_book("111111", 5))

    assert result['fee_amount'] == 2.0
    assert result['days_overdue'] == 4
    assert "overdue" in result['status']

def test_calculate_book_by_patron_id_never_borrowed(in_memory_db):
    """Test calculate fee for a book that was never borrowed by the patron."""
    result = json.loads(library_service.calculate_late_fee_for_book("101010", 1))

    assert result['fee_amount'] == 0.00
    assert result['days_overdue'] == 0
    assert "No charges" in result['status']

def test_calculate_book_with_nonexistent_book_id(in_memory_db):
    """Test calculate fee for a book that does not exist."""
    result = json.loads(library_service.calculate_late_fee_for_book("123456", 999))

    assert result['fee_amount'] == 0.00
    assert result['days_overdue'] == 0
    assert "Book not found" in result['status']