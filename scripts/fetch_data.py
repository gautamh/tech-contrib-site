import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv
import pandas as pd
from typing import List, Dict, Set, Tuple
from dataclasses import dataclass, asdict
import os
import json
import time

# Configuration
BASE_URL = "https://api.open.fec.gov/v1/"

@dataclass
class Contributor:
    """Represents a political contributor with name and employer information"""
    name: str
    employer: str

class FECContributionAnalyzer:
    def __init__(self, api_key: str):
        """Initialize the analyzer with an API key"""
        self.api_key = api_key
        self.base_params = {
            'api_key': api_key,
            'sort_hide_null': False,
            'sort_nulls_last': False,
            'per_page': 100,
        }

    def get_contributor_data(self, contributor: Contributor, start_date: str, end_date: str) -> List[Dict]:
        """Fetch all contributions for a given contributor within the date range"""
        params = self.base_params.copy()
        params.update({
            'contributor_name': contributor.name,
            'contributor_employer': contributor.employer,
            'min_date': start_date,
            'max_date': end_date,
            'sort': '-contribution_receipt_date',
            'is_individual': True,
        })
        
        endpoint = f"{BASE_URL}schedules/schedule_a/"
        all_contributions = []
        page = 1
        retries = 3
        
        while True:
            params['page'] = page
            response = None
            
            for attempt in range(retries):
                try:
                    print(f"Fetching individual contributions for {contributor.name} (page {page}), attempt {attempt + 1}")
                    response = requests.get(endpoint, params=params, timeout=30)
                    if response.status_code == 200:
                        break
                    else:
                        print(f"API request failed, status: {response.status_code}. Retrying in 5s...")
                        time.sleep(5)
                except requests.exceptions.RequestException as e:
                    print(f"API request exception: {e}. Retrying in 5s...")
                    time.sleep(5)
            
            if response is None or response.status_code != 200:
                print(f"All retries failed for {contributor.name} (page {page}). Skipping.")
                break

            data = response.json()
            results = data.get('results', [])
            if not results:
                break
                
            all_contributions.extend(results)
            
            if 'pagination' not in data or page >= data['pagination']['pages']:
                break
            page += 1
                
        return all_contributions

    def get_pac_expenditures(self, pac_ids: List[str], start_date: str, end_date: str) -> List[Dict]:
        """Fetch all Schedule B expenditures for a given list of PACs."""
        all_expenditures = []
        endpoint = f"{BASE_URL}schedules/schedule_b/"
        
        for pac_id in pac_ids:
            params = self.base_params.copy()
            params.update({
                'committee_id': pac_id,
                'min_date': start_date,
                'max_date': end_date,
                'sort': '-disbursement_date',
            })
            page = 1
            retries = 3

            while True:
                params['page'] = page
                response = None

                for attempt in range(retries):
                    try:
                        print(f"Fetching PAC expenditures for {pac_id} (page {page}), attempt {attempt + 1}")
                        response = requests.get(endpoint, params=params, timeout=30)
                        if response.status_code == 200:
                            break
                        else:
                            print(f"API request failed, status: {response.status_code}. Retrying in 5s...")
                            time.sleep(5)
                    except requests.exceptions.RequestException as e:
                        print(f"API request exception: {e}. Retrying in 5s...")
                        time.sleep(5)
                
                if response is None or response.status_code != 200:
                    print(f"All retries failed for PAC {pac_id} (page {page}). Skipping.")
                    break

                data = response.json()
                results = data.get('results', [])
                if not results:
                    break
                
                all_expenditures.extend(results)
                
                if 'pagination' not in data or page >= data['pagination']['pages']:
                    break
                page += 1
        
        return all_expenditures

def main():
    """Main function to fetch and save data."""
    load_dotenv()

    api_key = os.getenv('FEC_API_KEY')
    if not api_key:
        raise ValueError("FEC_API_KEY environment variable not set.")
        
    analyzer = FECContributionAnalyzer(api_key)
    
    # === Fetch Individual Contributions ===
    contributors = [
        Contributor(name="Sundar Pichai", employer="Google"),
        Contributor(name="Kent Walker", employer="Google"),
        Contributor(name="Thomas Kurian", employer="Google"),
        Contributor(name="Mark Zuckerberg", employer="Meta"),
        Contributor(name="Sheryl Sandberg", employer="Meta"),
        Contributor(name="Satya Nadella", employer="Microsoft"),
        Contributor(name="Brad Smith", employer="Microsoft"),
    ]
    
    individual_contributions = []
    for contributor in contributors:
        contributions = analyzer.get_contributor_data(
            contributor=contributor,
            start_date="01/01/2023",
            end_date="12/31/2025"
        )
        individual_contributions.extend(contributions)
    
    output_path = os.path.join(os.path.dirname(__file__), '..', 'static', 'data', 'contributions.json')
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, 'w') as f:
        json.dump(individual_contributions, f, indent=2)
    print(f"Successfully wrote {len(individual_contributions)} individual contributions to {output_path}")

    # === Fetch PAC Expenditures ===
    pac_ids = {
        "Google": "C00428623",
        "Meta": "C00786883",
        "Microsoft": "C00125997"
    }
    pac_expenditures = analyzer.get_pac_expenditures(
        pac_ids=list(pac_ids.values()),
        start_date="01/01/2023",
        end_date="12/31/2025"
    )
    pac_output_path = os.path.join(os.path.dirname(__file__), '..', 'static', 'data', 'pac_contributions.json')
    with open(pac_output_path, 'w') as f:
        json.dump(pac_expenditures, f, indent=2)
    print(f"Successfully wrote {len(pac_expenditures)} PAC expenditures to {pac_output_path}")

if __name__ == "__main__":
    main()