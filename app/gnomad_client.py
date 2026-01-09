"""
gnomad_client.py

Client for gnomAD via GraphQL API.
Fetch minimal gene info to confirm existence and provide a link.

GraphQL Endpoint: https://gnomad.broadinstitute.org/api

Query:
    query Gene($gene_symbol: String!) {
        gene(gene_symbol: $gene_symbol, reference_genome: GRCh38) {
            gene_id
            symbol
            reference_genome
            chrom
            start
            stop
            omim_id
        }
    }
"""

import requests
from typing import Dict, Any

GNOMAD_API_URL = "https://gnomad.broadinstitute.org/api"

def get_gnomad_summary(gene_symbol: str) -> Dict[str, Any]:
    gene_symbol = (gene_symbol or "").strip()
    if not gene_symbol:
         return {"used": False, "reason": "No gene symbol provided."}

    query = """
    query Gene($gene_symbol: String!) {
        gene(gene_symbol: $gene_symbol, reference_genome: GRCh38) {
            gene_id
            symbol
            reference_genome
            chrom
            start
            stop
            omim_id
        }
    }
    """
    
    variables = {"gene_symbol": gene_symbol}

    try:
        # Request with a tailored user-agent just in case
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "GeneGPT/2.0"
        }
        
        resp = requests.post(
            GNOMAD_API_URL, 
            json={"query": query, "variables": variables}, 
            headers=headers, 
            timeout=10
        )
        resp.raise_for_status()
        data = resp.json()
        
        # Parse result
        # data = { "data": { "gene": { ... } } }
        gene_data = data.get("data", {}).get("gene")
        
        if not gene_data:
             return {
                "used": False,
                "reason": f"No gnomAD data found for symbol {gene_symbol} (GRCh38)."
            }
        
        gene_id = gene_data.get("gene_id")  # e.g. ENSG00000012048
        
        # Link to the browser
        # Direct by ID is safest: https://gnomad.broadinstitute.org/gene/{gene_id}?dataset=gnomad_r4
        # Or just /gene/{gene_id}
        link = f"https://gnomad.broadinstitute.org/gene/{gene_id}?dataset=gnomad_r4"
        
        return {
            "used": True,
            "gene_id": gene_id,
            "chrom": gene_data.get("chrom"),
            "omim_id": gene_data.get("omim_id"),
            "link": link,
            "reason": "Fetched basic gene metadata from gnomAD."
        }

    except Exception as e:
        return {
            "used": False,
            "reason": f"Error querying gnomAD: {e}"
        }
