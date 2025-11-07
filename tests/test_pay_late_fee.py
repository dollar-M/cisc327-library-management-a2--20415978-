import pytest
from unittest.mock import Mock
from services import library_service
from services.payment_service import PaymentGateway
import json
import time
"""
network error exception handling
"""

def test_pay_fee_success(mocker):
    """Test successful payment of late fee."""
    mock_gateway = Mock(spec=PaymentGateway)
    mock_cal = mocker.patch("services.library_service.calculate_late_fee_for_book", return_value={'fee_amount': 3,'days_overdue': 6,'status': "Book overdue"})
    mocker.patch("services.library_service.get_book_by_id", return_value={'id': 2, 'title': "Test Book"})
    mock_gateway.process_payment.return_value = True, f"txn_123456_1730946927", f"Payment of $3 called successfully"
    

    result,msg,opmsg = library_service.pay_late_fees("123456", 2,payment_gateway=mock_gateway)

    assert result is True
    assert "Payment successful" in msg
    assert "called" in msg
    mock_cal.assert_called_once_with("123456", 2)
    mock_gateway.process_payment.assert_called_once_with(patron_id='123456', amount=3, description="Late fees for 'Test Book'")

def test_pay_fee_declined_by_gateway(mocker):
    """Test payment declined by gateway."""
    mock_gateway = Mock(spec=PaymentGateway)
    mocker.patch("services.library_service.calculate_late_fee_for_book", return_value={'fee_amount': 3,'days_overdue': 6,'status': "Book overdue"})
    mocker.patch("services.library_service.get_book_by_id", return_value={'id': 2, 'title': "Test Book"})
    mock_gateway.process_payment.return_value = False, "", "Payment declined: amount exceeds limit"
    

    result,msg,opmsg = library_service.pay_late_fees("123456", 2,payment_gateway=mock_gateway)

    assert result is False
    assert "Payment failed" in msg
    mock_gateway.process_payment.assert_called_once_with(patron_id='123456', amount=3, description="Late fees for 'Test Book'")

def test_invalid_ID(mocker):
    """Test invalid patron ID (verify mock NOT called)."""
    mock_gateway = Mock(spec=PaymentGateway)
    mocker.patch("services.library_service.calculate_late_fee_for_book", return_value={'fee_amount': 3,'days_overdue': 6,'status': "Book overdue"})
    mocker.patch("services.library_service.get_book_by_id", return_value={'id': 2, 'title': "Test Book"})
    mock_gateway.process_payment.return_value = True, f"txn_123456_1730946927", f"Payment of $3 processed successfully"
    

    result,msg,opmsg = library_service.pay_late_fees("123", 2,payment_gateway=mock_gateway)

    assert result is False
    assert "Invalid patron ID" in msg
    mock_gateway.process_payment.assert_not_called()

def test_zero_late_fees (mocker):
    """Test zero late fees (verify mock NOT called)."""
    mock_gateway = Mock(spec=PaymentGateway)
    mocker.patch("services.library_service.calculate_late_fee_for_book", return_value={'fee_amount': 0,'days_overdue': 0,'status': "Book not overdue"})
    mocker.patch("services.library_service.get_book_by_id", return_value={'id': 2, 'title': "Test Book"})
    mock_gateway.process_payment.return_value = True, f"txn_123456_1730946927", f"Payment of $3 called successfully"
    

    result,msg,opmsg = library_service.pay_late_fees("123456", 2,payment_gateway=mock_gateway)

    assert result is False
    assert "No late fees" in msg
    mock_gateway.process_payment.assert_not_called()

def test_network_error_exception_handling(mocker):
    """Test successful payment of late fee."""
    mock_gateway = Mock(spec=PaymentGateway)
    mock_cal = mocker.patch("services.library_service.calculate_late_fee_for_book", return_value={'fee_amount': 3,'days_overdue': 6,'status': "Book overdue"})
    mocker.patch("services.library_service.get_book_by_id", return_value={'id': 2, 'title': "Test Book"})
    mock_gateway.process_payment.return_value = ConnectionError("Network error")
    
    result,msg,opmsg = library_service.pay_late_fees("123456", 2,payment_gateway=mock_gateway)

    assert result is False
    assert "error" in msg
    mock_gateway.process_payment.assert_called_once_with(patron_id='123456', amount=3, description="Late fees for 'Test Book'")


