"""
This script reads the raw JSON data fetched from the FEC API and transforms
it into a structured format suitable for the frontend application.

It performs several key tasks:
1.  **Name Normalization:** Cleans and standardizes contributor names to group contributions from the same person accurately.
2.  **Cluster Detection:** Identifies and creates "clusters" of contributions where multiple executives from the same company donate to the same committee.
3.  **PAC Filtering:** Filters expenditures from corporate PACs to isolate actual contributions and removes refunds.
4.  **Combines Data:** Outputs a single `formatted_contributions.json` file containing both the executive clusters and the cleaned PAC donations.
"""

import json
import os
from dataclasses import asdict, dataclass
from typing import List

import pandas as pd

# --- Dataclasses for structured data ---

@dataclass
class FormattedContribution:
    """Represents a single contribution within an executive cluster."""
    donorName: str
    donorInfo: str
    amount: float
    date: str
    fecUrl: str

@dataclass
class ClusterEvent:
    """Represents a cluster of contributions from multiple executives at one company to a single committee."""
    recipientName: str
    recipientParty: str
    isExtreme: bool
    totalAmount: float
    donorCount: int
    timeframe: str
    contributions: List[FormattedContribution]

@dataclass
class PacDonation:
    """Represents a single, clean donation from a corporate PAC."""
    donorName: str
    recipientName: str
    amount: float
    recipientParty: str
    date: str
    fecUrl: str

# --- Constants ---

COMPANY_PACS = {
    "Google": "C00428623",
    "Meta": "C00786883",
    "Microsoft": "C00227546"
}

# --- Helper Functions ---

def normalize_name(name: str) -> str:
    """Creates a canonical representation of a name to handle minor variations.
    
    This function lowercases, removes punctuation, and sorts the name parts to ensure
    that names like "Smith, John L." and "John Smith" are treated as identical.
    It also removes common suffixes and single-letter initials.
    """
    if not isinstance(name, str):
        return ""
    name = name.lower()
    name = ''.join(c for c in name if c.isalnum() or c.isspace())
    parts = name.split()
    suffixes_to_remove = {'mr', 'ms', 'mrs', 'jr', 'sr', 'ii', 'iii', 'iv'}
    # Keep parts that are not a suffix and have more than one character.
    cleaned_parts = [p for p in parts if p not in suffixes_to_remove and len(p) > 1]
    # Fallback for names that are only initials or suffixes (e.g., "L.")
    if not cleaned_parts:
        cleaned_parts = [p for p in parts if p not in suffixes_to_remove]
    return ' '.join(sorted(cleaned_parts))

# --- Formatting Functions ---

def format_cluster_data(raw_individual_data: List[dict]) -> List[dict]:
    """Processes raw individual contributions to find and format donation clusters."""
    if not raw_individual_data:
        return []

    df = pd.DataFrame(raw_individual_data)
    df['contribution_receipt_date'] = pd.to_datetime(df['contribution_receipt_date'])
    df['normalized_name'] = df['contributor_name'].apply(normalize_name)

    clusters = []
    # A cluster is defined as multiple executives from the same company donating to the same committee.
    for (committee_id, employer), group in df.groupby(['committee_id', 'contributor_employer']):
        # Exclude clusters where the recipient is the company's own PAC.
        employer_key = next((key for key in COMPANY_PACS if key.lower() in employer.lower()), None)
        if employer_key and committee_id == COMPANY_PACS[employer_key]:
            continue
        
        # A cluster must have at least 2 unique donors.
        if group['normalized_name'].nunique() < 2:
            continue

        committee_info = group['committee'].iloc[0]
        contributions = []
        for _, row in group.iterrows():
            contributions.append(FormattedContribution(
                donorName=row['contributor_name'],
                donorInfo=f"{row['contributor_employer']}, {row.get('contributor_occupation', 'N/A')}",
                amount=row['contribution_receipt_amount'],
                date=row['contribution_receipt_date'].strftime('%Y-%m-%d'),
                fecUrl=row['pdf_url']
            ))

        min_date, max_date = group['contribution_receipt_date'].min(), group['contribution_receipt_date'].max()
        time_delta_days = (max_date - min_date).days
        timeframe = f"over {time_delta_days} days" if time_delta_days > 7 else ("in the last week" if time_delta_days > 1 else "in the last 24 hours")

        cluster = ClusterEvent(
            recipientName=committee_info.get('name', 'Unknown Committee'),
            recipientParty=(committee_info.get('party_full') or '').strip(),
            isExtreme=False, # Placeholder for future analysis
            totalAmount=group['contribution_receipt_amount'].sum(),
            donorCount=group['normalized_name'].nunique(),
            timeframe=timeframe,
            contributions=sorted([asdict(c) for c in contributions], key=lambda x: x['date'], reverse=True)
        )
        clusters.append(asdict(cluster))
    
    return sorted(clusters, key=lambda x: x['totalAmount'], reverse=True)

def format_pac_data(raw_pac_data: List[dict]) -> List[dict]:
    """Processes raw PAC expenditures into a clean list of donations, filtering out non-contributions and refunds."""
    if not raw_pac_data:
        return []

    df = pd.DataFrame(raw_pac_data)
    # Remove duplicates from source data, as the FEC API can sometimes return them.
    df.drop_duplicates(subset=['transaction_id'], keep='first', inplace=True)

    pac_donations = []
    for _, expenditure in df.iterrows():
        amount = expenditure.get('disbursement_amount')
        # Skip records that are not positive-value contributions to a committee.
        if amount is None or float(amount) <= 0:
            continue
        if not expenditure.get('recipient_committee') or expenditure.get('disbursement_purpose_category') != 'CONTRIBUTIONS':
            continue

        donation = PacDonation(
            donorName=expenditure['committee']['name'],
            recipientName=expenditure['recipient_committee']['name'],
            amount=float(amount),
            recipientParty=(expenditure['recipient_committee'].get('party_full') or '').strip(),
            date=expenditure['disbursement_date'],
            fecUrl=expenditure['pdf_url']
        )
        pac_donations.append(asdict(donation))
            
    return sorted(pac_donations, key=lambda x: x['date'], reverse=True)

# --- Main Execution ---

def main():
    """Reads raw data, formats it, and saves it for the frontend."""
    base_path = os.path.join(os.path.dirname(__file__), '..', 'static', 'data')
    
    # Process Individual Contributions
    individual_contribs_path = os.path.join(base_path, 'contributions.json')
    cluster_events = []
    if os.path.exists(individual_contribs_path):
        with open(individual_contribs_path, 'r') as f:
            raw_individual_data = json.load(f)
        cluster_events = format_cluster_data(raw_individual_data)
        print(f"Processed {len(raw_individual_data)} individual contributions into {len(cluster_events)} clusters.")
    else:
        print(f"Warning: Individual contributions file not found at {individual_contribs_path}")

    # Process PAC Expenditures
    pac_contribs_path = os.path.join(base_path, 'pac_contributions.json')
    pac_donations = []
    if os.path.exists(pac_contribs_path):
        with open(pac_contribs_path, 'r') as f:
            raw_pac_data = json.load(f)
        pac_donations = format_pac_data(raw_pac_data)
        print(f"Processed {len(raw_pac_data)} PAC expenditures into {len(pac_donations)} donations.")
    else:
        print(f"Warning: PAC contributions file not found at {pac_contribs_path}")

    # Combine and Write Final Output
    output_data = {
        "clusterEvents": cluster_events,
        "pacContributions": pac_donations
    }
    
    output_path = os.path.join(base_path, 'formatted_contributions.json')
    with open(output_path, 'w') as f:
        json.dump(output_data, f, indent=2)

    print(f"Successfully wrote formatted data to {output_path}")

if __name__ == "__main__":
    main()
