"""
Library Service Module - Business Logic Functions
Contains all the core business logic for the Library Management System
"""
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from database import (
    get_book_by_id, get_book_by_isbn, get_patron_borrow_count,
    insert_book, insert_borrow_record, update_book_availability,
    update_borrow_record_return_date, get_all_books, get_patron_borrowed_books,
    get_db_connection
)

def add_book_to_catalog(title: str, author: str, isbn: str, total_copies: int) -> Tuple[bool, str]:
    """
    Add a new book to the catalog.
    Implements R1: Book Catalog Management
    
    Args:
        title: Book title (max 200 chars)
        author: Book author (max 100 chars)
        isbn: 13-digit ISBN
        total_copies: Number of copies (positive integer)
        
    Returns:
        tuple: (success: bool, message: str)
    """
    # Input validation
    if not title or not title.strip():
        return False, "Title is required."
    
    if len(title.strip()) > 200:
        return False, "Title must be less than 200 characters."
    
    if not author or not author.strip():
        return False, "Author is required."
    
    if len(author.strip()) > 100:
        return False, "Author must be less than 100 characters."
    
    if len(isbn) != 13:
        return False, "ISBN must be exactly 13 digits."
    
    if not isinstance(total_copies, int) or total_copies <= 0:
        return False, "Total copies must be a positive integer."
    
    # Check for duplicate ISBN
    existing = get_book_by_isbn(isbn)
    if existing:
        return False, "A book with this ISBN already exists."
    
    # Insert new book
    success = insert_book(title.strip(), author.strip(), isbn, total_copies, total_copies)
    if success:
        return True, f'Book "{title.strip()}" has been successfully added to the catalog.'
    else:
        return False, "Database error occurred while adding the book."

def borrow_book_by_patron(patron_id: str, book_id: int) -> Tuple[bool, str]:
    """
    Allow a patron to borrow a book.
    Implements R3 as per requirements  
    
    Args:
        patron_id: 6-digit library card ID
        book_id: ID of the book to borrow
        
    Returns:
        tuple: (success: bool, message: str)
    """
    # Validate patron ID
    if not patron_id or not patron_id.isdigit() or len(patron_id) != 6:
        return False, "Invalid patron ID. Must be exactly 6 digits."
    
    # Check if book exists and is available
    book = get_book_by_id(book_id)
    if not book:
        return False, "Book not found."
    
    if book['available_copies'] <= 0:
        return False, "This book is currently not available."
    
    # Check patron's current borrowed books count
    current_borrowed = get_patron_borrow_count(patron_id)
    
    ############### greater than or equal to
    if current_borrowed >= 5:
        return False, "You have reached the maximum borrowing limit of 5 books."
    
    ######### added an if statement to make sure each patron can only borrow one book from each book id
    books = get_patron_borrowed_books(patron_id)
    for book in books:
        if book['book_id'] == book_id:
            return False, "You can only borrow the same book once."
    ########## changes
    # Create borrow record
    borrow_date = datetime.now()
    due_date = borrow_date + timedelta(days=14)
    
    # Insert borrow record and update availability
    borrow_success = insert_borrow_record(patron_id, book_id, borrow_date, due_date)
    if not borrow_success:
        return False, "Database error occurred while creating borrow record."
    
    availability_success = update_book_availability(book_id, -1)
    if not availability_success:
        return False, "Database error occurred while updating book availability."
    
    return True, f'Successfully borrowed "{book["title"]}". Due date: {due_date.strftime("%Y-%m-%d")}.'

def return_book_by_patron(patron_id: str, book_id: int) -> Tuple[bool, str]:
    """
    Process book return by a patron.
    Args:
        patron_id: 6-digit library card ID
        book_id: ID of the book to borrow
        
    Returns:
        tuple: (success: bool, message: str)
    
    Assume all book have a separate book id, 
    when returning, only book with that book id will be returned

    Implement R4 as per requirements
    """
    # Validate patron ID
    if not patron_id or not patron_id.isdigit() or len(patron_id) != 6:
        return False, "Invalid patron ID. Must be exactly 6 digits."
    
    # book id assumed to be positive integer(no 0 or negative number)
    # Check if book exists
    book = get_book_by_id(book_id)
    if not book:
        return False, "Does not found any book with that book ID"
    # Check if book full avaliability
    if book['available_copies'] == book['total_copies']:
        return False, " This book is at its full availability"

    # Check if book is borrowed by the patron given
    borrowed_books = get_patron_borrowed_books(patron_id)
    is_borrowed = False
    for book in borrowed_books:
        if book_id == book['book_id']:
            is_borrowed = True
    
    if not is_borrowed:
        return False, "This book with this book id is not borrowed by patron"

    # Calculates and displays any late fees owed
    # calculate before update to ensure the fee is right
    late_dict = json.loads(calculate_late_fee_for_book(patron_id, book_id))

    # Update book availablility
    update_book_availability(book_id, 1)

    # Records return date
    update_borrow_record_return_date(patron_id, book_id, datetime.now())

    return True,f"Fee amount owed: ${late_dict['fee_amount']:.2f}\nDays overdue: {late_dict['days_overdue']}\nStatus: {late_dict['status']}"

def calculate_late_fee_for_book(patron_id: str, book_id: int) -> Dict:
    """
    Calculate late fees for a specific book.

    Args:
        patron_id: 6-digit library card ID
        book_id: ID of the book to borrow (greater than or equal to 1)
        
    Returns:
        Dict{'fee_amount':float,
        'days_overdue': int,
        'status': str}
    
    Implement R5 as per requirements 
    """
    book_fee = 0.0
    days_over = 0
    msg = "This book is not overdue"
    # Validate patron ID
    if not patron_id or not patron_id.isdigit() or len(patron_id) != 6:
        return json.dumps({ 
        'fee_amount': book_fee,
        'days_overdue': days_over,
        'status': "This is invalid patron id"})


    # Check if book exists
    # book id should be greater than or equal to 1
    if book_id < 1:
        return json.dumps({'fee_amount': book_fee,
        'days_overdue': days_over,
        'status': "invalid book id"})
    
    book = get_book_by_id(book_id)
    if not book:
        return json.dumps({ 
        'fee_amount': book_fee,
        'days_overdue': days_over,
        'status': "Book not found"})
    
    # assume if 6 digit number, then for sure there will be record
    borrowed_books = get_patron_borrowed_books(patron_id)

    # this patron currently has no borrowed books in record
    if borrowed_books==[]:
        return json.dumps({ 
        'fee_amount': 0.00,
        'days_overdue': 0,
        'status': 'No charges avaliable for this patron'
    })
    
    # Look for the one book with book id
    for book in borrowed_books:
        book_fee = 0.0
        # covert to date to ignore the hour subtraction. 2025-10-11 17:00 to 2025-10-11
        due_date = book['due_date'].date()
        today = (datetime.now()).date()
        # found the book, start calculation
        if book['book_id'] == book_id:
            if (due_date<today):  ##########test with >
                msg = "Book overdue"
                # days_over = (due_date - today).days ######test use
                
                # days_over = 20 #and test with daysover by 20
                days_over = (today - due_date).days # right statement
                if days_over <= 7:
                    book_fee = days_over*0.5
                elif days_over > 7:
                    book_fee = 7 * 0.5 + (days_over-7) * 1.0
            break
    if book_fee > 15.0:
        book_fee = 15.0
    #Fee amount owed: $6.50 Days overdue: 10 Status: Book(s) overdue
    # return the calculated values
    return json.dumps({ 
        'fee_amount': book_fee,
        'days_overdue': days_over,
        'status': msg
    })
    

def search_books_in_catalog(search_term: str, search_type: str) -> List[Dict]:
    """
    Search for books in the catalog using search term and search type

    Args:
        search_term: str, user input, case-insesitive
        search_type: str, user choice, case-insesitive
        
    Returns:
        List[Dict]: [{first book detail},{second book detail}....]
        [] if no book match

    Implement R6 as per requirements
    """
    all_books = get_all_books()
    
    # wrong search type - return empty list
    if search_type.lower() != "title" and search_type.lower() != "author" and search_type.lower() != "isbn":
        return []
    match_book = []
    
    for book in all_books:
        found = False
        if search_type.lower() == "title": # Title search: Partial matching, case-insensitive 
            if search_term.lower() in book['title'].lower():
                found = True
        elif search_type.lower() == "author": # Author search: Partial matching, case-insensitive
            if search_term.lower() in book['author'].lower(): 
                found = True
        elif search_type.lower() == "isbn":# ISBN search: Exact matching
            if search_term == book['isbn']:
                found = True
        if found:
            match_book.append(book)
            #match_book.append({'ID':book['id'],'Title':book['title'],'Author':book['author'],'ISBN':book['isbn'],'available_copies':book['available_copies']})
    return match_book

def get_patron_status_report(patron_id: str) -> Dict:
    """
    Get status report for a patron.

    Args:
        patron id: 6-digit ID
        
    Returns:
        Dict: {
        'borrowed_book_with_due_date': List[Dict], currently borrowed
        'fee_amount':float,total fee for all the borrowed book
        'currently_borrowed_number':int,
        'history':history, List[Dict],currently borrowed and used borrowed
        }
        {} if no status
    
    Implement R7 as per requirements
    """

    # Validate patron ID
    if not patron_id or not patron_id.isdigit() or len(patron_id) != 6:
        return {}
    
    books = get_patron_borrowed_books(patron_id)
    total_fee = 0
    # Currently borrowed books with due dates
    # list of dict
    borrowed_books = []
    for book in books:
        book_fee = json.loads(calculate_late_fee_for_book(patron_id,book['book_id']))['fee_amount']
        # Total late fees owed
        total_fee += book_fee
        book['current_fee'] = book_fee
        borrowed_books.append(book)
    
    # Number of books currently borrowed
    borrowed_count = get_patron_borrow_count(patron_id)
    
    """Get all borrowing record for this patron from the database."""
    # Borrowing history
    # assuming want the borrows records from the database
    conn = get_db_connection()
    records = conn.execute('''
        SELECT * FROM borrow_records WHERE patron_id = ? ORDER BY borrow_date
    ''', (patron_id,)).fetchall()
    conn.close()
    # history is a list of dict
    ###########maybe add title
    history = [dict(book) for book in records]
    return {
        'borrowed_book_with_due_date': borrowed_books,
        'fee_amount':total_fee,
        'currently_borrowed_number':borrowed_count,
        'history':history
        }
