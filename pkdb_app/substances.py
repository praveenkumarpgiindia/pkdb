"""
Handling of substance information.

FIXME: add types, molecular weights and links to data bases
"""

SUBSTANCES_DATA = [
    # acetaminophen
    "acetaminophen",
    # caffeine (CYP2A1)
    "caffeine",
    "paraxanthine",
    "theobromine",
    "theophylline",
    "AFMU",
    "AAMU",
    "1U",
    "17X",
    "17U",
    "37X",
    "1X",
    "methylxanthine",
    "paraxanthine/caffeine",
    "caffeine/paraxanthine",
    "theobromine/caffeine",
    "theophylline/caffeine",
    "1X/caffeine",
    "1X/paraxanthine",
    "1X/theophylline",
    "(AFMU+1U+1X)/17U",
    "(AAMU+1X+1U)/17U",
    "17U/17X",
    "1U/(1U+1X)",
    "1U/1X",
    "AFMU/(AFMU+1U+1X)",
    "AAMU/(AAMU+1U+1X)",
    # caffeine interaction
    "fluvoxamine",
    "naringenin",
    "grapefruit juice",
    "quinolone",
    "pipemidic acid",
    "norfloxacin",
    "enoxacin",
    "ciprofloxacin",
    "ofloxacin",
    # oral contraceptives
    "levonorgestrel",
    "gestodene",
    "EE2",
    # codeine
    "codeine",
    "codeine-6-glucuronide",
    "norcodeine",
    "norcodeine-glucuronide",
    "codeine/morphine",
    "morphine/codine",
    "(Mor+M3G+M6G)/(Cod+C6G)",
    # chlorzoxazone (CYP2E1)
    "chlorzoxazone",
    "6-hydroxychlorzoxazone",
    # misc
    "tizanidine",
    "venlafaxine",
    "lomefloxacin",
    "ephedrine",
    "pseudoephedrine",
    "ibuprofen",
    "aspirin",
    "enoxacin",
    "ciprofloxacin",
    "pipemidic acid",
    "norfloxacin",
    "ofloxacin",
    "fluvoxamine",
    "ethanol",
    "chlorozoxazone",
    "lomefloxacin",
    "aminopyrine",
    "antipyrine",
    "bromsulpthalein",
    "phenylalanine",
    "indocyanine green",
    "morphine",
    "morphine-3-glucuronide",
    "morphine-6-glucuronide",
    "normorphine",
    "normorphine-glucuronide",
    "norcodeine-conjugates",
    "diclofenac",
    "glycerol",
    "FFA",
    "carbamazepine",
    # midazolam
    "midazolam",
    "1-hydroxymidazolam",
    # losartan
    "losartan",
    "exp3174",
    # omeprazole (CYP2C19)
    "omeprazole",
    "5-hydroxyomeprazole",
    "5-hydroxyomeprazole/omeprazole",
    # dextromethorphan
    "dextromethorphan",
    "dextrorphan",
    "digoxin",
    "clozapine",
    "carbon monoxide",

    # ----------------------
    # glucose metabolism
    # ----------------------
    'glucose',
    'insulin',
    'c-peptide',
    'glucagon',
]
SUBSTANCES_DATA_CHOICES = [(t, t) for t in SUBSTANCES_DATA]


if __name__ == "__main__":
    import os
    os.environ['PKDB_DEFAULT_PASSWORD'] = "pkdb"
    from pkdb_app.data_management import fill_database

    fill_database.setup_database(api_url=fill_database.API_URL, header=fill_database.get_header())

