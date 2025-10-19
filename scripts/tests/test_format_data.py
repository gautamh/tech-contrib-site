import pytest
from scripts.format_data import normalize_name, format_cluster_data, format_pac_data

# Sample raw data for testing
SAMPLE_INDIVIDUAL_CONTRIBUTIONS = [
    # Cluster 1: Google execs to a non-Google PAC
    {
        "contributor_name": "PICHAI, SUNDAR", "contributor_employer": "Google", "contribution_receipt_amount": 1000, 
        "contribution_receipt_date": "2025-01-15", "committee_id": "C123", "pdf_url": "url1",
        "committee": {"name": "A Good Cause PAC", "party_full": "DEMOCRATIC PARTY"}
    },
    {
        "contributor_name": "Kent Walker", "contributor_employer": "Google", "contribution_receipt_amount": 1500, 
        "contribution_receipt_date": "2025-01-16", "committee_id": "C123", "pdf_url": "url2",
        "committee": {"name": "A Good Cause PAC", "party_full": "DEMOCRATIC PARTY"}
    },
    # Cluster 2: Should be ignored (donations to own company PAC)
    {
        "contributor_name": "SMITH, BRADFORD L.", "contributor_employer": "Microsoft", "contribution_receipt_amount": 500, 
        "contribution_receipt_date": "2025-02-01", "committee_id": "C00227546", "pdf_url": "url3",
        "committee": {"name": "MSVPAC", "party_full": ""}
    },
    {
        "contributor_name": "Satya Nadella", "contributor_employer": "Microsoft", "contribution_receipt_amount": 500, 
        "contribution_receipt_date": "2025-02-02", "committee_id": "C00227546", "pdf_url": "url4",
        "committee": {"name": "MSVPAC", "party_full": ""}
    },
    # Not a cluster (only one person)
    {
        "contributor_name": "Zuckerberg, Mark", "contributor_employer": "Meta", "contribution_receipt_amount": 2000, 
        "contribution_receipt_date": "2025-03-10", "committee_id": "C456", "pdf_url": "url5",
        "committee": {"name": "Future Forward", "party_full": "DEMOCRATIC PARTY"}
    }
]

SAMPLE_PAC_EXPENDITURES = [
    # Valid contribution
    {
        "committee": {"name": "GOOGLE LLC NETPAC"},
        "recipient_committee": {"name": "TROY CARTER FOR CONGRESS", "party_full": "DEMOCRATIC PARTY"},
        "disbursement_amount": 1000.0, "disbursement_date": "2025-08-29", "disbursement_purpose_category": "CONTRIBUTIONS",
        "pdf_url": "url_pac1", "transaction_id": "1"
    },
    # Refund (should be ignored)
    {
        "committee": {"name": "GOOGLE LLC NETPAC"},
        "recipient_committee": {"name": "TROY CARTER FOR CONGRESS", "party_full": "DEMOCRATIC PARTY"},
        "disbursement_amount": -500.0, "disbursement_date": "2025-08-30", "disbursement_purpose_category": "CONTRIBUTIONS",
        "pdf_url": "url_pac2", "transaction_id": "2"
    },
    # Not a contribution
    {
        "committee": {"name": "GOOGLE LLC NETPAC"},
        "recipient_committee": {"name": "Some Vendor Inc"},
        "disbursement_amount": 250.0, "disbursement_date": "2025-08-15", "disbursement_purpose_category": "OTHER",
        "pdf_url": "url_pac3", "transaction_id": "3"
    }
]

# --- Tests for normalize_name --- #

@pytest.mark.parametrize("input_name, expected_output", [
    ("SMITH, BRADFORD L.", "bradford smith"),
    ("Bradford L. Smith", "bradford smith"),
    ("PICHAI, SUNDAR", "pichai sundar"),
    ("Mark Elliot Zuckerberg", "elliot mark zuckerberg"),
])
def test_normalize_name(input_name, expected_output):
    assert normalize_name(input_name) == expected_output

# --- Tests for format_cluster_data --- #

def test_format_cluster_data_creates_valid_cluster():
    result = format_cluster_data(SAMPLE_INDIVIDUAL_CONTRIBUTIONS)
    assert len(result) == 1
    cluster = result[0]
    assert cluster['recipientName'] == "A Good Cause PAC"
    assert cluster['donorCount'] == 2
    assert cluster['totalAmount'] == 2500

def test_format_cluster_data_ignores_company_pacs():
    # This is implicitly tested by the above test, which expects only 1 cluster
    # instead of 2.
    result = format_cluster_data(SAMPLE_INDIVIDUAL_CONTRIBUTIONS)
    assert len(result) == 1
    assert not any(c['recipientName'] == 'MSVPAC' for c in result)

def test_format_cluster_data_ignores_single_contributor():
    # Also implicitly tested by the main test
    result = format_cluster_data(SAMPLE_INDIVIDUAL_CONTRIBUTIONS)
    assert not any(c['recipientName'] == 'Future Forward' for c in result)

# --- Tests for format_pac_data --- #

def test_format_pac_data_filters_correctly():
    result = format_pac_data(SAMPLE_PAC_EXPENDITURES)
    assert len(result) == 1
    donation = result[0]
    assert donation['donorName'] == "GOOGLE LLC NETPAC"
    assert donation['recipientName'] == "TROY CARTER FOR CONGRESS"
    assert donation['amount'] == 1000.0

def test_format_pac_data_handles_empty_list():
    assert format_pac_data([]) == []