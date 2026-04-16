"""
UK SIC 2007 codes for biology-related sectors.

Used by the Companies House search to narrow results to relevant industries.
Reference: https://resources.companieshouse.gov.uk/sic/
"""

BIOLOGY_SIC_CODES: dict[str, list[str]] = {
    "pharmaceutical_manufacturing": [
        "21100",  # Manufacture of basic pharmaceutical products
        "21200",  # Manufacture of pharmaceutical preparations
    ],
    "biotechnology_research": [
        "72110",  # Research and experimental development on biotechnology
    ],
    "natural_science_research": [
        "72190",  # Other R&D on natural sciences and engineering
    ],
    "medical_devices_diagnostics": [
        "26600",  # Manufacture of irradiation / electromedical equipment
        "32500",  # Manufacture of medical and dental instruments and supplies
    ],
    "bioinformatics_software": [
        "62012",  # Business and domestic software development
        "62020",  # IT consultancy activities (covers bioinformatics consultancies)
    ],
    "chemical_biology_upstream": [
        "20140",  # Manufacture of other organic basic chemicals
        "20590",  # Manufacture of other chemical products n.e.c.
    ],
    "veterinary_animal_health": [
        "75000",  # Veterinary activities
    ],
    "agricultural_biotech": [
        "01110",  # Growing of cereals (firms with biotech crop divisions)
    ],
    "biotech_spinouts_consultancy": [
        "70229",  # Management consultancy (covers many biotech spinouts and incubators)
    ],
    "clinical_health_services": [
        "86900",  # Other human health activities (clinical-stage startups, CROs)
        "86210",  # General medical practice activities
    ],
    "laboratory_testing": [
        "71200",  # Technical testing and analysis (contract labs, diagnostics)
    ],
}

# Flat list used as the default search parameter for Companies House
ALL_BIOLOGY_SIC_CODES: list[str] = [
    code
    for codes in BIOLOGY_SIC_CODES.values()
    for code in codes
]

# Human-readable labels for each code (used in logs and email templates)
SIC_LABELS: dict[str, str] = {
    "21100": "Pharmaceutical manufacturing (basic products)",
    "21200": "Pharmaceutical manufacturing (preparations)",
    "72110": "Biotechnology R&D",
    "72190": "Natural science R&D",
    "26600": "Medical imaging / electromedical devices",
    "32500": "Medical and dental instruments",
    "62012": "Life science software development",
    "62020": "Bioinformatics / IT consultancy",
    "20140": "Organic chemistry manufacturing",
    "20590": "Specialty chemical manufacturing",
    "75000": "Veterinary / animal health",
    "01110": "Agricultural biotech",
    "70229": "Biotech spinout / consultancy",
    "86900": "Clinical-stage biotech / CRO",
    "86210": "Medical practice / clinical research",
    "71200": "Contract laboratory / technical testing",
}

# The recommended default set for a Manchester biotech search
# Note: 86900/86210/70229 excluded — too broad, catches clinics and consultancies
DEFAULT_SEARCH_SIC_CODES: list[str] = [
    "21100",  # Pharma manufacturing (basic)
    "21200",  # Pharma manufacturing (preparations)
    "72110",  # Biotechnology R&D
    "72190",  # Natural science R&D
    "26600",  # Medical devices
    "32500",  # Medical instruments
    "62012",  # Life science software
    "71200",  # Contract labs / technical testing
]

# Biology keywords to use as search terms (used instead of just "Manchester")
# Searching by specific terms returns far more targeted results than location alone
BIOLOGY_SEARCH_TERMS: list[str] = [
    "biotech",
    "biotechnology",
    "pharmaceutical",
    "bioinformatics",
    "genomics",
    "therapeutics",
    "diagnostics",
    "bioscience",
    "life science",
    "molecular biology",
]
