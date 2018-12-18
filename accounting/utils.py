#!/user/bin/env python2.7
import logging

from datetime import date, datetime
from dateutil.relativedelta import relativedelta

from accounting import db
from models import Contact, Invoice, Payment, Policy

"""
#######################################################
This is the base code for the engineer project.
#######################################################
"""

class PolicyAccounting(object):
    """
     Each policy has its own instance of accounting.
    """
    def __init__(self, policy_id):
        self.policy = Policy.query.filter_by(id=policy_id).one()

        if not self.policy.invoices:
            self.make_invoices()

    def return_account_balance(self, date_cursor=None):
        if not date_cursor:
            date_cursor = datetime.now().date()

        # Retrieve invoices by policy id with date up to date_cursor
        invoices = Invoice.query.filter_by(policy_id=self.policy.id)\
                                .filter(Invoice.deleted == False)\
                                .filter(Invoice.bill_date <= date_cursor)\
                                .order_by(Invoice.bill_date)\
                                .all()

        # Calculate total amount due
        due_now = 0
        for invoice in invoices:
            due_now += invoice.amount_due

        # Retrieve all previous payments
        payments = Payment.query.filter_by(policy_id=self.policy.id)\
                                .filter(Payment.transaction_date <= date_cursor)\
                                .all()

        # Subtract payments from total due
        for payment in payments:
            due_now -= payment.amount_paid

        return due_now

    def make_payment(self, contact_id=None, date_cursor=None, amount=0):
        if not date_cursor:
            date_cursor = datetime.now().date()

        if not contact_id:
            try:
                contact_id = self.policy.named_insured
            except:
                logging.exception('Problem retrieving insured name for make_payment')
                return None

        # If cancellation due to non pay, an agent must make the payment
        if self.evaluate_cancellation_pending_due_to_non_pay(date_cursor):
            contact = Contact.query.filter_by(id=contact_id)\
                                   .one()
            if contact.role != 'Agent':
                print 'Due to the current status of this policy, an agent is needed to make payment'
                return

        # Create payment
        payment = Payment(self.policy.id,
                          contact_id,
                          amount,
                          date_cursor)
        db.session.add(payment)
        db.session.commit()

        return payment

    def evaluate_cancellation_pending_due_to_non_pay(self, date_cursor=None):
        """
         If this function returns true, an invoice
         on a policy has passed the due date without
         being paid in full. However, it has not necessarily
         made it to the cancel_date yet.
        """

        # Get all invoices by policy id
        invoices = Invoice.query.filter_by(policy_id=self.policy.id)\
                                .filter(Invoice.deleted == False)\
                                .order_by(Invoice.bill_date)\
                                .all()

        # Find payments for each invoice
        for invoice in invoices:
            # Retrieve payments made on time
            payments = Payment.query.filter_by(policy_id=invoice.policy_id)\
                                    .filter(Payment.transaction_date >= invoice.bill_date and Payment.transaction_date <= invoice.due_date)\
                                    .all()

            # If no payments made. And date is past due date, but before cancel date. Return true
            if not payments:
                if date_cursor > invoice.due_date and date_cursor < invoice.cancel_date:
                    return True

        return False

    def evaluate_cancel(self, date_cursor=None):
        if not date_cursor:
            date_cursor = datetime.now().date()

        # Retrieve all invoices where cancel date has passed
        invoices = Invoice.query.filter_by(policy_id=self.policy.id)\
                                .filter(Invoice.deleted == False)\
                                .filter(Invoice.cancel_date <= date_cursor)\
                                .order_by(Invoice.bill_date)\
                                .all()

        # Returns whether or not a policy should cancel. Based on if there is a balance left on any invoice
        for invoice in invoices:
            if not self.return_account_balance(invoice.cancel_date):
                continue
            else:
                return True

        else:
            print False

    def cancel_policy(self, status=None, status_code=None, description=None, date_cursor=None):
        valid_status = {u'Canceled', u'Expired'}
        valid_reasons = {'Fraud': 0, 'Non-Payment': 1, 'Underwriting': 2}

        # If invalid status code return
        if status not in valid_status:
            print('Invalid status update chosen')
            return

        # If invalid reason return
        if status_code not in valid_reasons:
            print('Invalid reason chosen')
            return

        # Set as current date if empty
        if not date_cursor:
            date_cursor = datetime.now().date()

        # If policy passed grace period for unpaid invoices print message
        if not self.evaluate_cancel:
            print ('This policy has one or more invoices unpaid, and should be cancelled')

        # Add status and description to policy
        self.policy.status = status
        self.policy.status_code = status_code
        self.policy.cancel_date = date_cursor

        if description:
            self.policy.status_desc = description

        # Mark invoices associated with policy as deleted
        self.delete_invoices()

        db.session.commit()

    def delete_invoices(self):
        for invoice in self.policy.invoices:
            invoice.deleted = True

    def make_invoices(self):
        billing_schedules = {'Annual': 1, 'Two-Pay': 2, 'Quarterly': 4, 'Monthly': 12}

        invoices = []

        # Create an Invoice.
        first_invoice = Invoice(self.policy.id,
                                self.policy.effective_date,  # bill_date
                                self.policy.effective_date + relativedelta(months=1),  # due date
                                self.policy.effective_date + relativedelta(months=1, days=14),  # cancellation date
                                self.policy.annual_premium)

        # Add invoice to array.
        invoices.append(first_invoice)

        # Get number of payments from billing_schedules
        num_of_payments = billing_schedules.get(self.policy.billing_schedule) or None

        if not num_of_payments:
            print "You have chosen a bad billing schedule."

        # Calculate first invoice amount due by dividing total by number of payments
        first_invoice.amount_due = first_invoice.amount_due / num_of_payments

        for i in range(1, num_of_payments):
            # Calculate months after effective date
            months_after_eff_date = i*(12/num_of_payments)

            # Add months to effective date to get bill date
            bill_date = self.policy.effective_date + relativedelta(months=months_after_eff_date)
            invoice = Invoice(self.policy.id,
                              bill_date,
                              bill_date + relativedelta(months=1),
                              bill_date + relativedelta(months=1, days=14),
                              self.policy.annual_premium / billing_schedules.get(self.policy.billing_schedule))
            invoices.append(invoice)

        # Add new invoices to db
        for invoice in invoices:
            db.session.add(invoice)
        db.session.commit()

    def change_billing_schedule(self, new_schedule=''):
        # If trying to update to same schedule, return
        if(self.policy.billing_schedule == new_schedule):
            return

        billing_schedules = ['Annual', 'Two-Pay', 'Quarterly', 'Monthly']

        # If not a correct billing schedule print and return
        if new_schedule not in billing_schedules:
            print('You have chosen an incorrect billing schedule')
            return

        # Set all invoices to deleted
        for invoice in self.policy.invoices:
            invoice.deleted = True
            db.session.commit()

        # Update policy to new billing schedule and call make invoices
        self.policy.billing_schedule = new_schedule
        self.make_invoices()


################################
# The functions below are for the db and
# shouldn't need to be edited.
################################
def build_or_refresh_db():
    db.drop_all()
    db.create_all()
    insert_data()
    print "DB Ready!"

def insert_data():
    #Contacts
    contacts = []
    john_doe_agent = Contact('John Doe', 'Agent')
    contacts.append(john_doe_agent)
    john_doe_insured = Contact('John Doe', 'Named Insured')
    contacts.append(john_doe_insured)
    bob_smith = Contact('Bob Smith', 'Agent')
    contacts.append(bob_smith)
    anna_white = Contact('Anna White', 'Named Insured')
    contacts.append(anna_white)
    joe_lee = Contact('Joe Lee', 'Agent')
    contacts.append(joe_lee)
    ryan_bucket = Contact('Ryan Bucket', 'Named Insured')
    contacts.append(ryan_bucket)

    for contact in contacts:
        db.session.add(contact)
    db.session.commit()

    policies = []
    p1 = Policy('Policy One', date(2015, 1, 1), 365)
    p1.billing_schedule = 'Annual'
    p1.named_insured = john_doe_insured.id
    p1.agent = bob_smith.id
    policies.append(p1)

    p2 = Policy('Policy Two', date(2015, 2, 1), 1600)
    p2.billing_schedule = 'Quarterly'
    p2.named_insured = anna_white.id
    p2.agent = joe_lee.id
    policies.append(p2)

    p3 = Policy('Policy Three', date(2015, 1, 1), 1200)
    p3.billing_schedule = 'Monthly'
    p3.named_insured = ryan_bucket.id
    p3.agent = john_doe_agent.id
    policies.append(p3)

    for policy in policies:
        db.session.add(policy)
    db.session.commit()

    for policy in policies:
        PolicyAccounting(policy.id)

    payment_for_p2 = Payment(p2.id, anna_white.id, 400, date(2015, 2, 1))
    db.session.add(payment_for_p2)
    db.session.commit()
