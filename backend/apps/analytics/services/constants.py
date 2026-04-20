"""
Shared constants for analytics services.

These constants define spend bands and strategic segments used across
multiple analytics service classes.
"""

# Spend bands for stratification analysis
# Must match frontend definitions in SpendStratification page
SPEND_BANDS = [
    {'name': '0 - 1K', 'label': '0-1K', 'min': 0, 'max': 1000},
    {'name': '1K - 2K', 'label': '1K-2K', 'min': 1000, 'max': 2000},
    {'name': '2K - 5K', 'label': '2K-5K', 'min': 2000, 'max': 5000},
    {'name': '5K - 10K', 'label': '5K-10K', 'min': 5000, 'max': 10000},
    {'name': '10K - 25K', 'label': '10K-25K', 'min': 10000, 'max': 25000},
    {'name': '25K - 50K', 'label': '25K-50K', 'min': 25000, 'max': 50000},
    {'name': '50K - 100K', 'label': '50K-100K', 'min': 50000, 'max': 100000},
    {'name': '100K - 500K', 'label': '100K-500K', 'min': 100000, 'max': 500000},
    {'name': '500K - 1M', 'label': '500K-1M', 'min': 500000, 'max': 1000000},
    {'name': '1M and Above', 'label': '1M+', 'min': 1000000, 'max': float('inf')},
]

# Strategic segments for Kraljic matrix analysis
SEGMENTS = [
    {'name': 'Strategic', 'min': 1000000, 'max': float('inf'), 'strategy': 'Partnership & Innovation'},
    {'name': 'Leverage', 'min': 100000, 'max': 1000000, 'strategy': 'Competitive Bidding'},
    {'name': 'Routine', 'min': 10000, 'max': 100000, 'strategy': 'Efficiency & Automation'},
    {'name': 'Tactical', 'min': 0, 'max': 10000, 'strategy': 'Consolidation'},
]
