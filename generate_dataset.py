"""
SevaSetu grievance dataset generator (v2).

Why this exists
----------------
The v1 dataset (`sevasetu_grievance_dataset_100k_v1.csv`) was built from ~20
shared sentence templates with a small slot vocabulary, and every complaint
about e.g. a pothole contained the literal word "Pothole" that maps 1:1 to
PWD. The resulting classifiers memorized "if token X appears, output class
Y" instead of learning to read a complaint. See CLAUDE_CODE_BRIEF.md for the
full diagnosis.

This script generates a new dataset designed so that shortcut doesn't work:

- Per department: 15-20+ distinct sentence frames (clause order, opener,
  closer, formality, language) instead of one shared template pool.
- Per complaint type: a bank of hand-written situation descriptions, most of
  which do NOT name the complaint type verbatim - they describe the
  real-world symptom instead ("a bike fell into the hole" rather than
  "pothole problem").
- Noise: misspellings, dropped words, missing punctuation, inconsistent
  casing, pure Devanagari Hindi, pure English, and Hinglish code-mixing.
- Hard negatives: a slice of rows mention two departments' issues in one
  complaint, labeled by the primary (dominant) issue, so the model has to
  learn priority rather than "first keyword found."
- Urgency is derived from textual danger/injury/emergency cues scanned in
  the final generated sentence, not looked up from sector. Any department
  can produce a low, medium, or high urgency complaint depending on what
  the sentence actually says.
"""

import csv
import random
import re
import sys
from collections import Counter

RANDOM_STATE = 42
random.seed(RANDOM_STATE)

N_ROWS = 100_000
HARD_NEGATIVE_FRACTION = 0.03
OUTPUT_PATH = "sevasetu_grievance_dataset_v2.csv"

# ----------------------------------------------------------------------
# Locations
# ----------------------------------------------------------------------

CITIES = [
    "Kanpur, Uttar Pradesh", "Surat, Gujarat", "Kozhikode, Kerala",
    "Nagpur, Maharashtra", "Gaya, Bihar", "Ranchi, Jharkhand",
    "Bilaspur, Chhattisgarh", "Siliguri, West Bengal", "Coimbatore, Tamil Nadu",
    "Dibrugarh, Assam", "Indore, Madhya Pradesh", "Shillong, Meghalaya",
    "Ludhiana, Punjab", "Panaji, Goa", "Hyderabad, Telangana",
    "Amritsar, Punjab", "Kolkata, West Bengal", "Ahmedabad, Gujarat",
    "Guwahati, Assam", "Thiruvananthapuram, Kerala", "Jaipur, Rajasthan",
    "Lucknow, Uttar Pradesh", "Patna, Bihar", "Bhopal, Madhya Pradesh",
    "Raipur, Chhattisgarh", "Dehradun, Uttarakhand", "Chandigarh, Punjab",
    "Vadodara, Gujarat", "Nashik, Maharashtra", "Varanasi, Uttar Pradesh",
    "Agra, Uttar Pradesh", "Meerut, Uttar Pradesh", "Jabalpur, Madhya Pradesh",
    "Vijayawada, Andhra Pradesh", "Madurai, Tamil Nadu", "Jodhpur, Rajasthan",
    "Rajkot, Gujarat", "Kota, Rajasthan", "Gwalior, Madhya Pradesh",
    "Faridabad, Haryana", "Aurangabad, Maharashtra", "Srinagar, Jammu and Kashmir",
    "Jamshedpur, Jharkhand", "Bhubaneswar, Odisha", "Cuttack, Odisha",
    "Dhanbad, Jharkhand", "Asansol, West Bengal", "Allahabad, Uttar Pradesh",
    "Aligarh, Uttar Pradesh", "Gorakhpur, Uttar Pradesh", "Bikaner, Rajasthan",
    "Saharanpur, Uttar Pradesh", "Warangal, Telangana", "Mysuru, Karnataka",
    "Hubballi, Karnataka", "Belagavi, Karnataka", "Kolhapur, Maharashtra",
    "Solapur, Maharashtra", "Tirupati, Andhra Pradesh", "Guntur, Andhra Pradesh",
    "Rourkela, Odisha", "Muzaffarpur, Bihar", "Bhagalpur, Bihar",
]

# village / mohalla style location strings used when we want a rural flavor
VILLAGE_TAGS = [
    "gaon", "mohalla", "colony", "basti", "ward", "sector", "nagar",
]


def rand_location():
    return random.choice(CITIES)


# ----------------------------------------------------------------------
# Urgency lexicon - the ONLY source of the urgency label. It scans the
# final generated text, so urgency is a function of what the sentence
# actually says, not of which department/sector it belongs to.
# ----------------------------------------------------------------------

HIGH_URGENCY_CUES = [
    "died", "dead", "death", "murder", "shoot", "shot", "gun", "gunshot",
    "blood", "khoon", "maut", "mar gaya", "mar gayi", "mar gaye",
    "injured", "ghayal", "accident", "durghatna", "durghatana",
    "fire", "aag lag", "emergency", "jaan ka khatra", "jaan pe khatra",
    "unconscious", "behosh", "weapon", "hathiyar", "chaaku", "knife",
    "attack", "hamla", "critical condition", "hospitalized", "hospital le gaye",
    "life threat", "life-threatening", "bleeding", "khoon beh raha",
    "collapsed", "gir gaya aur behosh", "electrocuted", "current laga", "करंट लगा",
    "drown", "doob", "kidnap", "assault", "rape", "chhed",
    "spark", "sparking", "high voltage", "wire hanging", "loose wire",
]

LOW_URGENCY_CUES = [
    "not urgent", "no rush", "jab bhi", "koi jaldi nahi", "whenever possible",
    "whenever convenient", "just feedback", "general feedback", "suggestion hai",
    "minor issue", "chhoti si baat", "not an emergency", "urgent nahi hai",
    "not a big deal", "small complaint", "just a query", "sirf jaankari",
    "thank you", "resolved", "already fixed", "just for information",
]


LOW_URGENCY_CLOSERS = [
    " Yeh koi emergency nahi hai, jab bhi convenient ho dekh lijiye.",
    " This is not urgent, just wanted to flag it whenever possible.",
    " Sirf feedback ke roop mein bata raha hoon, koi jaldi nahi hai.",
    " Not a big deal, but please note it down for the record.",
    " Just for information, no rush on this from our side.",
    " Koi urgent baat nahi hai, bas suggestion samajh kar dekh lena.",
]

HIGH_URGENCY_CLOSERS = [
    " Kal isi wajah se ek chhota accident bhi ho gaya tha.",
    " Someone was slightly injured because of this yesterday.",
    " Yeh ab ek emergency ban chuka hai, turant madad chahiye.",
]


def maybe_inject_urgency_modifier(text):
    r = random.random()
    if r < 0.13:
        return text.rstrip(".") + "." + random.choice(LOW_URGENCY_CLOSERS)
    if r < 0.13 + 0.05:
        return text.rstrip(".") + "." + random.choice(HIGH_URGENCY_CLOSERS)
    return text


def _cue_matches(cue, text_lower):
    """Substring match for cues containing non-ASCII (Devanagari) text -
    those phrases are specific enough that accidental collisions aren't a
    real risk. Word-boundary regex match for ASCII cues, so e.g. the cue
    "gun" doesn't fire on the city name "Guntur"."""
    cue = cue.lower()
    if not cue.isascii():
        return cue in text_lower
    pattern = r"\b" + re.escape(cue) + r"\b"
    return re.search(pattern, text_lower) is not None


def derive_urgency(text):
    t = text.lower()
    for cue in HIGH_URGENCY_CUES:
        if _cue_matches(cue, t):
            return "high"
    for cue in LOW_URGENCY_CUES:
        if _cue_matches(cue, t):
            return "low"
    return "medium"


# ----------------------------------------------------------------------
# Department definitions
#
# Each department has:
#   sector, department (label)
#   complaint_types: list of dicts with:
#       type: the literal complaint-type string (kept for schema parity)
#       fragments: list of (text, has_keyword) situation strings across
#                  English / Hinglish (code-mixed, Latin script) / pure
#                  Hindi (Devanagari). Roughly half omit the literal
#                  keyword and describe the symptom instead.
# ----------------------------------------------------------------------

DEPARTMENTS = {}


def add_dept(key, sector, department, complaint_types):
    DEPARTMENTS[key] = {
        "sector": sector,
        "department": department,
        "complaint_types": complaint_types,
    }


add_dept("pwd", "Roads & Infrastructure", "Public Works Department (PWD)", [
    {
        "type": "Pothole",
        "fragments": [
            ("Pothole ki problem hai hamare area mein bahut dino se.", True),
            ("There is a big pothole on our street that nobody has fixed.", True),
            ("Sadak par itna bada gaddha hai ki kal ek bike wala gir gaya, ghutna toot gaya uska.", False),
            ("There's a deep hole in the road right outside our gate, cars keep swerving to avoid it and almost hit each other.", False),
            ("सड़क पर इतना बड़ा गड्ढा बन गया है कि बारिश में पानी भर जाता है और दिखता ही नहीं, कल एक स्कूटर वाला गिर गया।", False),
            ("Raat mein andhere mein gaddha dikhta nahi aur do baar gir chuke hain log.", False),
        ],
    },
    {
        "type": "Broken Footpath",
        "fragments": [
            ("Broken Footpath ki wajah se paidal chalna mushkil hai.", True),
            ("The footpath near our lane is completely broken.", True),
            ("Humara footpath itna tuta hua hai ki chalna mushkil ho gaya hai, khaas kar raat mein.", False),
            ("Old people in our lane keep tripping on the broken tiles, my grandmother almost fell last week.", False),
            ("पैदल रास्ते के पत्थर उखड़ गए हैं, अंधेरे में बच्चे ठोकर खाकर गिर जाते हैं।", False),
            ("Footpath par itni badi darar hai ki pram push karna namumkin hai.", False),
        ],
    },
    {
        "type": "Damaged Road Divider",
        "fragments": [
            ("Damaged Road Divider hai humare chowk par, please theek karwaiye.", True),
            ("The road divider near the market has been broken for months.", True),
            ("Chowraahe ka divider tuta pada hai, gaadiyan galat side se aa jaati hain.", False),
            ("The concrete divider is smashed and sticking out with exposed rods, two scooters have already hit it.", False),
            ("टूटा हुआ डिवाइडर सड़क के बीचोंबीच पड़ा है, रात में गाड़ी वाले उससे टकरा जाते हैं।", False),
            ("Divider ke tukde sadak par bikhre pade hain kai hafte se, koi hata nahi raha.", False),
        ],
    },
    {
        "type": "Bridge Damage",
        "fragments": [
            ("Bridge Damage ho gaya hai humare gaon ke paas wale pul mein.", True),
            ("There is serious Bridge Damage on the highway crossing near us.", True),
            ("Pul ki rail toot gayi hai aur neeche crack dikh raha hai, dar lagta hai paar karte waqt.", False),
            ("The old bridge over the canal has visible cracks in the pillars and shakes when a truck crosses it.", False),
            ("पुल का एक हिस्सा टूट कर लटक गया है, कभी भी गिर सकता है, नीचे बच्चे खेलते हैं।", False),
            ("Bridge itna kamzor ho gaya hai ki heavy vehicle jaate waqt poora hilta hai.", False),
        ],
    },
    {
        "type": "Missing Manhole Cover",
        "fragments": [
            ("Missing Manhole Cover hai humari gali mein, koi gir sakta hai.", True),
            ("A Missing Manhole Cover on our main road is a serious hazard.", True),
            ("Gali ke beech mein khula manhole hai, raat mein andhere mein koi bhi gir sakta hai.", False),
            ("The open drain hole near the bus stop has no cover, a child almost fell into it yesterday evening.", False),
            ("मैनहोल का ढक्कन गायब है और वहां से बदबूदार गंदा पानी भी बह रहा है।", False),
            ("Khula gattar hai school ke raste mein, bachche daudte waqt dhyan nahi dete.", False),
        ],
    },
    {
        "type": "Streetlight Not Working",
        "fragments": [
            ("Streetlight Not Working humari gali mein pichle mahine se.", True),
            ("The Streetlight Not Working on our lane makes it very unsafe at night.", True),
            ("Kal raat se gali ki batti bandh hai, andhera hone ke baad koi bahar nikalne se darta hai.", False),
            ("It's pitch dark on our street after 8pm because the pole light has been out for weeks, women are scared to walk home.", False),
            ("गली की लाइट कई महीनों से खराब है, अंधेरे में चोरी होने का डर रहता है।", False),
            ("Poora mohalla andhere mein doob jaata hai raat ko, khambhe ki batti fuse ho gayi.", False),
        ],
    },
])

add_dept("water", "Water Supply", "Water Board", [
    {
        "type": "No Water Supply",
        "fragments": [
            ("No Water Supply in our colony since three days.", True),
            ("No Water Supply hai humare area mein subah se.", True),
            ("Nal mein teen din se ek boond bhi pani nahi aaya, bartan bhi nahi dho paaye.", False),
            ("Humein paani lene ke liye 2 km door jaana padta hai kyunki yahan supply band ho gayi hai.", False),
            ("हमारे मोहल्ले में तीन दिन से नल सूखे पड़े हैं, बर्तन धोने तक का पानी नहीं है।", False),
            ("We have had to buy water tankers every day this week because nothing comes from the pipeline.", False),
        ],
    },
    {
        "type": "Low Water Pressure",
        "fragments": [
            ("Low Water Pressure ki complaint hai humari building mein.", True),
            ("There is Low Water Pressure in our tap since last week.", True),
            ("Nal se itni dheemi dhaar aati hai ki bucket bharne mein aadha ghanta lag jaata hai.", False),
            ("The tap barely trickles in the morning, we can't even fill one bucket before it stops.", False),
            ("नल में पानी का प्रेशर इतना कम है कि ऊपर की मंज़िल तक पहुंचता ही नहीं।", False),
            ("Pehli manzil tak paani chadhta hi nahi, roz subah dikkat hoti hai.", False),
        ],
    },
    {
        "type": "Water Leakage",
        "fragments": [
            ("Water Leakage ho raha hai humari sadak ke neeche wali pipeline mein.", True),
            ("A Water Leakage near our house is wasting a lot of clean water.", True),
            ("Sadak ke bagal se paani ka fountain jaisa nikal raha hai kai dino se, sadak bhi kharab ho rahi hai.", False),
            ("Clean drinking water has been gushing out of a cracked pipe on the roadside for a week, nobody has come to fix it.", False),
            ("सड़क किनारे पाइप फट गया है और लगातार पानी बह रहा है, सड़क कीचड़ हो गई है।", False),
            ("Pipeline se paani behta rehta hai roz raat ko, aas paas kichad ho gaya hai.", False),
        ],
    },
    {
        "type": "Broken Water Pipeline",
        "fragments": [
            ("Broken Water Pipeline hai humare road ke neeche, urgent repair chahiye.", True),
            ("There is a Broken Water Pipeline that has flooded half our street.", True),
            ("Zameen ke andar ki pipe phat gayi hai, poori gali mein paani bhar gaya hai.", False),
            ("The main pipe under our lane burst last night and now the whole road is underwater, two-wheelers can't pass.", False),
            ("पानी की मुख्य लाइन फट गई है, पूरी सड़क तालाब बन गई है और घरों में पानी घुस रहा है।", False),
            ("Pipeline phatne se ghar ke andar tak paani aa gaya, saman kharab ho gaya.", False),
        ],
    },
    {
        "type": "Illegal Water Connection",
        "fragments": [
            ("Illegal Water Connection li gayi hai padosi ne, humara pressure kam ho gaya hai.", True),
            ("There is an Illegal Water Connection tapped from the main line near the market.", True),
            ("Kisi ne bina permission ke seedhe mukhya pipeline se connection le liya hai, humara supply kam ho gaya.", False),
            ("Someone has tapped a pipe directly from the main line without permission and our supply has dropped since then.", False),
            ("पड़ोसी ने बिना अनुमति के सीधे मुख्य पाइप से कनेक्शन ले लिया है, अब हमारे यहाँ पानी नहीं आता।", False),
            ("Naye connection ke baad se hamare ghar mein pura din paani nahi aata.", False),
        ],
    },
    {
        "type": "Sewage Overflow",
        "fragments": [
            ("Sewage Overflow ho raha hai humari gali mein, bahut ganda paani bhar gaya hai.", True),
            ("There is Sewage Overflow near the water tank, we are scared it will mix with drinking water.", True),
            ("Ganda paani nikal kar seedha sadak par bahne laga hai, badbu se rehna mushkil hai.", False),
            ("Dirty sewage water has started overflowing right next to our drinking water tank, we are worried it's contaminating it.", False),
            ("नाले का गंदा पानी घरों के अंदर तक आ गया है, बीमारी फैलने का डर है।", False),
            ("The tap water has started smelling strange and turning slightly yellow since yesterday.", False),
        ],
    },
])

add_dept("electricity", "Electricity", "State Electricity Board", [
    {
        "type": "Power Outage",
        "fragments": [
            ("Power Outage hai humare area mein kal raat se.", True),
            ("There has been a Power Outage in our locality for two days.", True),
            ("Kal raat se andhera hai poore mohalle mein, bachche darr rahe hain.", False),
            ("We have had no electricity since last night, the fridge full of medicine is going to spoil.", False),
            ("पूरे मोहल्ले में कल रात से बिजली गायब है, अंधेरे में बच्चे डर रहे हैं।", False),
            ("Bijli itni der se gayi hai ki inverter bhi discharge ho gaya, pankha tak nahi chal raha.", False),
        ],
    },
    {
        "type": "Frequent Voltage Fluctuation",
        "fragments": [
            ("Frequent Voltage Fluctuation ki wajah se humare appliances kharab ho rahe hain.", True),
            ("There is Frequent Voltage Fluctuation every evening in our street.", True),
            ("Roz shaam ko light itni kam-zyada hoti hai ki TV aur fridge baar baar band ho jaate hain.", False),
            ("The lights keep dimming and brightening every few minutes in the evening, we've already lost one television to it.", False),
            ("शाम होते ही वोल्टेज इतना कम-ज्यादा होता है कि पंखा धीमा हो जाता है और बल्ब झिलमिलाते हैं।", False),
            ("Voltage ka utar chadhav itna zyada hai ki charger tak kaam nahi karta theek se.", False),
        ],
    },
    {
        "type": "Damaged Transformer",
        "fragments": [
            ("Damaged Transformer hai humare mohalle ke khambhe par.", True),
            ("There is a Damaged Transformer sparking near the school gate.", True),
            ("Khambhe par laga transformer se dhuan aur awaaz aa rahi hai kai dino se.", False),
            ("The transformer on the pole near our house makes a loud buzzing sound and smells of burning, we're worried it will catch fire.", False),
            ("बिजली के खंभे पर लगा ट्रांसफार्मर से चिंगारियां निकल रही हैं, कभी भी आग लग सकती है।", False),
            ("Transformer se kabhi kabhi tez chatak ki awaaz aati hai, dar lagta hai pass jaane mein.", False),
        ],
    },
    {
        "type": "Exposed Live Wire",
        "fragments": [
            ("Exposed Live Wire latki hui hai humare ghar ke bahar, please fix karwaiye.", True),
            ("There is an Exposed Live Wire near the bus stop that could hurt someone.", True),
            ("There's a wire hanging low near the school gate, sparking every time it rains, someone is going to get hurt.", False),
            ("Bijli ka tar bahut neeche latak raha hai gali mein, kal ek bachcha usse takraate takraate bacha.", False),
            ("स्कूल के गेट के पास बिजली का तार लटक रहा है और बारिश में चिंगारियां निकलती हैं, कोई भी घायल हो सकता है।", False),
            ("Neeche latka hua tar barish mein current laga sakta hai, bahut dar lagta hai bacchon ko bhejne mein.", False),
        ],
    },
    {
        "type": "Meter Reading Error",
        "fragments": [
            ("Meter Reading Error ki wajah se bill bahut zyada aaya hai.", True),
            ("There is a Meter Reading Error, our bill doubled without extra usage.", True),
            ("Meter reading galat aa rahi hai, bill double ho gaya iss mahine bina extra use kiye.", False),
            ("Our electricity bill jumped to nearly double this month even though we used the same appliances as always.", False),
            ("मीटर की रीडिंग गलत आ रही है, इस महीने बिल दोगुना आ गया है बिना किसी वजह के।", False),
            ("Bill mein galat units dikhaye gaye hain, complaint diye ek hafta ho gaya koi jawab nahi.", False),
        ],
    },
    {
        "type": "Streetlight Fault (Electrical)",
        "fragments": [
            ("Streetlight ka wiring fault hai, bar bar spark hoti hai khambhe se.", True),
            ("The pole near our house sparks every time it drizzles, this is an electrical fault.", True),
            ("Khambhe se chingari nikalti hai halki barish mein bhi, log darte hain uske paas se guzarne mein.", False),
            ("Every time it drizzles, the streetlight pole near the temple throws sparks and everyone avoids walking under it.", False),
            ("हल्की बारिश में भी खंभे से चिंगारी निकलती है, लोग डर के मारे रास्ता बदल लेते हैं।", False),
            ("Pole ke paas se guzarna khatarnak ho gaya hai, kal ek cycle wala usse takra gaya tha.", False),
        ],
    },
])

add_dept("sanitation", "Sanitation & Waste", "Municipal Corporation - Sanitation", [
    {
        "type": "Garbage Not Collected",
        "fragments": [
            ("Garbage Not Collected in our street for one week.", True),
            ("Garbage Not Collected hai humari gali mein kai dino se.", True),
            ("Gali mein kachre ka dher lag gaya hai, machhar bahut ho gaye hain, bachchon ko bimari ka darr hai.", False),
            ("A huge pile of trash has built up at the corner of our lane and mosquitoes have multiplied badly, we're worried about dengue.", False),
            ("गली के कोने में कचरे का ढेर लगा हुआ है, मक्खी मच्छर से बीमारी फैलने का डर है।", False),
            ("Kachra gaadi kai hafte se nahi aayi, poora mohalla kachre se bhar gaya hai.", False),
        ],
    },
    {
        "type": "Overflowing Dustbin",
        "fragments": [
            ("Overflowing Dustbin hai market ke paas, kachra sadak par bikhar raha hai.", True),
            ("There is an Overflowing Dustbin near our society gate for days.", True),
            ("Kachre ka dabba itna bhar gaya hai ki kachra chhalak kar sadak par pheli gaya hai.", False),
            ("The community bin has been spilling over onto the pavement for days and stray dogs keep dragging the trash further out.", False),
            ("कूड़ेदान इतना भर गया है कि कचरा सड़क पर फैल गया है, बदबू से चलना मुश्किल है।", False),
            ("Dustbin ke aas paas kachra hi kachra hai, koi cleaning staff nahi aata.", False),
        ],
    },
    {
        "type": "Illegal Dumping",
        "fragments": [
            ("Illegal Dumping ho raha hai khaali plot mein, health hazard ban gaya hai.", True),
            ("Illegal Dumping of construction waste is blocking our lane entrance.", True),
            ("Koi khaali plot mein raat ko chup chap kachra fenk jaata hai, bahut badbu aati hai.", False),
            ("Someone keeps dumping construction debris right at the entrance of our lane at night, it's now blocking two-wheelers.", False),
            ("खाली प्लॉट में कोई रात के अंधेरे में कचरा फेंक जाता है, वहां से बहुत बदबू आती है।", False),
            ("Plot mein padi ganda saman se saanp aur chuhe aane lage hain.", False),
        ],
    },
    {
        "type": "Blocked Drain",
        "fragments": [
            ("Blocked Drain hai humari gali mein, paani bahar aa raha hai.", True),
            ("There is a Blocked Drain outside our house causing water to stagnate.", True),
            ("The drain outside our house has been blocked for two weeks and now dirty water is coming into the lane.", False),
            ("Nali band ho gayi hai do hafte se, ganda paani ab gali mein ghusne laga hai.", False),
            ("नाली दो हफ्ते से जाम है, अब गंदा पानी गली में घुसने लगा है और मक्खी बहुत हैं।", False),
            ("Barsaat ka paani nikalne ki jagah nahi hai, ghar ke saamne talab ban jaata hai.", False),
        ],
    },
    {
        "type": "Public Toilet Unclean",
        "fragments": [
            ("Public Toilet Unclean hai station ke paas, jaana mushkil hai.", True),
            ("The Public Toilet Unclean condition near the market is unbearable.", True),
            ("Bahut badbu aa rahi hai humare area mein, kisi ne safai nahi ki lagta hai.", False),
            ("The public toilet near the bus stand hasn't been cleaned in weeks, women avoid using it entirely now.", False),
            ("सार्वजनिक शौचालय में इतनी गंदगी है कि अंदर जाना भी मुश्किल है, कई हफ्तों से सफाई नहीं हुई।", False),
            ("Toilet ka darwaza bhi tuta hua hai aur paani ki tanki khaali rehti hai.", False),
        ],
    },
    {
        "type": "Noise Complaint (Municipal)",
        "fragments": [
            ("Noise Complaint hai humare area mein loudspeaker ki wajah se.", True),
            ("A Noise Complaint about the garbage truck's early morning horn, it wakes the whole street.", True),
            ("Subah 5 baje kachre ki gaadi ka horn poora mohalla jaga deta hai.", False),
            ("The garbage collection truck blares its horn at 5am every day and wakes up the entire street including newborns.", False),
            ("सुबह पांच बजे ही कचरा गाड़ी का हॉर्न पूरा मोहल्ला जगा देता है, नवजात बच्चे परेशान हो जाते हैं।", False),
            ("Itni tez awaaz aati hai roz subah ki neend hi toot jaati hai.", False),
        ],
    },
])

add_dept("health", "Healthcare", "Department of Health & Family Welfare", [
    {
        "type": "Doctor Absent",
        "fragments": [
            ("Doctor Absent at PHC since morning.", True),
            ("Doctor Absent hai health center mein pichle teen din se.", True),
            ("Hum subah 6 baje pahunche the PHC lekin dopahar tak koi doctor nahi aaya.", False),
            ("We reached the health center at 6am and waited till noon but no doctor showed up at all.", False),
            ("हम सुबह छह बजे स्वास्थ्य केंद्र पहुंचे थे लेकिन दोपहर तक कोई डॉक्टर नहीं आया।", False),
            ("PHC mein sirf ek compounder baitha hai, doctor kai dino se nahi aa rahe.", False),
        ],
    },
    {
        "type": "Medicine Shortage",
        "fragments": [
            ("Medicine Shortage hai government hospital mein.", True),
            ("There is a Medicine Shortage at the PHC for basic tablets.", True),
            ("Dawaiyan khatam ho gayi hain government hospital mein pichle hafte se.", False),
            ("The government hospital pharmacy has been out of basic fever and BP medicine for over a week now.", False),
            ("सरकारी अस्पताल में पिछले हफ्ते से दवाइयां खत्म हैं, बाहर से खरीदनी पड़ रही हैं।", False),
            ("Free dawa ki jagah bahar se khareedni pad rahi hai, gareeb logon ke liye mushkil hai.", False),
        ],
    },
    {
        "type": "Ambulance Delay",
        "fragments": [
            ("Ambulance Delay hui thi jab meri maa ko emergency thi.", True),
            ("There was an Ambulance Delay of over an hour during a critical case.", True),
            ("Call kiya tha ambulance ke liye kyunki mere pitaji ko seene mein dard tha, ek ghante baad bhi nahi aayi.", False),
            ("We called for an ambulance because my father was having severe chest pain and it took more than an hour to arrive.", False),
            ("मेरे पिताजी को सीने में दर्द था, एम्बुलेंस बुलाई थी पर एक घंटे बाद भी नहीं आई।", False),
            ("Ambulance ka number hi kaam nahi kar raha tha emergency ke waqt, jaan ka khatra tha.", False),
        ],
    },
    {
        "type": "Overcharging at PHC",
        "fragments": [
            ("Overcharging at PHC ho rahi hai, free treatment ke liye bhi paisa maang rahe hain.", True),
            ("There is Overcharging at PHC for tests that are supposed to be free.", True),
            ("Free test ke liye bhi staff ne paisa maanga, jabki yeh government scheme mein free hai.", False),
            ("The staff asked for money for a blood test that is supposed to be free under the government scheme.", False),
            ("जो जांच मुफ्त होनी चाहिए उसके लिए भी स्टाफ पैसे मांग रहा है।", False),
            ("Bina receipt diye paisa le liya gaya OPD card banwane ke liye bhi.", False),
        ],
    },
    {
        "type": "Unhygienic Ward Conditions",
        "fragments": [
            ("Unhygienic Ward Conditions hain hospital ke general ward mein.", True),
            ("There are Unhygienic Ward Conditions, bedsheets have not been changed in days.", True),
            ("Ward mein chuhe ghoomte hain aur bedsheet kai dino se nahi badli gayi.", False),
            ("There are rats running around the general ward at night and the bedsheets haven't been changed in days.", False),
            ("वार्ड में चूहे घूमते रहते हैं और चादरें कई दिनों से नहीं बदली गई हैं, मरीज़ों को इंफेक्शन का डर है।", False),
            ("Patient ko infection ka khatra hai itni gandagi ki wajah se.", False),
        ],
    },
    {
        "type": "No Female Doctor Available",
        "fragments": [
            ("No Female Doctor Available at the PHC for check-ups.", True),
            ("There is No Female Doctor Available, women have to travel 20km for a checkup.", True),
            ("Yahan koi mahila doctor nahi hai, aurton ko checkup ke liye 20 km door jaana padta hai.", False),
            ("Women in our village have to travel twenty kilometers just to get a basic checkup because there's no woman doctor posted here.", False),
            ("यहां कोई महिला डॉक्टर नहीं है, महिलाओं को जांच के लिए बीस किलोमीटर दूर जाना पड़ता है।", False),
            ("Meri saas ko dikhane ke liye dusre shehar jaana pada kyunki yahan koi lady doctor hi nahi hai.", False),
        ],
    },
])

add_dept("education", "Education", "Department of School Education", [
    {
        "type": "Teacher Absenteeism",
        "fragments": [
            ("Teacher Absenteeism at school is a big problem.", True),
            ("Teacher Absenteeism hai school mein, bachchon ki padhai chhoot rahi hai.", True),
            ("Mahine mein sirf 5-6 din hi padhai hoti hai, baaki din koi sir nahi aate.", False),
            ("Classes only actually happen five or six days a month, the rest of the time no teacher shows up at all.", False),
            ("महीने में सिर्फ पांच-छह दिन ही पढ़ाई होती है, बाकी दिन कोई शिक्षक नहीं आते।", False),
            ("Bachche school jaate hain lekin teacher na hone ki wajah se khaali baithe rehte hain.", False),
        ],
    },
    {
        "type": "School Building Damage",
        "fragments": [
            ("School Building Damage hai, chhat se paani tapakta hai.", True),
            ("There is School Building Damage, a wall developed a crack after the rains.", True),
            ("The roof of the classroom is leaking and children have to sit in the corridor when it rains.", False),
            ("Classroom ki chhat se barish ka paani tapakta hai, bachche corridor mein baithte hain.", False),
            ("स्कूल की छत से बारिश का पानी टपकता है, बच्चों को बरामदे में बैठना पड़ता है।", False),
            ("Deewar mein badi darar aa gayi hai barish ke baad, girne ka darr hai.", False),
        ],
    },
    {
        "type": "Lack of Toilets in School",
        "fragments": [
            ("Lack of Toilets in School hai, ladkiyon ko bahut dikkat hoti hai.", True),
            ("Due to Lack of Toilets in School, many girls skip school during periods.", True),
            ("School mein toilet hi nahi hai, ladkiyan sharam ki wajah se school aana kam kar deti hain.", False),
            ("There are no functioning toilets at school, so many girls have started skipping classes altogether.", False),
            ("स्कूल में शौचालय ही नहीं है, इस वजह से कई लड़कियां स्कूल आना कम कर देती हैं।", False),
            ("Jo toilet hai wo band pada hai kai mahino se, taala laga hai usme.", False),
        ],
    },
    {
        "type": "Mid-Day Meal Quality",
        "fragments": [
            ("Mid-Day Meal Quality bahut kharab hai school mein.", True),
            ("There is a Mid-Day Meal Quality issue, food often has insects in it.", True),
            ("Bachchon ko khaana milta hai lekin usme keede dikhte hain kabhi kabhi.", False),
            ("Children are served lunch at school but sometimes there are small insects visible in the rice.", False),
            ("बच्चों को दोपहर का खाना मिलता है लेकिन कभी-कभी उसमें कीड़े दिखते हैं।", False),
            ("Khaana theek se pakta hi nahi, kacha chawal diya jaata hai kabhi kabhi.", False),
        ],
    },
    {
        "type": "Fee Overcharging",
        "fragments": [
            ("Fee Overcharging ho rahi hai private school mein bina notice ke.", True),
            ("There is Fee Overcharging, the school raised fees without informing parents.", True),
            ("School ne bina bataye fees badha di hai, parents ko koi notice nahi diya gaya.", False),
            ("The school increased fees suddenly without sending any notice to parents this term.", False),
            ("स्कूल ने बिना बताए फीस बढ़ा दी है, अभिभावकों को कोई सूचना नहीं दी गई।", False),
            ("Extra activity fund ke naam par bhi paisa maanga ja raha hai bar bar.", False),
        ],
    },
    {
        "type": "Overcrowded Classroom",
        "fragments": [
            ("Overcrowded Classroom hai, ek room mein 80 bachche baithte hain.", True),
            ("There is an Overcrowded Classroom problem, benches are shared by four students.", True),
            ("Ek hi kamre mein 80 bachche baithte hain, thik se baith bhi nahi paate.", False),
            ("Eighty children are packed into one small room and they can't even sit properly on the benches.", False),
            ("एक ही कमरे में अस्सी बच्चे बैठते हैं, ठीक से बैठने की जगह भी नहीं है।", False),
            ("Bench par char bachche baithte hain, kitab rakhne ki jagah tak nahi hai.", False),
        ],
    },
])

add_dept("transport", "Public Transport", "State Transport Corporation", [
    {
        "type": "Bus Not Arriving on Time",
        "fragments": [
            ("Bus Not Arriving on Time on our route for weeks.", True),
            ("Bus Not Arriving on Time hai, office ke liye late ho jaate hain roz.", True),
            ("Subah office jaane ke liye ghanta khada rehna padta hai, koi bus hi nahi aati is route par.", False),
            ("We stand at the stop for a full hour every morning and the bus on this route simply doesn't show up.", False),
            ("सुबह ऑफिस जाने के लिए घंटों खड़ा रहना पड़ता है, इस रूट पर बस ही नहीं आती।", False),
            ("Timetable ke hisab se bus kabhi nahi aati, schedule bekaar hai.", False),
        ],
    },
    {
        "type": "Bus Route Cancelled",
        "fragments": [
            ("Bus Route Cancelled kar diya gaya hai bina notice ke.", True),
            ("Our Bus Route Cancelled suddenly and now we have no way to reach the station.", True),
            ("Yeh route achanak band kar diya gaya, ab station tak jaane ka koi sadhan nahi bacha.", False),
            ("Overnight the only bus connecting our village to the station stopped running with no explanation.", False),
            ("हमारे गांव से स्टेशन जाने वाली बस अचानक बंद कर दी गई, कोई सूचना भी नहीं दी गई।", False),
            ("Ab school jaane wale bachchon ke liye koi bus nahi bachi is area mein.", False),
        ],
    },
    {
        "type": "Rude Conductor Behavior",
        "fragments": [
            ("Rude Conductor Behavior tha aaj bus mein, senior citizen ke saath.", True),
            ("There was Rude Conductor Behavior, he shouted at an elderly passenger over fare.", True),
            ("Conductor ne ek budhe passenger ko ticket ke paise ko lekar bahut bura bola.", False),
            ("The conductor yelled at an elderly passenger over a five rupee fare dispute in front of everyone.", False),
            ("कंडक्टर ने एक बुजुर्ग यात्री को किराए को लेकर सबके सामने बहुत बुरा-भला कहा।", False),
            ("Halka sa argument hua tha ticket ko lekar aur conductor bahut zor se chillane laga.", False),
        ],
    },
    {
        "type": "Damaged Bus Stop",
        "fragments": [
            ("Damaged Bus Stop hai, shelter ka chhat gir gaya hai.", True),
            ("There is a Damaged Bus Stop shelter, the roof collapsed after the storm.", True),
            ("Bus stop ka shed toofan mein gir gaya, ab dhoop aur barish mein khada rehna padta hai.", False),
            ("The bus stop shelter roof caved in during the last storm, now we stand in the sun and rain waiting.", False),
            ("बस स्टॉप का शेड तूफान में गिर गया, अब धूप और बारिश में खड़ा रहना पड़ता है।", False),
            ("Bench bhi tooti padi hai bus stop par, baithne ki jagah nahi bachi.", False),
        ],
    },
    {
        "type": "Overcharging by Auto/Taxi",
        "fragments": [
            ("Overcharging by Auto ho rahi hai station ke bahar meter ke bina.", True),
            ("There is Overcharging by Taxi drivers refusing to use the meter.", True),
            ("Auto wale meter se dugna paisa maang rahe hain station se.", False),
            ("Auto drivers outside the station are demanding almost double the metered fare and refusing to negotiate.", False),
            ("स्टेशन के बाहर ऑटो वाले मीटर से दोगुना पैसा मांगते हैं और मीटर लगाने से मना कर देते हैं।", False),
            ("Raat ko taxi wale bahut zyada paisa maangte hain, majboori mein dena padta hai.", False),
        ],
    },
    {
        "type": "Driver Skipping Stops",
        "fragments": [
            ("Driver Skipping Stops kar raha tha, humein chadhne hi nahi diya.", True),
            ("Driver Skipping Stops even when passengers are visibly waiting and waving.", True),
            ("The driver just skipped our stop even though five of us were standing there waving.", False),
            ("Driver ne humara stop skip kar diya jabki paanch log wahan khade the hath hilate hue.", False),
            ("ड्राइवर ने हमारा स्टॉप छोड़ दिया जबकि पांच लोग वहां हाथ हिलाते हुए खड़े थे।", False),
            ("Bus roki hi nahi, seedhe nikal gayi bina rukein.", False),
        ],
    },
])

add_dept("police", "Police & Public Safety", "Police Department", [
    {
        "type": "Theft Report Delay",
        "fragments": [
            ("Theft Report Delay hai, FIR abhi tak nahi bani.", True),
            ("There is a Theft Report Delay, I filed it a week ago with no update.", True),
            ("Kal raat ghar ka taala tod kar koi cheezein le gaya, hum bahut dare hue hain.", False),
            ("Someone broke the lock on our house last night and took our belongings, we're still shaken up.", False),
            ("कल रात घर का ताला तोड़कर कोई सामान ले गया, हम बहुत डरे हुए हैं।", False),
            ("Maine complaint di thi ek hafta pehle lekin abhi tak koi report nahi bani.", False),
        ],
    },
    {
        "type": "Eve-teasing/Harassment",
        "fragments": [
            ("Eve-teasing/Harassment ho raha hai college gate ke paas roz.", True),
            ("There is Eve-teasing/Harassment near the girls' hostel every evening.", True),
            ("A group of men have been following girls near the college gate every evening, everyone is scared to walk alone now.", False),
            ("Kuch ladke roz shaam college gate ke paas ladkiyon ka peecha karte hain, sab akele jaane se darte hain.", False),
            ("कुछ लड़के रोज़ शाम कॉलेज गेट के पास लड़कियों का पीछा करते हैं, सब अकेले जाने से डरते हैं।", False),
            ("Bus stop par kuch ladke rukwa ke tang karte hain roz, complaint ke baad bhi kuch nahi hua.", False),
        ],
    },
    {
        "type": "FIR Not Registered",
        "fragments": [
            ("FIR Not Registered even after three visits to the station.", True),
            ("FIR Not Registered hai humari, thane wale bol rahe baad mein aana.", True),
            ("Thane teen baar gaye lekin har baar bola gaya baad mein aana, report likhi hi nahi gayi.", False),
            ("We've gone to the police station three times and each time they say come later, nothing has been written down.", False),
            ("पुलिस स्टेशन तीन बार गए लेकिन हर बार बोला गया बाद में आना, रिपोर्ट लिखी ही नहीं गई।", False),
            ("Ek mahine se ghoom rahe hain report likhwane ke liye, koi sun hi nahi raha.", False),
        ],
    },
    {
        "type": "Violent Crime - Assault/Shooting",
        "fragments": [
            ("There is maar pit in my area one person has shoot the other person he is dead on spot", False),
            ("Kal raat humare mohalle mein do groups ke beech maarpeet ho gayi, ek ladke ko chaaku laga hai bahut khoon beh raha tha.", False),
            ("Someone was shot outside the tea stall near our house, there is blood on the road and he is not moving.", False),
            ("आज सुबह हमारे मोहल्ले में झगड़े के दौरान एक व्यक्ति को गोली लग गई, वह वहीं गिर गया और खून बह रहा है।", False),
            ("Do log gali maar rahe the aur phir achanak ek ne dusre ko chaku se maar diya, sab log dar ke bhaag gaye.", False),
            ("There was a big fight near the market and someone pulled out a gun, one man is lying unconscious on the ground.", False),
        ],
    },
    {
        "type": "Domestic Violence Report",
        "fragments": [
            ("Domestic Violence Report file karni hai, padosi ki chillane ki awaaz roz aati hai.", True),
            ("Filing a Domestic Violence Report for the family next door, we hear screaming almost every night.", True),
            ("Padosi ke ghar se roz raat chillane aur maarne ki awaazein aati hain, dar lagta hai kuch bada ho jaayega.", False),
            ("We hear a woman screaming and things being thrown next door almost every night, we're worried something serious will happen.", False),
            ("पड़ोस के घर से रोज़ रात चीखने और मारपीट की आवाज़ें आती हैं, डर लगता है कुछ बड़ा हो जाएगा।", False),
            ("Kal raat awaaz itni tez thi ki bachche bhi rone lage, kisi ko madad ke liye bulaya nahi ja saka.", False),
        ],
    },
    {
        "type": "Illegal Encroachment (Public Safety)",
        "fragments": [
            ("Illegal Encroachment on public road is blocking emergency vehicle access.", True),
            ("Illegal Encroachment hai sadak par jisse ambulance tak nahi ja pati.", True),
            ("Sadak par kisi ne permanent tapri laga di hai, ambulance bhi nahi guzar pati emergency mein.", False),
            ("Someone has built a permanent stall right on the road, and an ambulance couldn't get through during an emergency last week.", False),
            ("सड़क पर किसी ने पक्की टपरी बना ली है, पिछले हफ्ते एम्बुलेंस तक नहीं गुज़र पाई।", False),
            ("Encroachment ki wajah se fire brigade ki gaadi bhi phasi thi ek baar.", False),
        ],
    },
])

add_dept("food", "Ration & Public Distribution", "Department of Food & Civil Supplies", [
    {
        "type": "Ration Shop Closed",
        "fragments": [
            ("Ration Shop Closed this month, we didn't get our quota.", True),
            ("Ration Shop Closed hai is mahine, koi wajah nahi bataayi gayi.", True),
            ("Is mahine dukaan hi nahi khuli, humein anaj nahi mil paaya.", False),
            ("The shop hasn't opened at all this month and we haven't received our grain quota.", False),
            ("इस महीने दुकान ही नहीं खुली, हमें अनाज नहीं मिल पाया।", False),
            ("Dukaandaar ka phone bhi band aa raha hai kai dino se.", False),
        ],
    },
    {
        "type": "Short Quantity in Ration",
        "fragments": [
            ("Short Quantity in Ration diya gaya humein is mahine.", True),
            ("There was a Short Quantity in Ration, we paid for 5kg but got only 3kg.", True),
            ("We paid for 5kg of rice but the shopkeeper only gave us 3kg, this happens every month.", False),
            ("Paanch kilo chawal ka paisa liya lekin sirf teen kilo diya, yeh har mahine hota hai.", False),
            ("पांच किलो चावल का पैसा लिया लेकिन सिर्फ तीन किलो दिया, यह हर महीने होता है।", False),
            ("Weight machine hi galat lagti hai dukaan mein, sabko kam milta hai.", False),
        ],
    },
    {
        "type": "Adulterated Ration Items",
        "fragments": [
            ("Adulterated Ration Items mile hain is baar, chawal mein keede the.", True),
            ("There were Adulterated Ration Items, the wheat had stones mixed in.", True),
            ("The rice we got from the government shop had a lot of stones and dirt mixed in it.", False),
            ("Sarkari dukaan se mila chawal patthar aur mitti se bhara hua tha.", False),
            ("सरकारी दुकान से मिला चावल पत्थर और मिट्टी से भरा हुआ था, खाने लायक नहीं था।", False),
            ("Aata itna purana tha ki usme keede pad gaye the.", False),
        ],
    },
    {
        "type": "Ration Card Not Issued",
        "fragments": [
            ("Ration Card Not Issued even after six months of application.", True),
            ("Ration Card Not Issued hai humari, office ke chakkar kaat kaat ke thak gaye.", True),
            ("Chhah mahine ho gaye application diye, card abhi tak nahi bana, office ke chakkar hi lagate rehte hain.", False),
            ("It's been six months since we applied and we still don't have the card, we keep going back and forth to the office.", False),
            ("छह महीने हो गए आवेदन दिए, कार्ड अभी तक नहीं बना, दफ्तर के चक्कर ही लगाते रहते हैं।", False),
            ("Har baar koi na koi document maang liya jaata hai, khatam hi nahi hota process.", False),
        ],
    },
    {
        "type": "Ration Card Correction Pending",
        "fragments": [
            ("Ration Card Correction Pending hai, naam mein spelling mistake hai.", True),
            ("There is a Ration Card Correction Pending, family member's name is missing.", True),
            ("Card mein naam ki spelling galat hai, correction ke liye do baar office jaa chuke hain.", False),
            ("There's a spelling mistake in my name on the card and we've been to the office twice to get it fixed with no result.", False),
            ("कार्ड में नाम की स्पेलिंग गलत है, सुधार के लिए दो बार दफ्तर जा चुके हैं।", False),
            ("Beti ka naam card mein judwana tha, form jama kiye do mahine ho gaye.", False),
        ],
    },
    {
        "type": "Dealer Overcharging",
        "fragments": [
            ("Dealer Overcharging kar raha hai fixed rate se zyada.", True),
            ("There is Dealer Overcharging, he demands cash above the government rate.", True),
            ("Dukaandaar sarkari rate se zyada paisa maangta hai, mana karne par ration dene se mana kar deta hai.", False),
            ("The dealer demands extra cash above the fixed rate and refuses to give the ration if we don't pay it.", False),
            ("दुकानदार सरकारी दर से ज़्यादा पैसा मांगता है, मना करने पर राशन देने से इनकार कर देता है।", False),
            ("Bill mein kam amount likha jaata hai lekin asal mein zyada liya jaata hai.", False),
        ],
    },
])

add_dept("social", "Pension & Social Welfare", "Department of Social Welfare", [
    {
        "type": "Pension Not Credited",
        "fragments": [
            ("Pension Not Credited this month, humein bahut dikkat ho rahi hai.", True),
            ("Pension Not Credited hai, dawai ke liye paisa nahi hai ab.", True),
            ("Dadi ka paisa iss mahine khaate mein nahi aaya, unki dawai ke liye zaroori tha.", False),
            ("My grandmother's pension didn't come into her account this month, and she needed that money for her medicine.", False),
            ("दादी का पैसा इस महीने खाते में नहीं आया, उनकी दवाई के लिए ज़रूरी था।", False),
            ("Bank account check kiya toh koi transfer hi nahi dikha is mahine.", False),
        ],
    },
    {
        "type": "Old Age Pension Rejected",
        "fragments": [
            ("Old Age Pension Rejected without giving any clear reason.", True),
            ("Old Age Pension Rejected hai humari, application dobara bhejni padegi kya samajh nahi aaya.", True),
            ("Application reject ho gayi bina koi reason bataye, ab samajh nahi aa raha kya karein.", False),
            ("The application was rejected without any explanation, we don't understand what document was missing.", False),
            ("आवेदन बिना किसी कारण के अस्वीकार कर दिया गया, समझ नहीं आ रहा कौन सा दस्तावेज़ कम था।", False),
            ("Do baar apply kiya, dono baar reject ho gaya bina wajah bataye.", False),
        ],
    },
    {
        "type": "Widow Pension Pending",
        "fragments": [
            ("Widow Pension Pending hai chhah mahine se, koi update nahi mila.", True),
            ("Widow Pension Pending, application submit kiye bahut waqt ho gaya.", True),
            ("Chhah mahine se application pending hai, office jaakar poochte hain toh sirf wait karne ko bolte hain.", False),
            ("It has been pending for six months and every time we visit the office they just tell us to keep waiting.", False),
            ("छह महीने से आवेदन लंबित है, दफ्तर जाकर पूछते हैं तो सिर्फ इंतजार करने को कहते हैं।", False),
            ("Meri maa ka form jama hue bahut din ho gaye, ghar ka kharcha chalana mushkil ho gaya hai.", False),
        ],
    },
    {
        "type": "Disability Certificate Delay",
        "fragments": [
            ("Disability Certificate Delay hai, four months ho gaye application ko.", True),
            ("There is a Disability Certificate Delay, my father needs it for a job application.", True),
            ("My father's disability certificate application has been stuck for four months with no update from anyone.", False),
            ("Mere pitaji ka disability certificate chaar mahine se atka hua hai, koi update hi nahi milta.", False),
            ("मेरे पिताजी का विकलांगता प्रमाण पत्र चार महीने से अटका हुआ है, कोई अपडेट नहीं मिलता।", False),
            ("Medical board ki date hi nahi mil rahi, baar baar postpone ho jaati hai.", False),
        ],
    },
    {
        "type": "Scholarship Not Disbursed",
        "fragments": [
            ("Scholarship Not Disbursed even after approval three months ago.", True),
            ("Scholarship Not Disbursed hai humari beti ki, form approve hue teen mahine ho gaye.", True),
            ("Beti ki scholarship ka form bhara tha lekin paisa abhi tak nahi mila.", False),
            ("Her scholarship form was approved three months ago but the money still hasn't reached her account.", False),
            ("बेटी की छात्रवृत्ति का फॉर्म भरा था लेकिन पैसा अभी तक नहीं मिला, कॉलेज फीस देनी है।", False),
            ("College fees ki last date aa rahi hai aur scholarship abhi tak nahi aayi.", False),
        ],
    },
    {
        "type": "Welfare Scheme Application Stuck",
        "fragments": [
            ("Welfare Scheme Application Stuck hai portal par kai mahino se.", True),
            ("A Welfare Scheme Application Stuck at verification stage, no officer responds.", True),
            ("Form portal par verification stage par atka hua hai, koi officer response hi nahi deta.", False),
            ("Our application has been stuck at the verification stage on the portal for months with no officer responding.", False),
            ("फॉर्म पोर्टल पर वेरिफिकेशन स्टेज पर अटका हुआ है, कोई अधिकारी जवाब ही नहीं देता।", False),
            ("Helpline number bhi lagta nahi hai kai baar try karne par.", False),
        ],
    },
])

add_dept("revenue", "Property & Land Records", "Revenue Department", [
    {
        "type": "Land Record Mismatch",
        "fragments": [
            ("Land Record Mismatch problem since 10 days, please correct.", True),
            ("Land Record Mismatch hai, mere pita ka naam galat likha hai.", True),
            ("Zameen ke kaagzaat mein mere pita ka naam galat likha hai, bank loan atka hua hai isi wajah se.", False),
            ("My father's name is spelled wrong on the land documents, and it's holding up our bank loan approval.", False),
            ("ज़मीन के कागज़ात में मेरे पिता का नाम गलत लिखा है, इसी वजह से बैंक लोन अटका हुआ है।", False),
            ("Survey number galat darj ho gaya hai records mein, correction ke liye bhatak rahe hain.", False),
        ],
    },
    {
        "type": "Registry Delay",
        "fragments": [
            ("Registry Delay ho rahi hai property ki, do mahine ho gaye.", True),
            ("There is a Registry Delay, all documents were submitted weeks ago.", True),
            ("We've been trying to get our property registered for six months, every visit they say come back next week.", False),
            ("Chhah mahine se registry karwane ki koshish kar rahe hain, har baar agle hafte aane ko bolte hain.", False),
            ("छह महीने से रजिस्ट्री करवाने की कोशिश कर रहे हैं, हर बार अगले हफ्ते आने को कहते हैं।", False),
            ("Documents complete hone ke baad bhi appointment hi nahi mil rahi.", False),
        ],
    },
    {
        "type": "Boundary Dispute",
        "fragments": [
            ("Boundary Dispute hai padosi ke saath zameen ko lekar.", True),
            ("There is a Boundary Dispute, neighbor has built a wall on our side.", True),
            ("Padosi ne humari zameen ki kuch hissa mein deewar bana di hai, unhe koi adhikar nahi hai.", False),
            ("Our neighbor has built a wall extending into part of our plot and refuses to move it despite having no legal right to it.", False),
            ("पड़ोसी ने हमारी ज़मीन के कुछ हिस्से में दीवार बना दी है, उन्हें कोई अधिकार नहीं है।", False),
            ("Zameen ki nishandehi ko lekar do parivaron mein jhagda chal raha hai kai saal se.", False),
        ],
    },
    {
        "type": "Mutation Delay",
        "fragments": [
            ("Mutation Delay ho rahi hai property purchase ke baad se.", True),
            ("There is a Mutation Delay, records still show the previous owner's name.", True),
            ("Property khareede kai mahine ho gaye lekin records mein abhi bhi purane malik ka naam hai.", False),
            ("It's been months since we bought the property but the records still show the previous owner's name.", False),
            ("संपत्ति खरीदे कई महीने हो गए लेकिन रिकॉर्ड में अभी भी पुराने मालिक का नाम है।", False),
            ("Tehsil office mein file kahan hai koi bata hi nahi pa raha.", False),
        ],
    },
    {
        "type": "Illegal Encroachment (Land)",
        "fragments": [
            ("Illegal Encroachment on our agricultural land by a neighboring farmer.", True),
            ("Illegal Encroachment hai, padosi ne humari kheti ki zameen par kabza kar liya.", True),
            ("Padosi kisan ne dheere dheere humari zameen ki side badha li hai apni fasal lagakar.", False),
            ("The neighboring farmer has slowly extended his crop line into our field over the past two seasons.", False),
            ("पड़ोसी किसान ने धीरे-धीरे हमारी ज़मीन की सीमा बढ़ा ली है अपनी फसल लगाकर।", False),
            ("Records mein hamari zameen hai lekin field mein kabza kisi aur ka hai.", False),
        ],
    },
    {
        "type": "Property Tax Overcharge",
        "fragments": [
            ("Property Tax Overcharge hai is saal ka bill, category galat lagayi gayi hai.", True),
            ("There is a Property Tax Overcharge, we were billed as commercial instead of residential.", True),
            ("Is saal ka tax bill residential ki jagah commercial rate se bana diya gaya hai.", False),
            ("This year's tax bill was calculated at the commercial rate instead of residential, nearly triple what we usually pay.", False),
            ("इस साल का टैक्स बिल रिहायशी की जगह व्यावसायिक दर से बना दिया गया है, लगभग तिगुना आ गया है।", False),
            ("Records update karwane ke liye kai baar office ja chuke hain, koi sunwai nahi.", False),
        ],
    },
])

add_dept("pollution", "Environment & Pollution", "State Pollution Control Board", [
    {
        "type": "Air Pollution from Factory",
        "fragments": [
            ("Air Pollution from nearby factory is affecting our health.", True),
            ("Air Pollution from Factory hai, bachchon ko khaansi rehti hai.", True),
            ("Factory se roz subah kaala dhuan nikalta hai, bachchon ko khaansi rehti hai humesha.", False),
            ("Thick black smoke pours out of the factory chimney every morning and our children have a constant cough now.", False),
            ("फैक्ट्री से रोज़ सुबह काला धुआं निकलता है, बच्चों को हमेशा खांसी रहती है।", False),
            ("Ghar ke andar tak dhuan aa jaata hai, khidki kholna mushkil ho gaya hai.", False),
        ],
    },
    {
        "type": "River/Lake Contamination",
        "fragments": [
            ("River/Lake Contamination hai, factory waste seedha nadi mein ja raha hai.", True),
            ("There is River/Lake Contamination, fish are dying near our village.", True),
            ("The small river behind our village has turned a strange color and fish are dying, we think a factory is dumping something.", False),
            ("Gaon ke peechhe wali nadi ka rang ajeeb ho gaya hai aur machliyan marne lagi hain.", False),
            ("गांव के पीछे वाली नदी का रंग अजीब हो गया है और मछलियां मरने लगी हैं, लगता है फैक्ट्री कुछ बहा रही है।", False),
            ("Nadi se ab paani lene se bhi log darte hain, badbu aane lagi hai.", False),
        ],
    },
    {
        "type": "Noise Pollution",
        "fragments": [
            ("Noise Pollution hai factory se, raat bhar awaaz aati hai.", True),
            ("There is Noise Pollution from the mill running all night.", True),
            ("Raat ko bahut tez awaaz aati hai factory se, neend nahi aata kisi ko.", False),
            ("The mill runs machinery all through the night and nobody in the neighborhood can sleep properly anymore.", False),
            ("रात को बहुत तेज़ आवाज़ आती है फैक्ट्री से, किसी को नींद नहीं आती।", False),
            ("Bachche padhai bhi nahi kar paate itni tez ghar-ghar ki awaaz mein.", False),
        ],
    },
    {
        "type": "Industrial Effluent Discharge",
        "fragments": [
            ("Industrial Effluent Discharge is going untreated into the drain.", True),
            ("Industrial Effluent Discharge hai, nala poora kala pad gaya hai.", True),
            ("Factory ka gandaa paani seedha nale mein chhod diya jaata hai, nala poora kala pad gaya hai.", False),
            ("The factory releases untreated waste directly into the drain and it has turned completely black and foul-smelling.", False),
            ("फैक्ट्री का गंदा पानी सीधे नाले में छोड़ दिया जाता है, नाला पूरा काला पड़ गया है।", False),
            ("Ganda paani khet tak pahunch gaya hai, fasal kharab hone ka darr hai.", False),
        ],
    },
    {
        "type": "Illegal Tree Cutting",
        "fragments": [
            ("Illegal Tree Cutting ho raha hai park mein raat ke andhere mein.", True),
            ("There is Illegal Tree Cutting, old trees are being cut without permission.", True),
            ("Kuch log raat ke andhere mein park ke purane ped kaat rahe hain bina kisi permission ke.", False),
            ("People have been cutting down old trees in the park at night without any permit.", False),
            ("कुछ लोग रात के अंधेरे में पार्क के पुराने पेड़ काट रहे हैं बिना किसी अनुमति के।", False),
            ("Subah uthkar dekha toh teen bade ped kate pade the.", False),
        ],
    },
    {
        "type": "Open Burning of Waste",
        "fragments": [
            ("Open Burning of Waste ho raha hai khaali plot mein har shaam.", True),
            ("There is Open Burning of Waste that fills our street with smoke every evening.", True),
            ("Har shaam khaali plot mein kachra jalaya jaata hai, poori gali dhuen se bhar jaati hai.", False),
            ("Someone burns garbage in the empty plot every evening and the whole street fills with thick smoke.", False),
            ("हर शाम खाली प्लॉट में कचरा जलाया जाता है, पूरी गली धुएं से भर जाती है।", False),
            ("Dhuen ki wajah se saans lena mushkil ho jaata hai shaam ko.", False),
        ],
    },
])

# ----------------------------------------------------------------------
# Sentence frames.
#
# A frame wraps a "core" situation/keyword phrase with an opener, a
# closer, and a location mention, varying clause order, register, and
# whether punctuation/greeting is present. SHARED_FRAMES apply to every
# department. DEPT_FRAMES add department-flavored frames on top (using
# institutional nouns specific to that department), so each department
# ends up with 15-20+ distinct frames as required by the brief.
#
# Each frame is a function (core, location) -> str.
# ----------------------------------------------------------------------

def f_plain(core, location):
    return f"{core}"


def f_location_lead_en(core, location):
    return f"In {location}, {core[0].lower()}{core[1:]}"


def f_location_lead_hi(core, location):
    return f"{location} mein, {core}"


def f_greeting_formal(core, location):
    return f"Respected Officer, {core[0].lower()}{core[1:]} This is in {location}, please look into it."


def f_namaste(core, location):
    return f"Namaste, {core} Yeh {location} ka mamla hai, kripya jald karyawahi karein."


def f_two_clause_recent(core, location):
    return f"This has been going on for a while in {location}. {core}"


def f_two_clause_recent_hi(core, location):
    return f"{location} mein kaafi samay se yeh chal raha hai. {core}"


def f_question_form(core, location):
    return f"{core} Kya koi is baare mein kuch karega, hum {location} mein bahut pareshan hain?"


def f_question_form_en(core, location):
    return f"{core} Will anyone actually look into this, we are in {location} and no one has responded?"


def f_emotional_appeal(core, location):
    return f"{core} Please help us, we don't know who else to ask in {location}."


def f_emotional_appeal_hi(core, location):
    return f"{core} Kripya madad kijiye, {location} mein humein aur kahin se koi madad nahi mil rahi."


def f_repeat_complaint(core, location):
    return f"Yeh mera doosra complaint hai iss baare mein, {location} area mein. {core}"


def f_formal_english(core, location):
    return f"I am writing to report the following issue in {location}. {core}"


def f_no_punct(core, location):
    text = f"{core} yeh {location} mein ho raha hai kripya dekhiye"
    return text.replace(".", "").replace(",", "")


def f_short_blunt(core, location):
    return f"{core}"


def f_third_person(core, location):
    return f"Residents of {location} are reporting the following. {core}"


def f_time_stamped(core, location):
    return f"Since last week in {location}: {core}"


def f_forwarded(core, location):
    return f"Forwarding a complaint received from a resident of {location}. {core}"


def f_pure_devanagari_formal(core, location):
    return f"आदरणीय अधिकारी महोदय, {location} में निम्नलिखित समस्या है। {core} कृपया शीघ्र समाधान करें।"


def f_pure_english_formal(core, location):
    return f"To the concerned authority, I would like to bring the following matter to your attention regarding {location}. {core} Kindly take necessary action."


def f_worried_family(core, location):
    return f"Meri family bahut pareshan hai is baat ko lekar {location} mein. {core}"


SHARED_FRAMES = [
    f_plain, f_location_lead_en, f_location_lead_hi, f_greeting_formal,
    f_namaste, f_two_clause_recent, f_two_clause_recent_hi,
    f_question_form, f_question_form_en, f_emotional_appeal,
    f_emotional_appeal_hi, f_repeat_complaint, f_formal_english,
    f_no_punct, f_short_blunt, f_third_person, f_time_stamped,
    f_forwarded, f_pure_devanagari_formal, f_pure_english_formal,
    f_worried_family,
]


def _dept_frame(prefix_en, prefix_hi):
    def frame(core, location):
        return f"{prefix_en} in {location}. {core}"

    def frame_hi(core, location):
        return f"{location} ke {prefix_hi} mein, {core}"

    return [frame, frame_hi]


DEPT_FRAMES = {
    "pwd": _dept_frame("A complaint to the PWD junior engineer's office", "PWD dafter"),
    "water": _dept_frame("A complaint to the Jal Board control room", "jal board office"),
    "electricity": _dept_frame("A complaint to the electricity substation office", "vidyut vibhag"),
    "sanitation": _dept_frame("A complaint to the ward sanitation inspector", "nagar nigam ward"),
    "health": _dept_frame("A complaint to the block medical officer regarding the PHC", "PHC"),
    "education": _dept_frame("A complaint to the block education officer regarding the school", "school"),
    "transport": _dept_frame("A complaint to the depot manager of the state transport corporation", "bus depot"),
    "police": _dept_frame("A complaint filed at the local police station", "thane"),
    "food": _dept_frame("A complaint to the food and civil supplies inspector", "ration dukaan"),
    "social": _dept_frame("A complaint to the social welfare office", "samaj kalyan karyalaya"),
    "revenue": _dept_frame("A complaint to the tehsildar's office", "tehsil office"),
    "pollution": _dept_frame("A complaint to the pollution control board regional office", "pradushan board karyalaya"),
}


def frames_for(dept_key):
    frames = list(SHARED_FRAMES) + DEPT_FRAMES[dept_key]
    return frames


# ----------------------------------------------------------------------
# Noise
# ----------------------------------------------------------------------

MISSPELL_MAP = {
    "problem": "problam", "complaint": "complain", "please": "pls",
    "government": "govt", "hospital": "hospitle", "immediately": "immediatly",
    "hai": "h", "nahi": "nhi", "kar": "kr", "raha": "rha", "hain": "hai",
    "bahut": "bhut", "area": "eria", "school": "skool", "water": "watar",
    "electricity": "electrisity", "kripya": "kripaya", "receive": "recieve",
    "occurred": "occured", "necessary": "nessesary", "definitely": "definately",
    "office": "offce", "regarding": "regarding", "sadak": "sadko",
    "residents": "residense", "authority": "authroity", "department": "departmnt",
    "corporation": "corparation", "issue": "isue", "children": "childern",
    "yesterday": "yestarday", "morning": "mornig", "tomorrow": "tommorow",
    "condition": "conditon", "responsible": "responsable", "situation": "sitution",
    "serious": "sirious", "police": "plice", "station": "staton",
    "medicine": "medecine", "attention": "attension", "request": "requst",
    "location": "lokation", "resolve": "resolv", "action": "actoin",
    "committee": "commitee", "officer": "offcer", "public": "publik",
    "quality": "qualaty", "quantity": "quantaty", "recieved": "recieved",
    "possible": "possable", "available": "availble", "already": "alredy",
    "several": "sevral", "because": "becoz", "though": "thou",
    "unfortunately": "unfortunatly", "genuine": "genuin",
}

FILLER_WORDS = [
    "basically", "you know", "I mean", "waise", "actually", "matlab",
    "jaise ki", "toh", "bhai", "sir", "madam ji", "please note that",
    "honestly", "seriously", "arre", "yaar", "for real", "sach mein",
    "ek baat batayein", "aur kya kahen", "kya karein", "bas itna hi",
    "in short", "overall", "kul milakar", "frankly speaking",
]


def apply_misspellings(text, rate=0.35):
    if random.random() > rate:
        return text
    words = text.split()
    for i, w in enumerate(words):
        bare = re.sub(r"[^\w]", "", w).lower()
        if bare in MISSPELL_MAP and random.random() < 0.6:
            repl = MISSPELL_MAP[bare]
            words[i] = w.replace(bare, repl) if bare in w else w
    return " ".join(words)


def drop_random_word(text, rate=0.15):
    if random.random() > rate:
        return text
    words = text.split()
    if len(words) > 6:
        idx = random.randrange(1, len(words) - 1)
        del words[idx]
    return " ".join(words)


def add_filler(text, rate=0.2):
    if random.random() > rate:
        return text
    filler = random.choice(FILLER_WORDS)
    words = text.split()
    if len(words) < 4:
        return text
    idx = random.randrange(1, len(words))
    words.insert(idx, filler + ",")
    return " ".join(words)


def strip_punctuation(text, rate=0.15):
    if random.random() > rate:
        return text
    return re.sub(r"[.,!?]", "", text)


def randomize_case(text, rate=0.25):
    r = random.random()
    if r < rate * 0.4:
        return text.lower()
    if r < rate * 0.6:
        return text.upper()
    if r < rate:
        # random capitalization noise on first letters of some words
        words = text.split()
        for i in range(len(words)):
            if random.random() < 0.15 and words[i]:
                words[i] = words[i][0].upper() + words[i][1:]
        return " ".join(words)
    return text


def random_typo(text, rate=0.18):
    """Swap two adjacent letters in one random ASCII word, mimicking a
    realistic fat-finger typo. Deliberately applied to whole words at
    random rather than a fixed dictionary, so it produces many distinct
    misspelled tokens instead of the same handful every time."""
    if random.random() > rate:
        return text
    words = text.split()
    candidates = [
        i for i, w in enumerate(words)
        if re.fullmatch(r"[A-Za-z]{5,}", w)
    ]
    if not candidates:
        return text
    idx = random.choice(candidates)
    w = words[idx]
    pos = random.randrange(1, len(w) - 1)
    chars = list(w)
    chars[pos], chars[pos + 1] = chars[pos + 1], chars[pos]
    words[idx] = "".join(chars)
    return " ".join(words)


def apply_noise(text):
    text = apply_misspellings(text)
    text = random_typo(text)
    text = add_filler(text)
    text = drop_random_word(text)
    text = strip_punctuation(text)
    text = randomize_case(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


# ----------------------------------------------------------------------
# Row generation
# ----------------------------------------------------------------------

def rand_phone():
    return f"9{random.randint(100000000, 999999999)}"


def build_row(complaint_id, dept_key, complaint_type_entry, sector, department):
    fragment, has_keyword = random.choice(complaint_type_entry["fragments"])
    location = rand_location()
    frame = random.choice(frames_for(dept_key))
    text = frame(fragment, location)
    text = maybe_inject_urgency_modifier(text)
    text = apply_noise(text)
    urgency = derive_urgency(text)
    return {
        "complaint_id": complaint_id,
        "sector": sector,
        "complaint_text": text,
        "location": location,
        "complaint_type": complaint_type_entry["type"],
        "phone_number": rand_phone(),
        "department": department,
        "urgency": urgency,
    }


def build_hard_negative_row(complaint_id, primary_key, secondary_key):
    primary = DEPARTMENTS[primary_key]
    secondary = DEPARTMENTS[secondary_key]
    p_type = random.choice(primary["complaint_types"])
    s_type = random.choice(secondary["complaint_types"])
    p_fragment, _ = random.choice(p_type["fragments"])
    s_fragment, _ = random.choice(s_type["fragments"])
    location = rand_location()

    connector = random.choice([
        "Waise humare area mein {s} bhi hai lekin abhi sabse zyada dikkat isi se hai.",
        "There is also an issue with {s_en} nearby, but this is the more serious one right now.",
        "Alag se yeh bhi bata dun ki {s} bhi ho raha hai, but pehle isko dekhiye.",
    ])
    if "{s_en}" in connector:
        closer = connector.format(s_en=s_fragment[0].lower() + s_fragment[1:])
    else:
        closer = connector.format(s=s_fragment)

    text = f"{p_fragment} {closer}"
    text = maybe_inject_urgency_modifier(text)
    text = apply_noise(text)
    urgency = derive_urgency(text)

    return {
        "complaint_id": complaint_id,
        "sector": primary["sector"],
        "complaint_text": text,
        "location": location,
        "complaint_type": p_type["type"],
        "phone_number": rand_phone(),
        "department": primary["department"],
        "urgency": urgency,
    }


def generate_dataset(n_rows=N_ROWS):
    rows = []
    dept_keys = list(DEPARTMENTS.keys())
    n_hard_negatives = int(n_rows * HARD_NEGATIVE_FRACTION)
    n_normal = n_rows - n_hard_negatives

    complaint_id = 1

    # Build a flat list of (dept_key, complaint_type_entry) pairs and
    # sample uniformly so every type gets roughly equal representation.
    all_types = []
    for dept_key, dept in DEPARTMENTS.items():
        for ct in dept["complaint_types"]:
            all_types.append((dept_key, ct))

    for _ in range(n_normal):
        dept_key, ct = random.choice(all_types)
        dept = DEPARTMENTS[dept_key]
        row = build_row(complaint_id, dept_key, ct, dept["sector"], dept["department"])
        rows.append(row)
        complaint_id += 1

    for _ in range(n_hard_negatives):
        primary_key, secondary_key = random.sample(dept_keys, 2)
        row = build_hard_negative_row(complaint_id, primary_key, secondary_key)
        rows.append(row)
        complaint_id += 1

    random.shuffle(rows)
    for i, row in enumerate(rows, start=1):
        row["complaint_id"] = i

    return rows


def vocab_report(rows):
    counter = Counter()
    for row in rows:
        tokens = re.findall(r"[A-Za-z0-9ऀ-ॿ']+", row["complaint_text"].lower())
        counter.update(tokens)
    print(f"Total unique tokens: {len(counter)}")
    print(f"Total tokens: {sum(counter.values())}")
    print("Most common 20:", counter.most_common(20))
    return len(counter)


def main():
    n_rows = N_ROWS
    if len(sys.argv) > 1:
        n_rows = int(sys.argv[1])

    print(f"Generating {n_rows} rows...")
    rows = generate_dataset(n_rows)

    fieldnames = [
        "complaint_id", "sector", "complaint_text", "location",
        "complaint_type", "phone_number", "department", "urgency",
    ]

    with open(OUTPUT_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

    print(f"Wrote {len(rows)} rows to {OUTPUT_PATH}")

    vocab_size = vocab_report(rows)
    if vocab_size < 1000:
        print("WARNING: vocabulary size is still low, generation is not diverse enough.")
    else:
        print(f"Vocabulary check passed: {vocab_size} unique tokens (target: several thousand).")

    urgency_counts = Counter(r["urgency"] for r in rows)
    print("Urgency distribution:", dict(urgency_counts))

    dept_counts = Counter(r["department"] for r in rows)
    print("Department distribution:", dict(dept_counts))

    unique_texts = len(set(r["complaint_text"] for r in rows))
    print(f"Unique complaint_text: {unique_texts} / {len(rows)}")


if __name__ == "__main__":
    main()
