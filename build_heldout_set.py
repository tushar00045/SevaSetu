"""
Builds heldout_test_set.csv - a hand-written evaluation set for the
SevaSetu department and urgency classifiers.

Every sentence in HELDOUT is written by hand for this purpose, not sampled
from generate_dataset.py's templates/fragments. This is the actual test of
whether the model learned to read complaints instead of memorizing tokens
from the training generator - see CLAUDE_CODE_BRIEF.md.

Columns:
    complaint_text      - the complaint
    expected_department - ground truth department, or empty for the
                           adversarial/no-signal rows where there is no
                           correct department and the model is expected to
                           show LOW confidence rather than guess.
    expected_urgency     - low / medium / high, or empty where genuinely
                           ambiguous even to a human reader.
    category             - normal / no_keyword / ambiguous / adversarial /
                           violent_crime_check / theft_check
    notes                - why this row is in the set
"""

import csv

DEPARTMENTS = {
    "pwd": "Public Works Department (PWD)",
    "water": "Water Board",
    "electricity": "State Electricity Board",
    "sanitation": "Municipal Corporation - Sanitation",
    "health": "Department of Health & Family Welfare",
    "education": "Department of School Education",
    "transport": "State Transport Corporation",
    "police": "Police Department",
    "food": "Department of Food & Civil Supplies",
    "social": "Department of Social Welfare",
    "revenue": "Revenue Department",
    "pollution": "State Pollution Control Board",
}

# Each entry: (text, dept_key_or_None, urgency_or_None, category, notes)
HELDOUT = []


def add(text, dept, urgency, category, notes=""):
    dept_name = DEPARTMENTS[dept] if dept else ""
    HELDOUT.append((text, dept_name, urgency or "", category, notes))


# ------------------------------------------------------------------
# PWD - roads, footpaths, dividers, bridges, streetlights
# ------------------------------------------------------------------
add("A truck's front wheel got stuck in a crater on MG Road this morning and traffic was backed up for an hour.", "pwd", "medium", "no_keyword", "describes pothole without the word")
add("Kal shaam ek scooter waali gir gayi kyunki sadak ka ek hissa dhans gaya tha barish ke baad.", "pwd", "high", "no_keyword", "collapsed road surface, injury implied")
add("The pavement tiles outside the temple have come loose and shift under your feet when you walk on them.", "pwd", "medium", "no_keyword", "broken footpath, no keyword")
add("Humare mohalle ke chowk ka concrete block toot kar sadak ke beech mein pada hai, koi bhi takra sakta hai.", "pwd", "high", "no_keyword", "damaged divider, no keyword")
add("The steel railing on the old bridge is missing in one section, we can see straight down to the river below.", "pwd", "high", "no_keyword", "bridge safety hazard")
add("Sadak ke neeche se gattar ka dhakkan gayab hai kai hafte se, andhere mein koi bhi gir sakta hai.", "pwd", "high", "no_keyword", "missing manhole, no keyword")
add("Poore gali mein andhera rehta hai raat ko kyunki khambhe ki roshni kharab hai mahino se.", "pwd", "medium", "no_keyword", "streetlight, no keyword")
add("There's a construction pit left open near the school for over a month with no barricade around it.", "pwd", "high", "no_keyword", "unsafe roadwork")
add("Speed breaker itna unchaa bana diya hai bina paint kiye ki raat mein gaadiyan udd jaati hain usse.", "pwd", "medium", "no_keyword", "unmarked speed breaker")
add("The road near the market has sunk in the middle after the drain work, water collects there every time it rains.", "pwd", "low", "no_keyword", "minor sunken road, mild framing")
add("PWD ki sadak ban ke ek saal bhi nahi hua aur already ukhadne lag gayi hai jagah jagah se.", "pwd", "medium", "no_keyword", "poor road quality")
add("Just wanted to note that the footpath repair from last month looks fine now, thanks for fixing it.", "pwd", "low", "normal", "positive/closed feedback, still PWD topic")

# ------------------------------------------------------------------
# Water Board
# ------------------------------------------------------------------
add("Humare ghar mein pichle paanch din se nal bilkul sookha hai, bacchon ko nahalna tak mushkil ho gaya hai.", "water", "high", "no_keyword", "no water, no keyword, escalated by duration")
add("The water that comes out of our tap in the morning is muddy brown and has a bad smell.", "water", "high", "no_keyword", "contaminated water")
add("Building ki upper floors tak paani chadhta hi nahi, roz bucket lekar neeche jaana padta hai.", "water", "medium", "no_keyword", "low pressure, no keyword")
add("Ek pipe kaafi din se sadak ke bagal se behta rehta hai, saaf paani barbaad ho raha hai.", "water", "low", "no_keyword", "leakage, low severity framing")
add("We noticed someone has connected a hose directly into the main supply line without any authorization near the market.", "water", "medium", "no_keyword", "illegal connection")
add("Nali ka ganda paani ab humare peene ke paani ki tanki ke bilkul paas se guzarne laga hai, hum darr gaye hain.", "water", "high", "no_keyword", "sewage near drinking water tank")
add("Tanker mangwana padta hai har teesre din kyunki yahan supply hi band ho gayi hai permanently.", "water", "medium", "no_keyword", "chronic supply failure")
add("Bore well ka paani is baar khara lag raha hai, pehle aisa nahi tha.", "water", "medium", "no_keyword", "water quality change")
add("There has been no water in our tank for three days and my elderly mother can't carry water from the tanker herself.", "water", "high", "no_keyword", "vulnerable person affected")

# ------------------------------------------------------------------
# Electricity
# ------------------------------------------------------------------
add("Kal raat se poora gaon andhere mein hai, transformer mein kuch kharabi aa gayi lagti hai.", "electricity", "high", "no_keyword", "outage, no keyword")
add("Every evening around 7pm the lights flicker so badly that our new television already stopped working.", "electricity", "medium", "no_keyword", "voltage fluctuation")
add("Khambhe ke transformer se ajeeb awaaz aur halka dhuan nikal raha hai do din se.", "electricity", "high", "no_keyword", "transformer hazard")
add("A live wire is hanging about four feet above the ground right next to the bus stop, it sparked once when it rained yesterday.", "electricity", "high", "no_keyword", "exposed wire danger, echoes brief's calibration example")
add("Is mahine ka bijli bill pichle mahine se teen guna aa gaya hai bina kisi naye appliance ke.", "electricity", "medium", "no_keyword", "meter/billing error")
add("Bilkul halki barish mein bhi hamare gali ke khambhe se chingari nikalne lagti hai.", "electricity", "high", "no_keyword", "sparking pole")
add("Meter box ka dhakkan tuta hua hai aur andar ke taar khule dikh rahe hain.", "electricity", "high", "no_keyword", "exposed meter wiring")
add("It would be good if someone could check why our reading always seems higher than our neighbors' despite similar usage.", "electricity", "low", "no_keyword", "mild billing query")

# ------------------------------------------------------------------
# Sanitation
# ------------------------------------------------------------------
add("Humari gali ke corner par kachre ka pahad ban gaya hai, kutte aur suar wahan ghoomte rehte hain.", "sanitation", "medium", "no_keyword", "garbage pileup, no keyword")
add("The drain right outside our gate has been clogged for two weeks and black water now pools right at our doorstep.", "sanitation", "high", "no_keyword", "blocked drain, health risk")
add("Community bin se kachra chalak kar sadak par pheli gaya hai, safai karmi kai hafte se nahi aaye.", "sanitation", "medium", "no_keyword", "overflowing bin")
add("Someone keeps burning plastic waste in the empty plot behind our house every evening and the smoke makes it hard to breathe.", "sanitation", "medium", "no_keyword", "open waste burning")
add("Station ke paas wale toilet mein itni gandagi hai ki andar jaana bhi mushkil ho gaya hai.", "sanitation", "low", "no_keyword", "unclean public toilet, mild")
add("Machhar itne badh gaye hain kachre ki wajah se ki bachchon ko dengue hone ka darr hai.", "sanitation", "high", "no_keyword", "disease risk from garbage")
add("Nagar nigam ki gaadi humari gali chhod deti hai roz, agal bagal ki galiyon mein aati hai.", "sanitation", "medium", "no_keyword", "selective garbage collection")

# ------------------------------------------------------------------
# Health
# ------------------------------------------------------------------
add("Hum subah saat baje se line mein khade the lekin dopahar tak koi doctor check karne nahi aaya.", "health", "medium", "no_keyword", "doctor absence, no keyword")
add("The pharmacy at the government hospital has been out of basic paracetamol and ORS for over a week now.", "health", "medium", "no_keyword", "medicine shortage")
add("Meri maa ko seene mein dard hua tha, humne ambulance bulayi lekin ek ghante tak nahi pahunchi.", "health", "high", "no_keyword", "ambulance delay + chest pain")
add("Nurse ne free test ke liye bhi paisa maang liya jabki scheme mein yeh free hona chahiye.", "health", "low", "no_keyword", "overcharging, moderate/low framing")
add("Ward mein bedsheet kai dino se nahi badli gayi hai aur cockroach bhi dikhte hain.", "health", "medium", "no_keyword", "unhygienic ward")
add("There is no woman doctor posted at our health center, my sister had to travel to the next town just for a routine checkup.", "health", "medium", "no_keyword", "no female doctor")
add("Mere pitaji behosh ho gaye achanak ghar par, unhe turant hospital le jaana pada.", "health", "high", "no_keyword", "medical emergency, unconscious")

# ------------------------------------------------------------------
# Education
# ------------------------------------------------------------------
add("Is mahine sirf paanch din school khula, baaki din koi teacher nahi aaya padhane.", "education", "medium", "no_keyword", "teacher absenteeism")
add("The classroom ceiling has been leaking for two months and the children now sit in the corridor whenever it rains.", "education", "medium", "no_keyword", "building damage")
add("Humari beti ko school mein toilet na hone ki wajah se poora din pyaas bhi rok ke rehna padta hai.", "education", "low", "no_keyword", "lack of toilets, mild framing")
add("Bachchon ke khaane mein aaj phir keede mil gaye, yeh teesri baar hua hai iss mahine.", "education", "medium", "no_keyword", "midday meal quality, repeated")
add("The school suddenly increased the annual fee by fifteen percent without sending any notice to parents.", "education", "low", "no_keyword", "fee overcharging")
add("Ek hi classroom mein 90 bachche baithte hain, bench par thik se baithne ki jagah tak nahi hai.", "education", "medium", "no_keyword", "overcrowding")
add("Meri beti ko roz teacher dwara daanta jaata hai chhoti chhoti baaton par, wo ab school jaane se darti hai.", "education", "medium", "ambiguous", "could read as school issue or a safety/welfare concern; primary is school conduct")

# ------------------------------------------------------------------
# Transport
# ------------------------------------------------------------------
add("Subah office ke liye humein ek ghante se zyada khada rehna padta hai kyunki is route par bus hi nahi aati.", "transport", "medium", "no_keyword", "bus not arriving")
add("Overnight the state transport corporation stopped the only bus connecting our village to the railway station.", "transport", "medium", "no_keyword", "route cancelled")
add("Conductor ne ek budhi mahila ko ticket ke paise ko lekar sabke saamne bahut bura bhala kaha.", "transport", "low", "no_keyword", "conductor behavior")
add("Bus stop ka shed toofan mein gir gaya, ab log dhoop aur barish mein khule mein khade rehte hain.", "transport", "medium", "no_keyword", "damaged shelter")
add("Auto driver station ke bahar meter lagane se seedha mana kar deta hai aur dugna paisa maangta hai.", "transport", "low", "no_keyword", "overcharging")
add("The driver saw us waving at the stop and just drove past without even slowing down.", "transport", "low", "no_keyword", "skipped stop")

# ------------------------------------------------------------------
# Police
# ------------------------------------------------------------------
add("Kal raat koi ghar ka taala tod kar gehne aur cash le gaya, hum sab bahut dare hue hain.", "police", "high", "no_keyword", "theft, no keyword")
add("Maine ek hafte pehle complaint di thi chori ki lekin abhi tak FIR hi nahi likhi gayi.", "police", "medium", "theft_check", "theft report delay, spirit of the brief's theft example")
add("A group of men has been following girls near the college gate every evening and nobody feels safe walking alone now.", "police", "high", "no_keyword", "harassment")
add("Padosi ke ghar se roz raat chillane aur maarne ki awaazein aati hain, dar lagta hai kuch bada ho jaayega.", "police", "high", "no_keyword", "suspected domestic violence")
add("There is maar pit in my area one person has shoot the other person he is dead on spot", "police", "high", "violent_crime_check", "exact sentence from CLAUDE_CODE_BRIEF.md that the old model misrouted to Pollution Control Board at 96% confidence")
add("Aaj subah bazaar mein jhagde ke dauran ek aadmi ko goli lag gayi, khoon bahut beh raha tha, log bhaag gaye.", "police", "high", "violent_crime_check", "murder/shooting variant, code-mixed")
add("Someone pulled a knife during a fight outside the liquor shop last night and one man was badly hurt.", "police", "high", "violent_crime_check", "assault with weapon")
add("दो गुटों में मारपीट हो गई और एक व्यक्ति की चाकू लगने से मौके पर ही मौत हो गई।", "police", "high", "violent_crime_check", "pure Devanagari murder scenario")
add("Kisi ne humari dukaan ka shutter tod kar poora cash counter khaali kar diya raat mein.", "police", "high", "no_keyword", "burglary")
add("Sadak par khada karke kisi ne mera phone chheen liya aur bhaag gaya.", "police", "medium", "no_keyword", "snatching")

# ------------------------------------------------------------------
# Food & Civil Supplies
# ------------------------------------------------------------------
add("Is mahine dukaan hi nahi khuli, humein anaj bilkul nahi mil paaya.", "food", "medium", "no_keyword", "shop closed")
add("We paid for five kilos of rice this month but the dealer only weighed out three kilos in front of us.", "food", "medium", "no_keyword", "short quantity")
add("Sarkari dukaan se mila gehun is baar patthar aur keeda dono se bhara hua tha.", "food", "medium", "no_keyword", "adulterated ration")
add("It has been six months since we applied for a ration card and every visit to the office ends with 'come back next week'.", "food", "medium", "no_keyword", "card not issued")
add("Card mein meri beti ka naam hi darj nahi hai, do baar correction form bhar chuke hain.", "food", "low", "no_keyword", "correction pending")
add("Dukaandaar bina bill diye fixed rate se zyada paisa le leta hai har baar.", "food", "medium", "no_keyword", "dealer overcharging")

# ------------------------------------------------------------------
# Social Welfare
# ------------------------------------------------------------------
add("Dadi ka pension iss mahine khaate mein nahi aaya, unki zaroori dawai ruk gayi hai isi wajah se.", "social", "high", "no_keyword", "pension not credited, medicine dependency raises stakes")
add("The old age pension application was rejected without giving any reason and we don't know what to fix.", "social", "medium", "no_keyword", "pension rejected")
add("Meri maa ka vidhwa pension form jama kiye chhah mahine ho gaye, koi update nahi mil raha.", "social", "medium", "no_keyword", "widow pension pending")
add("My father's disability certificate has been stuck in process for four months and he needs it for a job application.", "social", "medium", "no_keyword", "certificate delay")
add("College fees jama karni hai lekin beti ki scholarship abhi tak account mein nahi aayi.", "social", "medium", "no_keyword", "scholarship not disbursed")
add("Humara welfare scheme ka form portal par verification stage par hi atka hua hai kai mahino se.", "social", "low", "no_keyword", "application stuck")

# ------------------------------------------------------------------
# Revenue
# ------------------------------------------------------------------
add("Zameen ke kaagzaat mein mere pita ka naam galat likha hai jiski wajah se bank loan atka hua hai.", "revenue", "medium", "no_keyword", "record mismatch")
add("We have been trying to register our property for six months and every visit ends with 'come back next week'.", "revenue", "medium", "no_keyword", "registry delay")
add("Padosi ne humari zameen ke ek hisse mein pakki deewar bana di hai bina kisi adhikar ke.", "revenue", "medium", "no_keyword", "boundary dispute")
add("Property khareede kai mahine ho gaye lekin records mein abhi bhi purane malik ka naam chal raha hai.", "revenue", "low", "no_keyword", "mutation delay")
add("This year's property tax bill was calculated as commercial instead of residential, almost triple what we usually pay.", "revenue", "medium", "no_keyword", "tax overcharge")
add("Padosi kisan dheere dheere apni fasal ki line badhakar humari zameen mein ghus raha hai.", "revenue", "low", "no_keyword", "land encroachment, slow-moving")

# ------------------------------------------------------------------
# Pollution
# ------------------------------------------------------------------
add("Factory ki chimney se roz subah kaala dhuan nikalta hai aur bachchon ko lagatar khaansi rehti hai.", "pollution", "medium", "no_keyword", "air pollution")
add("The small river behind our village has turned a strange grey color and dead fish have started washing up on the bank.", "pollution", "high", "no_keyword", "water contamination")
add("Raat bhar mill se itni tez awaaz aati hai ki poore mohalle ko neend nahi aati.", "pollution", "low", "no_keyword", "noise pollution")
add("Factory ka bina treat kiya hua paani seedha nale mein chhoda jaa raha hai, nala poora kala pad gaya hai.", "pollution", "medium", "no_keyword", "effluent discharge")
add("Kuch log raat ke andhere mein park ke purane ped kaat rahe hain bina kisi permission ke.", "pollution", "low", "no_keyword", "illegal tree cutting")
add("Har shaam khaali plot mein kachra jalaya jaata hai aur poori gali dhuen se bhar jaati hai.", "pollution", "medium", "ambiguous", "could plausibly route to sanitation (waste) or pollution (burning/air); primary complaint is the smoke")

# ------------------------------------------------------------------
# Genuinely ambiguous / multi-issue - test priority reasoning
# ------------------------------------------------------------------
add("Humare area mein bahut dino se pothole bhi hai aur streetlight bhi kharab hai, lekin abhi sabse zyada dikkat andhere ki wajah se ho rahi hai raat mein chalne mein.", "pwd", "medium", "ambiguous", "two PWD sub-issues, same department either way")
add("School ke paas ek bada gaddha hai sadak mein jisme kal ek bachcha gir gaya, school walo ne bhi complain kiya hai lekin yeh sadak ka masla hai.", "pwd", "high", "ambiguous", "school mentioned but primary issue is the road hazard, not school administration")
add("Hospital ke bahar wali sadak itni kharab hai ki ambulance tak nahi ghus paati emergency mein.", "pwd", "high", "ambiguous", "road problem blocking health access; primary is the road")
add("Humare ghar mein na paani aa raha hai na bijli, do din se dono band hain ek saath.", None, "high", "ambiguous", "genuinely two departments (water + electricity) with equal weight, no single correct primary")
add("Ration dukaan ke bahar hi kal jhagda ho gaya paise ko lekar, dukaandaar ne dhamki bhi di hai.", "police", "medium", "ambiguous", "starts as a ration issue but the reportable event is now a threat/altercation")
add("Nagar nigam ki safai gadi hi sadak par khadi rehti hai poora din, aane jaane walon ko gaadi nikalna mushkil hota hai.", "sanitation", "low", "ambiguous", "sanitation vehicle causing an obstruction, could read as PWD/traffic too")

# ------------------------------------------------------------------
# Adversarial / no department signal at all - model should show LOW
# confidence rather than a confident wrong guess.
# ------------------------------------------------------------------
add("Mujhe samajh nahi aa raha kis department mein complaint karu, koi guide kar sakta hai?", None, None, "adversarial", "asking for routing help, no actual complaint content")
add("This is a general feedback about the portal, not a specific complaint.", None, None, "adversarial", "meta feedback about the app itself")
add("Thank you for resolving my last complaint quickly.", None, "low", "adversarial", "closure/thanks message, no active issue")
add("Testing testing 123", None, None, "adversarial", "test input")
add("asdkfj alskdjf laksjdf", None, None, "adversarial", "keyboard mash, nonsense")
add("Humare gaon mein bahut saari samasyaen hain overall.", None, None, "adversarial", "vague, no specific department signal")
add("Can you tell me the office hours for government departments?", None, None, "adversarial", "informational query, not a grievance")
add("Hello", None, None, "adversarial", "empty greeting")
add("I just wanted to say the new portal design looks nice.", None, "low", "adversarial", "unrelated compliment")
add("Kya is portal se main apna aadhaar card bhi update kar sakta hoon?", None, None, "adversarial", "unrelated question about Aadhaar, out of scope")
add("Life is full of struggles and we must keep moving forward no matter what happens.", None, None, "adversarial", "generic philosophical text, no complaint")
add("12345 67890 test test", None, None, "adversarial", "numeric noise")
add("मुझे नहीं पता क्या लिखूं यहां।", None, None, "adversarial", "pure Hindi, 'I don't know what to write here'")
add("Please call me back at your convenience regarding some matter we discussed earlier.", None, None, "adversarial", "vague callback request, no content")
add("...", None, None, "adversarial", "empty-ish input")

# ------------------------------------------------------------------
# Additional rows per department to reach the brief's 150-200 minimum,
# still hand-written, still mostly without the literal keyword.
# ------------------------------------------------------------------
add("Barish ke baad se sadak par gehra gaddha ban gaya hai, do baar auto uska tyre usme phasa chuka hai.", "pwd", "medium", "no_keyword", "pothole, extra variant")
add("The zebra crossing paint has completely faded near the school and cars don't slow down at all now.", "pwd", "medium", "no_keyword", "road safety marking")
add("Naala cross karne wala chhota pul kaafi jhukk gaya hai ek taraf se, dar lagta hai cycle lekar jaate waqt.", "pwd", "medium", "no_keyword", "sagging footbridge")
add("Hamare gali ka last khambha kai mahino se bujha hua hai, sirf woh ek jagah andheri rehti hai.", "pwd", "low", "no_keyword", "single streetlight out, minor")

add("Building ki tanki mein paani aata hi nahi hai kabhi kabhi poora hafta, motor bhi kharab lag rahi hai.", "water", "medium", "no_keyword", "intermittent supply")
add("Kal se nal se kaala paani aa raha hai, hum darr ke maare peene ke liye nahi le rahe.", "water", "high", "no_keyword", "contaminated black water")
add("The overhead tank near our society has a crack and water keeps leaking down the outer wall.", "water", "low", "no_keyword", "tank leakage, minor")
add("Naye connection ke baad se hamare purane connection mein pressure bilkul kam ho gaya hai.", "water", "medium", "no_keyword", "impact of new illegal connection")

add("Do din se bijli aa ja rahi hai baar baar, ek minute ke liye aati hai fir chali jaati hai.", "electricity", "medium", "no_keyword", "intermittent power")
add("The wooden electric pole near the bus stand looks like it's about to fall, it's leaning quite a bit now.", "electricity", "high", "no_keyword", "leaning pole hazard")
add("Naya meter lagne ke baad se bill pehle se kaafi zyada aa raha hai har mahine.", "electricity", "low", "no_keyword", "billing concern after meter change")
add("Hamare block mein sirf humare ghar ki bijli baar baar trip ho jaati hai, baaki sab thik hai.", "electricity", "low", "no_keyword", "isolated fault, low severity")

add("Kachra gaadi is hafte ek baar bhi nahi aayi, ab poori gali mein dher lag gaya hai.", "sanitation", "medium", "no_keyword", "missed collection")
add("The public urinal wall near the market has been broken for months and it's an unpleasant sight for everyone passing.", "sanitation", "low", "no_keyword", "damaged public facility")
add("Naali ka dhakkan gayab hai humari gali mein, badbu bhi bahut aati hai wahan se.", "sanitation", "medium", "no_keyword", "open drain smell")
add("Stray cattle have started gathering near the garbage dump and blocking half the street every afternoon.", "sanitation", "low", "no_keyword", "garbage attracting animals")

add("PHC mein aaj bhi sirf ek hi staff tha, baaki sab chutti par the achanak.", "health", "medium", "no_keyword", "understaffed PHC")
add("The vaccination camp that was supposed to happen this week at our anganwadi never took place.", "health", "medium", "no_keyword", "missed health camp")
add("Meri dadi ko admit karne ke liye bed hi khaali nahi mila do din tak.", "health", "high", "no_keyword", "no bed availability")
add("Lab report milne mein ek hafta lag gaya jabki bola gaya tha teen din mein milega.", "health", "low", "no_keyword", "delayed lab report")

add("Aaj bhi teacher sirf do ghante padha kar chale gaye, baaki period khaali hi rahe.", "education", "medium", "no_keyword", "reduced teaching hours")
add("The library room at our school has been locked for the entire term, nobody has the key apparently.", "education", "low", "no_keyword", "inaccessible facility")
add("Exam ka result der se aaya aur usme bhi kai bachchon ke marks galat print hue hain.", "education", "medium", "no_keyword", "result errors")
add("Bachchon ko diya jaane wala uniform is saal abhi tak nahi mila, session aadha nikal gaya.", "education", "low", "no_keyword", "delayed uniform distribution")

add("Last bus roz humara stop chhod kar seedha aage nikal jaati hai bina rukey.", "transport", "medium", "no_keyword", "bus skipping stop, extra variant")
add("The new ticket counter at the depot only opens for two hours a day, causing long queues every morning.", "transport", "low", "no_keyword", "limited counter hours")
add("Bus ke andar seat ka foam bahar nikla hua hai aur AC bhi kaam nahi karta gर्मi mein.", "transport", "low", "no_keyword", "poor bus condition")
add("Driver ne rasta beech mein hi badal diya bina announcement kiye, sab passenger confuse ho gaye.", "transport", "low", "no_keyword", "route change without notice")

add("Kal raat kisi ne humari bike ka lock tod diya parking mein, subah dekha to bike gayab thi.", "police", "high", "no_keyword", "vehicle theft")
add("An unknown car has been parked outside our gate for three days and nobody has come to claim it, we're a bit worried.", "police", "low", "no_keyword", "suspicious vehicle, mild")
add("Do naujawan roz raat gali mein tez bike chalate hain aur log dar jaate hain unse.", "police", "medium", "no_keyword", "reckless driving/nuisance")
add("Humein anonymous calls aa rahe hain dhamki dete hue pichle do hafte se.", "police", "high", "no_keyword", "threatening calls")

add("Is baar mila anaj bahut purana lag raha tha, khushboo bhi ajeeb thi.", "food", "medium", "no_keyword", "stale grain")
add("The shop owner told us to come back next week for our quota, this is the third time he's said that.", "food", "medium", "no_keyword", "repeated denial of quota")
add("Kerosene ka kota is mahine humein diya hi nahi gaya bina koi karan bataye.", "food", "medium", "no_keyword", "kerosene quota denied")

add("Meri saas ka disability pension form six mahine se pending hai bina kisi update ke.", "social", "medium", "no_keyword", "pension pending, extra variant")
add("The scholarship portal keeps rejecting my daughter's documents citing a technical error we can't fix ourselves.", "social", "low", "no_keyword", "portal technical issue")
add("Widow certificate ke liye jo documents maange gaye the wo sab jama kar diye lekin abhi bhi koi jawab nahi.", "social", "medium", "no_keyword", "certificate delay")

add("Naye survey mein humari zameen ka rakba galat likh diya gaya hai, pichle se kaafi kam dikha raha hai.", "revenue", "medium", "no_keyword", "survey error")
add("We submitted every document for the mutation three months ago and the file seems to have disappeared at the tehsil office.", "revenue", "medium", "no_keyword", "lost file")
add("Padosi ne apna naya ghar banate waqt humari boundary wall ka ek hissa tod diya.", "revenue", "medium", "no_keyword", "property boundary damage")

add("Factory ke paas rehna mushkil ho gaya hai, saans lete waqt gale mein jalan hoti hai roz.", "pollution", "medium", "no_keyword", "air quality health impact")
add("The construction site next door runs a generator all night that fills the whole lane with diesel fumes.", "pollution", "low", "no_keyword", "generator fumes")
add("Talab ka paani ab hara ho gaya hai aur usme se ajeeb badbu aane lagi hai pichle hafte se.", "pollution", "medium", "no_keyword", "pond contamination")

add("Meri beti college se ghar aate waqt roz kuch ladko dwara tang ki jaati hai bus stop ke paas.", "police", "high", "no_keyword", "harassment, extra variant")
add("Humne suna hai ki humari gali mein koi nashe ka saman becha jaa raha hai raat ko.", "police", "medium", "no_keyword", "suspected drug activity")

add("Mere chacha ka phone aya tha ki unke office mein aaj bahut kaam hai.", None, None, "adversarial", "unrelated personal message")
add("What is the weather like today in Delhi?", None, None, "adversarial", "unrelated question")
add("यह सिर्फ एक टेस्ट मैसेज है, कृपया इसे नज़रअंदाज़ करें।", None, None, "adversarial", "explicit test message in Devanagari")
add("Congratulations on completing 75 years of independence.", None, None, "adversarial", "unrelated greeting text")
add("Kripya mera application number bata dijiye, maine kal apply kiya tha kisi scheme ke liye.", None, None, "adversarial", "vague status request, no department named or inferable")

add("Ek taraf humare mohalle mein bijli nahi hai teen din se, dusri taraf sadak bhi tooti padi hai kaafi samay se, lekin abhi sabse zyada takleef andhere ki wajah se hai.", "electricity", "high", "ambiguous", "electricity + PWD both mentioned, primary stated explicitly")
add("School ke bagal wale nale se itni badbu aati hai ki bachche class mein baithne se bhi katrate hain.", "sanitation", "medium", "ambiguous", "affects school but root cause is a sanitation drain")
add("Ration dukaan ke upar ka bijli ka meter bahut purana ho gaya hai aur sparking bhi karta hai kabhi kabhi.", "electricity", "high", "ambiguous", "ration shop context but hazard is electrical")


def main():
    fieldnames = [
        "complaint_text", "expected_department", "expected_urgency",
        "category", "notes",
    ]
    with open("heldout_test_set.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(fieldnames)
        for row in HELDOUT:
            writer.writerow(row)
    print(f"Wrote {len(HELDOUT)} hand-written held-out rows to heldout_test_set.csv")

    by_cat = {}
    for row in HELDOUT:
        by_cat[row[3]] = by_cat.get(row[3], 0) + 1
    print("By category:", by_cat)


if __name__ == "__main__":
    main()
