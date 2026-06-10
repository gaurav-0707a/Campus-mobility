ZONES = [
    "Cautley Bhawan + Rajiv Bhawan + MAC",
    "Rajendra Bhawan + Radhakrishna Bhawan + Ganga",
    "Ravindra Bhawan",
    "Jawahar Bhawan + Sarojini Bhawan",
    "Azad Bhawan",
    "Govind Bhawan + Insti Hpspital",
    "Kasturba Bhawan + SAC",
    "EWS Bhawan + Himalya Bhawan",
    "James Thomason Building + SBI Bank",
    "Convocation Hall",
    "Mechanical Dept and Masjid",
    "Mandir",
    "Civil Dept + Earth Sciences Dept",
    "Tinkering Lab + Design Dept",
    "Chemical Eng Dept + Metallurgy Dept",
    "PNB Bank",
    "New Chemistry Dept",
    "Biosciences and Biotech Dept",
    "Electronics Dept",
    "Physics Dept",
    "Old Chemistry Dept + CSE Dept",
    "Mathematics Dept + Economic Dept",
    "Main Gate",
    "APJ + Gargi block + MGCL",
    "MBA Block",
    "Hydrology Dept + R"
]
NEARBY_ZONES = {
    "Cautley Bhawan":           ["Rajendra Bhawan", "Ravindra Bhawan"],
    "Rajendra Bhawan":          ["Cautley Bhawan", "Ravindra Bhawan"],
    "Ravindra Bhawan":          ["Cautley Bhawan", "Rajendra Bhawan", "Jawahar Bhawan"],
    "Jawahar Bhawan":           ["Ravindra Bhawan", "Rajiv Bhawan", "Azad Bhawan"],
    "Rajiv Bhawan":             ["Jawahar Bhawan", "Azad Bhawan", "Sports Complex"],
    "Azad Bhawan":              ["Jawahar Bhawan", "Rajiv Bhawan"],
    "Sarojini Bhawan":          ["Kasturba Bhawan", "Main Building"],
    "Kasturba Bhawan":          ["Sarojini Bhawan", "Main Building"],
    "Main Building":            ["Convocation Hall", "James Thomason Building", "Sarojini Bhawan"],
    "James Thomason Building":  ["Main Building", "Convocation Hall", "Civil Dept"],
    "Convocation Hall":         ["Main Building", "Survey Chowk"],
    "Mechanical Dept":          ["Civil Dept", "Electronics Dept"],
    "Civil Dept":               ["Mechanical Dept", "James Thomason Building"],
    "Electronics Dept":         ["Mechanical Dept", "Civil Dept"],
    "Main Gate":                ["Survey Chowk", "Staff Quarters Gate"],
    "Survey Chowk":             ["Main Gate", "Convocation Hall"],
    "Hospital":                 ["Sports Complex", "MBA Block"],
    "Sports Complex":           ["Hospital", "Rajiv Bhawan"],
    "MBA Block":                ["Hospital", "Staff Quarters Gate"],
    "Staff Quarters Gate":      ["MBA Block", "Main Gate"]
}
PENALTY = 60
PASSENGER_CANCEL_WINDOW = 60
DRIVER_RESPONSE_WINDOW = 30
SUSPENSION_THRESHOLD = 3
SUSPENSION_HOURS = 24
SECRET_KEY = "campus_rides_iitroorkee_2026"
ALGORITHM = "HS256"
TOKEN_EXPIRE_HOURS = 24