#!/user/bin/env python2.7

import unittest
from datetime import date, datetime
from dateutil.relativedelta import relativedelta

from accounting import db
from models import Contact, Invoice, Payment, Policy
from utils import PolicyAccounting

"""
#######################################################
Test Suite for Accounting
#######################################################
"""

class TestCancelPolicy(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.test_agent = Contact('Test Agent', 'Agent')
        cls.test_insured = Contact('Test Insured', 'Named Insured')
        db.session.add(cls.test_agent)
        db.session.add(cls.test_insured)
        db.session.commit()

        cls.policy = Policy('Test Policy', date(2015, 1, 1), 1200)
        db.session.add(cls.policy)
        cls.policy.billing_schedule = "Annual"
        cls.policy.named_insured = cls.test_insured.id
        cls.policy.agent = cls.test_agent.id
        db.session.commit()

    @classmethod
    def tearDownClass(cls):
        db.session.delete(cls.test_insured)
        db.session.delete(cls.test_agent)
        db.session.delete(cls.policy)
        db.session.commit()

    def setUp(self):
        pass

    def tearDown(self):
        for invoice in self.policy.invoices:
            db.session.delete(invoice)

        self.policy.status = 'Active'
        self.policy.status_code = None
        self.policy.status_desc = None
        self.policy.cancel_date = None

        db.session.commit()

    def test_cancel_policy(self):
        pa = PolicyAccounting(self.policy.id)
        pa.cancel_policy('Canceled', 'Fraud', 'description', date(2015, 1, 1))

        self.assertEquals(self.policy.invoices[0].deleted, True)
        self.assertEquals(self.policy.status, 'Canceled')
        self.assertEquals(self.policy.status_code, 'Fraud')
        self.assertEquals(self.policy.status_desc, 'description')
        self.assertEquals(self.policy.cancel_date, date(2015, 1, 1))

    def test_expire_policy(self):
        pa = PolicyAccounting(self.policy.id)
        pa.cancel_policy('Expired', 'Non-Payment')

        self.assertEquals(self.policy.invoices[0].deleted, True)
        self.assertEquals(self.policy.status, 'Expired')
        self.assertEquals(self.policy.status_code, 'Non-Payment')
        self.assertEquals(self.policy.status_desc, None)
        self.assertEquals(self.policy.cancel_date, datetime.now().date())

    def test_cancel_policy_invalid_status(self):
        pa = PolicyAccounting(self.policy.id)
        pa.cancel_policy('Random Status', 'Fraud', 'description', date(2015, 1, 1))

        self.assertEquals(self.policy.invoices[0].deleted, False)
        self.assertEquals(self.policy.status, 'Active')
        self.assertEquals(self.policy.status_code, None)
        self.assertEquals(self.policy.status_desc, None)
        self.assertEquals(self.policy.cancel_date, None)

    def test_cancel_policy_invalid_reason(self):
        pa = PolicyAccounting(self.policy.id)
        pa.cancel_policy('Canceled', 'Random Status Code', 'description', date(2015, 1, 1))

        self.assertEquals(self.policy.invoices[0].deleted, False)
        self.assertEquals(self.policy.status, 'Active')
        self.assertEquals(self.policy.status_code, None)
        self.assertEquals(self.policy.status_desc, None)
        self.assertEquals(self.policy.cancel_date, None)


class TestBillingSchedules(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.test_agent = Contact('Test Agent', 'Agent')
        cls.test_insured = Contact('Test Insured', 'Named Insured')
        db.session.add(cls.test_agent)
        db.session.add(cls.test_insured)
        db.session.commit()

        cls.policy = Policy('Test Policy', date(2015, 1, 1), 1200)
        db.session.add(cls.policy)
        cls.policy.named_insured = cls.test_insured.id
        cls.policy.agent = cls.test_agent.id
        db.session.commit()

    @classmethod
    def tearDownClass(cls):
        db.session.delete(cls.test_insured)
        db.session.delete(cls.test_agent)
        db.session.delete(cls.policy)
        db.session.commit()

    def setUp(self):
        pass

    def tearDown(self):
        for invoice in self.policy.invoices:
            db.session.delete(invoice)
        db.session.commit()

    def test_annual_billing_schedule(self):
        self.policy.billing_schedule = "Annual"
        #No invoices currently exist
        self.assertFalse(self.policy.invoices)
        #Invoices should be made when the class is initiated
        pa = PolicyAccounting(self.policy.id)

        self.assertEquals(len(self.policy.invoices), 1)
        self.assertEquals(self.policy.invoices[0].amount_due, self.policy.annual_premium)

    def test_monthly_billing_schedule(self):
        self.policy.billing_schedule = "Monthly"
        #No invoices currently exist
        self.assertFalse(self.policy.invoices)
        #Create invoices for policy id
        pa = PolicyAccounting(self.policy.id)

        self.assertEquals(len(self.policy.invoices), 12)
        self.assertEquals(self.policy.invoices[0].amount_due, 100)

    def test_twopay_billing_schedule(self):
        self.policy.billing_schedule = "Two-Pay"
        #No invoices currently exist
        self.assertFalse(self.policy.invoices)
        #Create invoices for policy id
        pa = PolicyAccounting(self.policy.id)

        self.assertEquals(len(self.policy.invoices), 2)
        self.assertEquals(self.policy.invoices[0].amount_due, 600)

    def test_quarterly_billing_schedule(self):
        self.policy.billing_schedule = "Quarterly"
        #No invoices currently exist
        self.assertFalse(self.policy.invoices)
        #Create invoices for policy id
        pa = PolicyAccounting(self.policy.id)

        self.assertEquals(len(self.policy.invoices), 4)
        self.assertEquals(self.policy.invoices[0].amount_due, 300)

class TestUpdateBillingSchedule(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.test_agent = Contact('Test Agent', 'Agent')
        cls.test_insured = Contact('Test Insured', 'Named Insured')
        db.session.add(cls.test_agent)
        db.session.add(cls.test_insured)
        db.session.commit()

        cls.policy = Policy('Test Policy', date(2015, 1, 1), 1200)
        db.session.add(cls.policy)
        cls.policy.named_insured = cls.test_insured.id
        cls.policy.agent = cls.test_agent.id
        db.session.commit()

    @classmethod
    def tearDownClass(cls):
        db.session.delete(cls.test_insured)
        db.session.delete(cls.test_agent)
        db.session.delete(cls.policy)
        db.session.commit()

    def setUp(self):
        pass

    def tearDown(self):
        for invoice in self.policy.invoices:
            db.session.delete(invoice)
        db.session.commit()

    def test_update_billing_schedule_quartely_to_annual(self):
        self.policy.billing_schedule = "Quarterly"
        #No invoices currently exist
        self.assertFalse(self.policy.invoices)
        #Invoices should be made when the class is initiated
        pa = PolicyAccounting(self.policy.id)
        #There are 4 invoices in total before updating
        self.assertEqual(len(self.policy.invoices), 4)

        #Call update billing schedule with Annual option
        pa.change_billing_schedule("Annual")

        #There are 5 invoices in total after updating
        self.assertEqual(len(self.policy.invoices), 5)
        #4 are marked as deleted new invoice is not
        self.assertEqual(self.policy.invoices[0].deleted, True)
        self.assertEqual(self.policy.invoices[1].deleted, True)
        self.assertEqual(self.policy.invoices[2].deleted, True)
        self.assertEqual(self.policy.invoices[3].deleted, True)
        self.assertEqual(self.policy.invoices[4].deleted, False)

    def test_update_billing_schedule_annual_to_twopay(self):
        self.policy.billing_schedule = "Annual"
        #No invoices currently exist
        self.assertFalse(self.policy.invoices)
        #Invoices should be made when the class is initiated
        pa = PolicyAccounting(self.policy.id)
        #There is 1 invoice in total before updating
        self.assertEqual(len(self.policy.invoices), 1)

        #Call update billing schedule with Annual option
        pa.change_billing_schedule("Two-Pay")

        #There are 3 invoices in total after updating
        self.assertEqual(len(self.policy.invoices), 3)
        #1 is marked as deleted new invoices are not
        self.assertEqual(self.policy.invoices[0].deleted, True)
        self.assertEqual(self.policy.invoices[1].deleted, False)
        self.assertEqual(self.policy.invoices[2].deleted, False)

    def test_update_billing_schedule_to_incorrect_name(self):
        self.policy.billing_schedule = "Annual"
        #No invoices currently exist
        self.assertFalse(self.policy.invoices)
        #Invoices should be made when the class is initiated
        pa = PolicyAccounting(self.policy.id)
        #There is 1 invoice in total before updating
        self.assertEqual(len(self.policy.invoices), 1)

        #Call change billing schedule with Random option
        pa.change_billing_schedule("Random")

        #There is 1 invoice in total after updating
        self.assertEqual(len(self.policy.invoices), 1)
        #None have been marked as deleted
        self.assertEqual(self.policy.invoices[0].deleted, False)

    def test_update_billing_schedule_to_same_schedule(self):
        self.policy.billing_schedule = "Annual"
        #No invoices currently exist
        self.assertFalse(self.policy.invoices)
        #Invoices should be made when the class is initiated
        pa = PolicyAccounting(self.policy.id)
        #There is 1 invoice in total before updating
        self.assertEqual(len(self.policy.invoices), 1)

        #Call change billing schedule with Random option
        pa.change_billing_schedule("Annual")

        #There is 1 invoice in total after updating
        self.assertEqual(len(self.policy.invoices), 1)
        #None have been marked as deleted
        self.assertEqual(self.policy.invoices[0].deleted, False)


class TestMakePayment(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.agent = Contact('Test Agent', 'Agent')
        cls.insured = Contact('Test Insured', 'Named Insured')
        db.session.add(cls.agent)
        db.session.add(cls.insured)
        db.session.commit()

        cls.test_policy = Policy('Test Policy', date(2015, 1, 1), 1200)
        cls.test_policy.named_insured = cls.insured.id
        cls.test_policy.agent = cls.agent.id
        db.session.add(cls.test_policy)
        db.session.commit()

    @classmethod
    def tearDownClass(cls):
        db.session.delete(cls.insured)
        db.session.delete(cls.agent)
        db.session.delete(cls.test_policy)
        db.session.commit()

    def setUp(self):
        self.payments_made = []

    def tearDown(self):
        for invoice in self.test_policy.invoices:
            db.session.delete(invoice)
        for payment in self.payments_made:
            db.session.delete(payment)
        db.session.commit()

    def test_make_payment(self):
        pa = PolicyAccounting(self.test_policy.id)
        self.payments_made.append(pa.make_payment(self.test_policy.agent, datetime.now().date(), 1200))
        self.assertEqual(1200, self.payments_made[0].amount_paid)

    def test_make_payment_during_pending_cancellation_due_to_nonpay(self):
        pa = PolicyAccounting(self.test_policy.id)
        self.payments_made.append(pa.make_payment(self.test_policy.agent, date(2015, 2, 2), 1200))
        self.assertEquals(len(self.payments_made), 1)


class TestReturnAccountBalance(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.test_agent = Contact('Test Agent', 'Agent')
        cls.test_insured = Contact('Test Insured', 'Named Insured')
        db.session.add(cls.test_agent)
        db.session.add(cls.test_insured)
        db.session.commit()

        cls.policy = Policy('Test Policy', date(2015, 1, 1), 1200)
        cls.policy.named_insured = cls.test_insured.id
        cls.policy.agent = cls.test_agent.id
        db.session.add(cls.policy)
        db.session.commit()

    @classmethod
    def tearDownClass(cls):
        db.session.delete(cls.test_insured)
        db.session.delete(cls.test_agent)
        db.session.delete(cls.policy)
        db.session.commit()

    def setUp(self):
        self.payments = []

    def tearDown(self):
        for invoice in self.policy.invoices:
            db.session.delete(invoice)
        for payment in self.payments:
            db.session.delete(payment)
        db.session.commit()

    def test_annual_on_eff_date(self):
        self.policy.billing_schedule = "Annual"
        pa = PolicyAccounting(self.policy.id)
        self.assertEquals(pa.return_account_balance(date_cursor=self.policy.effective_date), 1200)

    def test_quarterly_on_eff_date(self):
        self.policy.billing_schedule = "Quarterly"
        pa = PolicyAccounting(self.policy.id)
        self.assertEquals(pa.return_account_balance(date_cursor=self.policy.effective_date), 300)

    def test_quarterly_on_last_installment_bill_date(self):
        self.policy.billing_schedule = "Quarterly"
        pa = PolicyAccounting(self.policy.id)
        invoices = Invoice.query.filter_by(policy_id=self.policy.id)\
                                .order_by(Invoice.bill_date).all()
        self.assertEquals(pa.return_account_balance(date_cursor=invoices[3].bill_date), 1200)

    def test_quarterly_on_second_installment_bill_date_with_full_payment(self):
        self.policy.billing_schedule = "Quarterly"
        pa = PolicyAccounting(self.policy.id)
        invoices = Invoice.query.filter_by(policy_id=self.policy.id)\
                                .order_by(Invoice.bill_date).all()
        self.payments.append(pa.make_payment(contact_id=self.policy.agent,
                                             date_cursor=invoices[1].bill_date, amount=600))
        self.assertEquals(pa.return_account_balance(date_cursor=invoices[1].bill_date), 0)
