from flask import url_for
import subprocess
import time
import pytest
from datetime import datetime, timedelta
import uuid
import random
import requests
from playwright.sync_api import Page, expect

@pytest.fixture(scope="session", autouse=True)
def flask_server():
    """Start the Flask app in a subprocess for the entire test session."""
    proc = subprocess.Popen(["python", "app.py"])
    
    # Wait for Flask to be up
    for _ in range(20):  # 20 * 0.5s = 10s max
        try:
            r = requests.get("http://127.0.0.1:5000")
            if r.status_code == 200:
                break
        except:
            time.sleep(0.5)
    else:
        proc.terminate()
        raise RuntimeError("Flask server did not start in time")
    
    yield  # tests run here
    
    # Teardown: stop Flask
    proc.terminate()
    proc.wait()


def test_web(page: Page):
    page.goto("http://127.0.0.1:5000")
    expect(page).to_have_title("Library Management System")

"""Test end-to-end user interactions on add book with invalid ISBN."""
def test_user_add_book_with_invalid_isbn(page: Page):
    page.goto("http://127.0.0.1:5000")
    # used command for following: playwright codegen http://127.0.0.1:5000
    # add a book with invalid ISBN
    page.goto("http://127.0.0.1:5000/catalog")
    # go to add book page
    page.get_by_role("link", name="➕ Add Book").click()
    # fill the add book form
    page.get_by_role("textbox", name="Title *").click()
    page.get_by_role("textbox", name="Title *").fill("The python Pulase")
    page.get_by_role("textbox", name="Author *").click()
    page.get_by_role("textbox", name="Author *").fill("VScode")
    page.get_by_role("textbox", name="ISBN *").click()
    page.get_by_role("textbox", name="ISBN *").fill("108531420231")
    page.get_by_role("spinbutton", name="Total Copies *").click()
    page.get_by_role("spinbutton", name="Total Copies *").fill("6")
    # submit the form
    page.get_by_role("button", name="Add Book to Catalog").click()
    # check for validation message
    expect(page).to_have_url("http://127.0.0.1:5000/add_book")
    expect(page.get_by_text("ISBN must be exactly 13 digits.")).to_be_visible()



"""Test end-to-end user interactions on borr search the book using a patron ID."""
def test_user_search_book(page: Page):
    page.goto("http://127.0.0.1:5000")
    # search for a book with partial title that does not exist
    page.get_by_role("link", name="🔍 Search").click()
    page.get_by_role("textbox", name="Search Term").click()
    page.get_by_role("textbox", name="Search Term").fill("I t")
    page.get_by_role("button", name="🔍 Search").click()
    expect(page.get_by_text("No book matched.")).to_be_visible()
    expect(page).to_have_url("http://127.0.0.1:5000/search?q=I+t&type=title")

    # search for a book with partial title that exists
    page.get_by_role("textbox", name="Search Term").click()
    page.get_by_role("textbox", name="Search Term").fill("Great")
    page.get_by_role("button", name="🔍 Search").click()
    expect(page.get_by_role("cell", name="The Great Gatsby")).to_be_visible()



""""Flow: go to catalog, check book visible, borrow book with id 121212, check message, go to return/search/patron report page, input id 121212, check report."""
def test_user_navigate_all_pages(page: Page):
    """book = "Book5 to Borrow"
    author = "Author5"
    isbn = "5050505050505"""
    uid = uuid.uuid4().hex[:10]  # 10 random hex chars

    book   = f"Book Borrow {uid}"
    author = f"Author {uid}"
    isbn = ''.join(random.choices("0123456789", k=13))
    # 6- digit patron ID
    patron = ''.join(random.choices("0123456789", k=6))

    page.goto("http://127.0.0.1:5000")
    # navigate to catalog
    page.get_by_role("link", name="📖 Catalog").click()
    # check the book is visible
    #expect(page.get_by_role("cell", name="The Book")).to_be_visible()

    # navigate to add book
    page.get_by_role("link", name="➕ Add Book").click()
    expect(page).to_have_url("http://127.0.0.1:5000/add_book")
    # add a book to borrow
    page.get_by_role("textbox", name="Title *").click()
    page.get_by_role("textbox", name="Title *").fill(book)
    page.get_by_role("textbox", name="Author *").click()
    page.get_by_role("textbox", name="Author *").fill(author)
    page.get_by_role("textbox", name="ISBN *").click()
    page.get_by_role("textbox", name="ISBN *").fill(isbn)
    page.get_by_role("spinbutton", name="Total Copies *").click()
    page.get_by_role("spinbutton", name="Total Copies *").fill("3")
    # submit the form
    page.get_by_role("button", name="Add Book to Catalog").click()
    expect(page).to_have_url("http://127.0.0.1:5000/catalog")
    # search the book just added
    page.get_by_role("link", name="🔍 Search").click()
    page.get_by_role("textbox", name="Search Term").click()
    page.get_by_role("textbox", name="Search Term").fill(book)
    page.get_by_role("button", name="🔍 Search").click()
    expect(page.get_by_role("cell", name=book)).to_be_visible()
    # borrow the book
    page.get_by_role("textbox", name="Patron ID").click()
    page.get_by_role("textbox", name="Patron ID").fill(patron)
    page.get_by_role("button", name="Borrow").click()
    # check borrow success by check return url
    expect(page).to_have_url("http://127.0.0.1:5000/catalog")




#############difficaulties encountered#############
# 1. have to open a new terminal to run the flask app while running the test
# 2. did not realize user flow change database, so some tests failed when run multiple times
# 3. get_by_text have to match exactly the text shown on the page, otherwise it will fail