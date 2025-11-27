from flask import url_for
import subprocess
import time
import pytest
from datetime import datetime, timedelta
import requests
from playwright.sync_api import Page, expect
import os
import tempfile
import shutil

@pytest.fixture(scope="session", autouse=True)
def flask_server():
    # use a temp directory for the test DB to guarantee isolation
    tmpdir = tempfile.mkdtemp()
    test_db_path = os.path.join(tmpdir, "test_library.db")

    env = os.environ.copy()
    # tell the app where to create the DB; implement app support for DATABASE_PATH
    env["DATABASE_PATH"] = test_db_path
    env["FLASK_ENV"] = "testing"

    # remove any leftover file just in case
    if os.path.exists(test_db_path):
        os.remove(test_db_path)

    proc = subprocess.Popen(["python", "app.py"], env=env)

    # Wait longer for Flask to be up (increase timeout)
    for _ in range(60):  # 60 * 0.5s = 30s max
        try:
            r = requests.get("http://127.0.0.1:5000")
            if r.status_code == 200:
                break
        except Exception:
            time.sleep(0.5)
    else:
        proc.terminate()
        shutil.rmtree(tmpdir)
        raise RuntimeError("Flask server did not start in time")

    yield

    proc.terminate()
    proc.wait()
    # cleanup DB
    shutil.rmtree(tmpdir)


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
    page.get_by_role("textbox", name="Search Term").fill("It")
    page.get_by_role("button", name="🔍 Search").click()
    expect(page.get_by_role("cell", name="It is rainy day")).to_be_visible()
    expect(page).to_have_url("http://127.0.0.1:5000/search?q=It&type=title")

    page.get_by_role("textbox", name="Patron ID").fill("121212")
    page.get_by_role("button", name="Borrow").click()
    expect(page).to_have_url("http://127.0.0.1:5000/catalog")



""""Flow: go to catalog, check book visible, borrow book with id 121212, check message, go to return/search/patron report page, input id 121212, check report."""
def test_user_navigate_all_pages(page: Page):
    page.goto("http://127.0.0.1:5000")
    # navigate to catalog
    page.get_by_role("link", name="📖 Catalog").click()
    # check the book is visible
    expect(page.get_by_role("cell", name="The Book")).to_be_visible()

    #borrow the book with patron ID 121212
    page.locator("tr:nth-child(9) > td:nth-child(6) > form > input:nth-child(2)").click()
    page.locator("tr:nth-child(9) > td:nth-child(6) > form > input:nth-child(2)").fill("121212")
    page.locator("tr:nth-child(9) > td:nth-child(6) > form > .btn").click()
    # validate navigation to catalog page
    expect(page).to_have_url("http://127.0.0.1:5000/catalog")

    # navigate to add book
    page.get_by_role("link", name="➕ Add Book").click()
    expect(page).to_have_url("http://127.0.0.1:5000/add_book")
    # navigate to return book
    page.get_by_role("link", name="↩️ Return Book").click()
    expect(page).to_have_url("http://127.0.0.1:5000/return")
    # navigate to search
    page.get_by_role("link", name="🔍 Search").click()
    expect(page).to_have_url("http://127.0.0.1:5000/search")
    # navigate to patron report
    page.get_by_role("link", name="📋 Patron Report").click()
    expect(page).to_have_url("http://127.0.0.1:5000/user/profile")

    #check patron report for patron ID 121212
    page.get_by_role("textbox", name="Patron ID*").click()
    page.get_by_role("textbox", name="Patron ID*").fill("121212")
    page.get_by_role("button", name="Load Patron Report").click()

    expect(page.get_by_role("cell", name="The Book")).to_be_visible()



#############difficaulties encountered#############
# 1. have to open a new terminal to run the flask app while running the test
# 2. did not realize user flow change database, so some tests failed when run multiple times
# 3. get_by_text have to match exactly the text shown on the page, otherwise it will fail