import pytest
from unittest.mock import Mock
from services import library_service
from services.payment_service import PaymentGateway


def test_refund_fee_success():
    """Test successful refund."""
    mock_gateway = Mock(spec=PaymentGateway)
    mock_gateway.refund_payment.return_value = True, "Refund of $10.5 processed successfully. Refund ID: refund_txn_123456_1730946927_1730946928"
    

    result,msg = library_service.refund_late_fee_payment("txn_123456_1730946927_1730946928", 10.5,payment_gateway=mock_gateway)

    assert result is True
    assert "refund_txn_123456" in msg
    mock_gateway.refund_payment.assert_called_once_with('txn_123456_1730946927_1730946928', 10.5)


def test_invalid_transaction_ID_rejection():
    """Test invalid transaction ID rejection ."""
    mock_gateway = Mock(spec=PaymentGateway)
    mock_gateway.refund_payment.return_value = False, "Invalid transaction ID"
    

    result,msg = library_service.refund_late_fee_payment("123456_1730946927_1730946928", 10.5,payment_gateway=mock_gateway)

    assert result is False
    assert "Invalid transaction" in msg
    mock_gateway.refund_payment.assert_not_called() 

def test_invalid_negative_refund_amounts():
    """Test invalid refund amounts (negative)"""
    mock_gateway = Mock(spec=PaymentGateway)
    mock_gateway.refund_payment.return_value = False, "Invalid refund amount"
    
    result,msg = library_service.refund_late_fee_payment("txn_123456_1730946927_1730946928", -2.5,payment_gateway=mock_gateway)

    assert result is False
    assert "greater than 0" in msg
    mock_gateway.refund_payment.assert_not_called()

def test_invalid_zero_refund_amounts():
    """Test invalid refund amounts (zero)"""
    mock_gateway = Mock(spec=PaymentGateway)
    mock_gateway.refund_payment.return_value = True, "Invalid refund amount"
    
    result,msg = library_service.refund_late_fee_payment("txn_123456_1730946927_1730946928", 0,payment_gateway=mock_gateway)

    assert result is False
    assert "greater than 0" in msg
    mock_gateway.refund_payment.assert_not_called()

def test_invalid_exceed_refund_amounts():
    """Test invalid refund amounts (exceed 15 max)"""
    mock_gateway = Mock(spec=PaymentGateway)
    mock_gateway.refund_payment.return_value = True, "Invalid refund amount"
    
    result,msg = library_service.refund_late_fee_payment("txn_123456_1730946927_1730946928", 16.5,payment_gateway=mock_gateway)

    assert result is False
    assert "exceeds maximum" in msg
    mock_gateway.refund_payment.assert_not_called()


# extra check for exception handling
