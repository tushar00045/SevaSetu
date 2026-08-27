# SevaSetu grievance classifiers — evaluation

This is the honest result, not the flattering one. See `CLAUDE_CODE_BRIEF.md`
for the original diagnosis and `CALIBRATION_EXAMPLES.md` for the style of
examples this fix targets.

## What was wrong (recap)

`grievance_dataset.csv` / `sevasetu_grievance_dataset_100k_v1.csv` came from
~20 shared templates with a small slot vocabulary. Training logged a
vocabulary of 367 unique tokens across ~78k examples, and every complaint
about a pothole contained the literal word "Pothole", which maps 1:1 to PWD.
The model learned a lookup table, not language. Two symptoms from the brief:

- "There is maar pit in my area one person has shoot the other person he is
  dead on spot" → predicted State Pollution Control Board at 96% confidence.
  Correct answer: Police Department.
- A theft/FIR complaint → correctly predicted Police Department, but at only
  38% confidence, basically a guess.

## What changed

1. `generate_dataset.py` was rewritten. Each of the 12 departments gets
   15-20+ distinct sentence frames (opener/closer/clause-order/register,
   shared across departments plus a few department-specific ones), and each
   of the 72 complaint types has a hand-written bank of situation
   descriptions, most of which do not name the complaint type. Noise
   (misspellings, dropped words, missing punctuation, case variation, a
   random-adjacent-letter-swap typo), pure Devanagari Hindi, pure English,
   Hinglish, and a 3% slice of hard-negative rows that mention two
   departments' issues in one sentence (labeled by the primary issue) are
   all part of the generator. Urgency is derived by scanning the *final
   generated sentence* for danger/injury/emergency cues (`derive_urgency()`
   in `generate_dataset.py`), not looked up from sector.
2. `train_department_model.py` / `train_urgency_model.py` retrain the same
   Embedding + BiLSTM architecture (the brief's diagnosis was the data, not
   the architecture) on `sevasetu_grievance_dataset_v2.csv`.
3. `heldout_test_set.csv` (165 rows, built by `build_heldout_set.py`) is
   hand-written for this evaluation, not sampled from the generator's
   templates. `evaluate_heldout.py` scores both models against it.

## Vocabulary

| | v1 | v2 |
|---|---|---|
| Unique tokens (100k rows) | 367 | **5,452** |
| Unique complaint_text | not measured | 97,172 / 100,000 |
| Complaint types | 60 | 72 |
| Rows with keyword literal in text | ~100% | ~50% (by design) |

## In-distribution test split (from the training notebook/script) — NOT the real result

Both models hit very high accuracy on a test split drawn from the same
generation process as training: department 100.00%, urgency 99.74%. Per the
brief, this number is being reported precisely so it is *not* mistaken for
the final result. It mostly reflects that the generator, while far more
diverse than v1, still draws from a finite bank of hand-written situations
per department, and those situations use genuinely different vocabulary by
topic (roads vs. water vs. electricity), so within-distribution rows remain
close to linearly separable. That is expected and is exactly why the brief
asks for a held-out set that the generator never produced.

## Held-out evaluation (the real result)

`heldout_test_set.csv`, 165 hand-written rows: 128 "no keyword" complaints
across all 12 departments, 11 ambiguous/multi-issue complaints, 4 variations
on the murder/shooting failure case, 1 direct restatement of the brief's
theft example, 1 closure/thank-you message, and 20 adversarial/no-signal
inputs (nonsense, meta-feedback, off-topic questions).

### Department classifier

| Metric | Value |
|---|---|
| Accuracy (144 scored rows, excludes adversarial) | **79.17%** |
| Macro-F1 | **0.8077** |
| Accuracy on "no keyword" subset (128 rows) | 82.03% |
| Accuracy on ambiguous subset (10 rows) | 60.00% |

Confusion matrix (rows = actual, columns = predicted; label order below):

```
0 Department of Food & Civil Supplies      1 Department of Health & Family Welfare
2 Department of School Education           3 Department of Social Welfare
4 Municipal Corporation - Sanitation       5 Police Department
6 Public Works Department (PWD)            7 Revenue Department
8 State Electricity Board                  9 State Pollution Control Board
10 State Transport Corporation             11 Water Board

[[ 9  0  0  0  0  0  0  0  0  0  0  0]
 [ 0  9  0  1  0  1  0  0  0  0  0  0]
 [ 1  0  8  0  0  0  0  0  1  0  1  0]
 [ 0  0  0  9  0  0  0  0  0  0  0  0]
 [ 0  0  1  0 11  0  0  0  0  1  0  0]
 [ 3  0  2  0  2  8  2  0  0  0  0  0]
 [ 0  2  2  0  1  0 11  0  2  1  0  0]
 [ 0  0  0  0  0  0  0  9  0  0  0  0]
 [ 0  0  0  0  0  1  1  0 12  0  0  0]
 [ 0  0  0  0  1  0  0  0  0  8  0  0]
 [ 1  0  0  0  0  0  0  0  0  0  9  0]
 [ 0  0  1  0  1  0  0  0  0  0  0 11]]
```

**The brief's flagship examples, checked directly:**

| Complaint | Expected | Predicted | Confidence |
|---|---|---|---|
| "There is maar pit in my area one person has shoot the other person he is dead on spot" | Police Department | **Police Department** | **99.9999%** |
| "Maine ek hafte pehle complaint di thi chori ki lekin abhi tak FIR hi nahi likhi gayi." | Police Department | **Police Department** | **99.9997%** |

The exact murder/shooting sentence from the brief, previously misrouted to
State Pollution Control Board at 96% confidence, now routes correctly to
Police at essentially full confidence. The theft-delay complaint, previously
a 38%-confidence guess, is now a confident correct prediction. Two more
violent-crime variants were added; one more (a Devanagari sentence, and a
code-mixed one) is a genuine miss, both misrouted to School Education, see
below.

**Every wrong prediction (30 of 144 scored rows):**

| Complaint (truncated) | Expected | Predicted | Confidence | Category |
|---|---|---|---|---|
| A truck's front wheel got stuck in a crater on MG Road... | PWD | Health & Family Welfare | 0.577 | no_keyword |
| Kal shaam ek scooter waali gir gayi kyunki sadak ka ek hissa dhans gaya... | PWD | State Electricity Board | 0.820 | no_keyword |
| The pavement tiles outside the temple have come loose... | PWD | Sanitation | 0.835 | no_keyword |
| Poore gali mein andhera rehta hai raat ko kyunki khambhe ki roshni kharab... | PWD | State Electricity Board | 0.997 | no_keyword |
| Just wanted to note that the footpath repair from last month looks fine now... | PWD | Pollution Control Board | 0.513 | normal (closure) |
| Nali ka ganda paani ab humare peene ke paani ki tanki ke paas se guzarne... | Water Board | Sanitation | 0.999 | no_keyword |
| Someone keeps burning plastic waste in the empty plot... | Sanitation | Pollution Control Board | 1.000 | no_keyword |
| Bachchon ke khaane mein aaj phir keede mil gaye... | School Education | Food & Civil Supplies | 0.919 | no_keyword |
| Aaj subah bazaar mein jhagde ke dauran ek aadmi ko goli lag gayi... | Police | School Education | 0.481 | violent_crime_check |
| दो गुटों में मारपीट हो गई और एक व्यक्ति की चाकू लगने से मौके पर ही मौत हो गई। | Police | School Education | 0.805 | violent_crime_check |
| Kisi ne humari dukaan ka shutter tod kar poora cash counter khaali... | Police | Food & Civil Supplies | 0.483 | no_keyword |
| Sadak par khada karke kisi ne mera phone chheen liya aur bhaag gaya. | Police | Food & Civil Supplies | 0.952 | no_keyword |
| School ke paas ek bada gaddha hai sadak mein jisme kal ek bachcha gir gaya... | PWD | School Education | 0.982 | ambiguous |
| Hospital ke bahar wali sadak itni kharab hai ki ambulance tak nahi ghus paati... | PWD | Health & Family Welfare | 0.708 | ambiguous |
| Ration dukaan ke bahar hi kal jhagda ho gaya paise ko lekar... | Police | Food & Civil Supplies | 0.999 | ambiguous |
| Barish ke baad se sadak par gehra gaddha ban gaya hai... | PWD | School Education | 0.794 | no_keyword |
| Building ki tanki mein paani aata hi nahi hai kabhi kabhi poora hafta... | Water Board | School Education | 0.931 | no_keyword |
| Do din se bijli aa ja rahi hai baar baar... | Electricity Board | Police | 0.515 | no_keyword |
| Hamare block mein sirf humare ghar ki bijli baar baar trip ho jaati hai... | Electricity Board | PWD | 0.521 | no_keyword |
| Meri dadi ko admit karne ke liye bed hi khaali nahi mila do din tak. | Health & Family Welfare | Social Welfare | 0.996 | no_keyword |
| Lab report milne mein ek hafta lag gaya... | Health & Family Welfare | Police | 0.729 | no_keyword |
| Exam ka result der se aaya aur usme bhi kai bachchon ke marks galat print... | School Education | Electricity Board | 0.801 | no_keyword |
| Bachchon ko diya jaane wala uniform is saal abhi tak nahi mila... | School Education | Transport Corporation | 0.770 | no_keyword |
| The new ticket counter at the depot only opens for two hours a day... | Transport Corporation | Food & Civil Supplies | 0.308 | no_keyword |
| An unknown car has been parked outside our gate for three days... | Police | Sanitation | 0.984 | no_keyword |
| Do naujawan roz raat gali mein tez bike chalate hain... | Police | PWD | 0.710 | no_keyword |
| Humein anonymous calls aa rahe hain dhamki dete hue... | Police | PWD | 0.661 | no_keyword |
| Talab ka paani ab hara ho gaya hai... | Pollution Control Board | Sanitation | 0.930 | no_keyword |
| Humne suna hai ki humari gali mein koi nashe ka saman becha jaa raha hai... | Police | Sanitation | 0.991 | no_keyword |
| School ke bagal wale nale se itni badbu aati hai... | Sanitation | School Education | 0.617 | ambiguous |

Reading through these, the failure pattern is mostly sensible rather than
random: water/drain/smell complaints get pulled toward Sanitation, anything
mentioning a school pulls toward School Education even when the actual issue
is a road or a drain nearby, and Police complaints without an explicit
crime word (a suspicious car, anonymous threatening calls, a snatched phone)
scatter toward whichever department's vocabulary happens to overlap. This is
a real gap, but a qualitatively different one from v1's "keyword or nothing"
behavior. It is confidently wrong more often than it should be, which is the
next thing worth fixing (see Limitations below), but it is reading the
situation, not pattern-matching one inserted word.

### Confidence distribution (routing threshold = 0.6)

The backend routes anything below 0.6 confidence to human review instead of
auto-routing (`backend/src/routing.ts` in the SevaSetu app repo).

- Fraction of all 165 held-out predictions below 0.6 confidence: **15.76%**
  (26 / 165)
- Fraction of the 21 unscored rows below 0.6 confidence: **52.4%** (11 / 21)
  — 20 are genuine adversarial/no-signal rows, plus one deliberately
  unresolvable ambiguous row ("no water AND no electricity, both equally
  serious") that also has no single correct department.

The adversarial number is the one that matters most: on inputs with no real
department signal at all ("Testing testing 123", "asdkfj alskdjf laksjdf",
"Hello"), a bit over half correctly triggered a confidence low enough to
route to a human. The rest were confidently wrong, for example "12345 67890
test test" got routed to Health & Family Welfare at 98.9% confidence, and
"Mere chacha ka phone aya tha..." (an unrelated personal message) got routed
to Food & Civil Supplies at 97.5% confidence. The model has no explicit
"none of the above" class, so on nonsense it falls back to whatever
department's word statistics loosely match, sometimes with unwarranted
confidence. This is a real limitation, not hidden here.

### Urgency classifier

| Metric | Value |
|---|---|
| Accuracy (147 scored rows) | **51.02%** |
| Macro-F1 | **0.2687** |

```
              predicted:  high  low  medium
actual: high                3    0      36
actual: low                 0    0      35
actual: medium               1    0      72
```

This is a genuine failure, and it is worth being specific about why. Urgency
labels in the training data were derived by scanning generated text for an
explicit cue lexicon (`HIGH_URGENCY_CUES` / `LOW_URGENCY_CUES` in
`generate_dataset.py`), for example "khoon", "ghayal", "emergency",
"not urgent", "sirf feedback". That approach was correct in the sense that
it broke urgency's 100% correlation with sector (which was the v1 bug), and
the in-distribution test split confirms the model learned those cues well
(99.74% accuracy on data drawn from the same lexicon). But the model learned
to detect the specific cue *words*, not to infer real-world severity from
context. The hand-written held-out sentences describe danger and triviality
using different words than the training lexicon ("we can see straight down
to the river below" instead of "khatarnak", "a bit worried" instead of
"chhoti si baat"), and the model has almost no exposure to inferring
severity without a literal trigger word, so it collapses to predicting
"medium" for nearly everything. In effect, urgency labeling swapped one
narrow lookup table (sector → urgency) for a different narrow lookup table
(cue word → urgency) that generalizes about as poorly. Fixing this properly
needs either a much larger and fuzzier cue vocabulary covering indirect
danger/triviality language, or actual human-labeled urgency examples rather
than programmatic derivation, and is flagged here as follow-up work rather
than something this pass solved.

## What "done" looks like, honestly

- Department classifier: real improvement, not just a bigger number. The
  brief's two flagship failure cases are fixed with high confidence, the
  held-out accuracy (79%) is meaningfully below the in-distribution number
  (100%) which is expected and healthy, and most errors are semantically
  reasonable near-misses rather than random guesses.
- Urgency classifier: not fixed. The 100% sector-correlation bug from v1 is
  gone (verified: every department in the new training data produces all
  three urgency levels, see `generate_dataset.py`'s cross-tab in commit
  history), but the replacement labeling approach has its own generalization
  gap, caught here rather than hidden.
- Vocabulary: 367 → 5,452 unique tokens (100k rows), comfortably in the
  "several thousand" range the brief asked for.
- Confidence calibration on nonsense input: partial. About half of
  adversarial inputs correctly produce low confidence; the rest are
  confidently wrong, which is a specific, named gap rather than a vague one.

## Reproducing this evaluation

```
python3 generate_dataset.py 100000        # writes sevasetu_grievance_dataset_v2.csv
python3 train_department_model.py         # writes sevasetu_department_bilstm.keras, etc.
python3 train_urgency_model.py            # writes sevasetu_urgency_bilstm.keras, etc.
python3 build_heldout_set.py              # writes heldout_test_set.csv
python3 evaluate_heldout.py               # writes heldout_predictions.csv, prints all metrics above
```
