"""
schools.py — All 9 schools and their departments.
Edit the DEPT_BOT_LINKS below to add the actual bot usernames
after you create all the department bots on BotFather.
"""

# ── 9 Schools with their departments ─────────────────────────
SCHOOLS = {
    "saat": {
        "name":  "School of Agriculture And Agricultural Technology",
        "short": "SAAT",
        "emoji": "🌾",
        "departments": {
            "crop":       "Crop Production & Horticulture",
            "soil":       "Soil Science & Land Management",
            "animal":     "Animal Production & Health",
            "agric_ext":  "Agricultural Extension & Management",
            "food_tech":  "Food Technology",
            "agric_econ": "Agricultural Economics & Extension",
        },
    },
    "soht": {
        "name":  "School of Health Technology",
        "short": "SOHT",
        "emoji": "🏥",
        "departments": {
            "med_lab":    "Medical Laboratory Science",
            "health_info":"Health Information Management",
            "dental_tech":"Dental Technology",
            "optometry":  "Optometry",
            "radiology":  "Radiography",
            "nutrition":  "Nutrition & Dietetics",
            "environ_hlth":"Environmental Health Technology",
        },
    },
    "sbms": {
        "name":  "School of Basic Medical Science",
        "short": "SBMS",
        "emoji": "🧬",
        "departments": {
            "anatomy":    "Anatomy",
            "physiology": "Physiology",
            "biochemistry":"Biochemistry",
            "microbiology":"Microbiology",
            "pharmacology":"Pharmacology",
        },
    },
    "sict": {
        "name":  "School of Information and Communication Technology",
        "short": "SICT",
        "emoji": "💻",
        "departments": {
            "computer_sci":    "Computer Science",
            "info_tech":       "Information Technology",
            "cyber_security":  "Cyber Security",
            "software_eng":    "Software Engineering",
            "data_mgt":        "Data Management Technology",
            "library_info":    "Library & Information Science",
        },
    },
    "sobs": {
        "name":  "School of Biological Science",
        "short": "SOBS",
        "emoji": "🔬",
        "departments": {
            "biology":    "Biology",
            "botany":     "Botany",
            "zoology":    "Zoology",
            "genetics":   "Genetics & Biotechnology",
            "ecology":    "Ecology & Environmental Biology",
        },
    },
    "slit": {
        "name":  "School of Logistics and Innovation Technology",
        "short": "SLIT",
        "emoji": "🚚",
        "departments": {
            "logistics":     "Logistics & Supply Chain Management",
            "procurement":   "Procurement & Supply Chain",
            "transport":     "Transport Management",
            "innovation":    "Innovation & Entrepreneurship Technology",
            "business_mgt":  "Business Management Technology",
        },
    },
    "seet": {
        "name":  "School of Engineering and Engineering Technology",
        "short": "SEET",
        "emoji": "⚙️",
        "departments": {
            "civil":       "Civil Engineering Technology",
            "mechanical":  "Mechanical Engineering Technology",
            "chemical":    "Chemical Engineering Technology",
            "industrial":  "Industrial & Production Engineering",
            "petroleum":   "Petroleum Engineering Technology",
            "welding":     "Welding & Fabrication Technology",
            "polymer":     "Polymer Technology",
        },
    },
    "sops": {
        "name":  "School of Physical Science",
        "short": "SOPS",
        "emoji": "⚗️",
        "departments": {
            "physics":     "Physics",
            "chemistry":   "Chemistry",
            "mathematics": "Mathematics & Statistics",
            "geology":     "Geology & Mineral Science",
            "science_lab": "Science Laboratory Technology",
        },
    },
    "seset": {
        "name":  "School of Electrical Systems and Engineering Technology",
        "short": "SESET",
        "emoji": "⚡",
        "departments": {
            "electrical":      "Electrical Engineering Technology",
            "electronics":     "Electronics Engineering Technology",
            "telecomms":       "Telecommunications Engineering",
            "computer_eng":    "Computer Engineering Technology",
            "instrumentation": "Instrumentation & Control Technology",
            "mechatronics":    "Mechatronics Engineering Technology",
        },
    },
}

# ── Department Bot Links ──────────────────────────────────────
# After creating each department bot on BotFather,
# paste the link here. Format: "dept_key": "https://t.me/YourBotName"
# Leave as None if you haven't created the bot yet — main bot will tell
# students it's "coming soon".

DEPT_BOT_LINKS = {
    # SAAT
    "crop":          None,   # e.g. "https://t.me/saat_crop_bot"
    "soil":          None,
    "animal":        None,
    "agric_ext":     None,
    "food_tech":     None,
    "agric_econ":    None,
    # SOHT
    "med_lab":       None,
    "health_info":   None,
    "dental_tech":   None,
    "optometry":     None,
    "radiology":     None,
    "nutrition":     None,
    "environ_hlth":  None,
    # SBMS
    "anatomy":       None,
    "physiology":    None,
    "biochemistry":  None,
    "microbiology":  None,
    "pharmacology":  None,
    # SICT
    "computer_sci":  None,
    "info_tech":     None,
    "cyber_security":None,
    "software_eng":  None,
    "data_mgt":      None,
    "library_info":  None,
    # SOBS
    "biology":       None,
    "botany":        None,
    "zoology":       None,
    "genetics":      None,
    "ecology":       None,
    # SLIT
    "logistics":     None,
    "procurement":   None,
    "transport":     None,
    "innovation":    None,
    "business_mgt":  None,
    # SEET
    "civil":         None,
    "mechanical":    None,
    "chemical":      None,
    "industrial":    None,
    "petroleum":     None,
    "welding":       None,
    "polymer":       None,
    # SOPS
    "physics":       None,
    "chemistry":     None,
    "mathematics":   None,
    "geology":       None,
    "science_lab":   None,
    # SESET
    "electrical":    None,
    "electronics":   None,
    "telecomms":     None,
    "computer_eng":  None,
    "instrumentation":None,
    "mechatronics":  None,
}


def get_school(school_key: str) -> dict:
    return SCHOOLS.get(school_key, {})


def get_dept_name(school_key: str, dept_key: str) -> str:
    school = SCHOOLS.get(school_key, {})
    return school.get("departments", {}).get(dept_key, dept_key.replace("_", " ").title())


def get_dept_bot(dept_key: str):
    return DEPT_BOT_LINKS.get(dept_key)


def all_dept_keys() -> list:
    keys = []
    for school in SCHOOLS.values():
        keys.extend(school["departments"].keys())
    return keys
