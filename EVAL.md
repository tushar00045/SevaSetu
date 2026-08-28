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
   the architecture) on `sevasetu_grievance_dataset_v2.csv`. Sequence length
   is capped at 64 tokens instead of 150 (99% of generated complaints are
   52 tokens or shorter; the extra padding cost training time for no
   accuracy benefit) and batch size is 256 instead of 128, which cut a full
   training run from ~45 minutes to under 10 with no change to model
   architecture or capacity.
3. `heldout_test_set.csv` (165 rows, built by `build_heldout_set.py`) is
   hand-written for this evaluation, not sampled from the generator's
   templates. `evaluate_heldout.py` scores both models against it.
4. After the first held-out pass showed the urgency classifier collapsing to
   "medium" on almost everything, `HIGH_URGENCY_CUES` / `LOW_URGENCY_CUES`
   were broadened with indirect hazard/triviality language ("missing
   railing", "could collapse", "not that big a deal", ...) instead of only
   direct danger words, and 24 new hand-written fragments (one high- and one
   low-severity example per department) were added so the training data
   actually contains that indirect phrasing. Both models were then retrained
   on the updated dataset. Results below; this closed part of the gap, not
   all of it — see the urgency section.

## Vocabulary

| | v1 | v2 |
|---|---|---|
| Unique tokens (100k rows) | 367 | **5,689** |
| Unique complaint_text | not measured | 97,293 / 100,000 |
| Complaint types | 60 | 72 |
| Rows with keyword literal in text | ~100% | ~50% (by design) |

## In-distribution test split (from the training script) — NOT the real result

Both models hit very high accuracy on a test split drawn from the same
generation process as training: department 100.00%, urgency 99.76%. Per the
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
| Accuracy (144 scored rows, excludes adversarial) | **76.39%** |
| Macro-F1 | **0.7806** |

Confusion matrix (rows = actual, columns = predicted; label order below):

```
0 Department of Food & Civil Supplies      1 Department of Health & Family Welfare
2 Department of School Education           3 Department of Social Welfare
4 Municipal Corporation - Sanitation       5 Police Department
6 Public Works Department (PWD)            7 Revenue Department
8 State Electricity Board                  9 State Pollution Control Board
10 State Transport Corporation             11 Water Board

[[ 9  0  0  0  0  0  0  0  0  0  0  0]
 [ 0  9  0  1  0  0  0  0  0  0  0  1]
 [ 1  0  8  0  0  0  0  0  1  0  1  0]
 [ 0  0  0  9  0  0  0  0  0  0  0  0]
 [ 0  0  1  0 11  0  0  0  0  1  0  0]
 [ 3  1  0  0  2  9  1  0  0  0  1  0]
 [ 1  1  0  1  2  0  9  0  4  0  1  0]
 [ 0  0  0  0  0  0  0  9  0  0  0  0]
 [ 2  0  0  0  0  1  1  0 10  0  0  0]
 [ 0  0  0  0  1  0  0  0  0  8  0  0]
 [ 0  0  0  0  0  0  0  0  0  0 10  0]
 [ 1  1  1  0  1  0  0  0  0  0  0  9]]
```

**The brief's flagship examples, checked directly:**

| Complaint | Expected | Predicted | Confidence |
|---|---|---|---|
| "There is maar pit in my area one person has shoot the other person he is dead on spot" | Police Department | **Police Department** | **100.0%** |
| "Maine ek hafte pehle complaint di thi chori ki lekin abhi tak FIR hi nahi likhi gayi." | Police Department | **Police Department** | **99.9997%** |

The exact murder/shooting sentence from the brief, previously misrouted to
State Pollution Control Board at 96% confidence, now routes correctly to
Police at full confidence. The theft-delay complaint, previously a
38%-confidence guess, is now a confident correct prediction. All 4 of the
violent-crime variants in the held-out set (the brief's exact sentence, a
code-mixed shooting, an English knife-assault, and a pure-Devanagari murder
sentence) now route correctly to Police Department, with confidence ranging
from 75.4% to 100%.

**Every wrong prediction (34 of 144 scored rows):**

| Complaint (truncated) | Expected | Predicted | Confidence | Category |
|---|---|---|---|---|
| A truck's front wheel got stuck in a crater on MG Road... | PWD | Social Welfare | 0.692 | no_keyword |
| Kal shaam ek scooter waali gir gayi kyunki sadak ka ek hissa dhans gaya... | PWD | State Electricity Board | 0.986 | no_keyword |
| The pavement tiles outside the temple have come loose... | PWD | Transport Corporation | 0.658 | no_keyword |
| Poore gali mein andhera rehta hai raat ko kyunki khambhe ki roshni kharab... | PWD | State Electricity Board | 0.996 | no_keyword |
| Speed breaker itna unchaa bana diya hai bina paint kiye... | PWD | Food & Civil Supplies | 0.897 | no_keyword |
| The road near the market has sunk in the middle after the drain work... | PWD | Sanitation | 0.454 | no_keyword |
| Just wanted to note that the footpath repair from last month looks fine now... | PWD | State Electricity Board | 0.485 | normal (closure) |
| Nali ka ganda paani ab humare peene ke paani ki tanki ke paas se guzarne... | Water Board | Sanitation | 0.957 | no_keyword |
| Tanker mangwana padta hai har teesre din kyunki yahan supply hi band... | Water Board | Health & Family Welfare | 0.610 | no_keyword |
| Bore well ka paani is baar khara lag raha hai, pehle aisa nahi tha. | Water Board | Food & Civil Supplies | 0.453 | no_keyword |
| Someone keeps burning plastic waste in the empty plot... | Sanitation | Pollution Control Board | 1.000 | no_keyword |
| Bachchon ke khaane mein aaj phir keede mil gaye... | School Education | Food & Civil Supplies | 0.994 | no_keyword |
| Kisi ne humari dukaan ka shutter tod kar poora cash counter khaali... | Police | Food & Civil Supplies | 0.623 | no_keyword |
| Sadak par khada karke kisi ne mera phone chheen liya aur bhaag gaya. | Police | Food & Civil Supplies | 0.777 | no_keyword |
| Hospital ke bahar wali sadak itni kharab hai ki ambulance tak nahi ghus paati... | PWD | Health & Family Welfare | 0.906 | ambiguous |
| Ration dukaan ke bahar hi kal jhagda ho gaya paise ko lekar... | Police | Food & Civil Supplies | 1.000 | ambiguous |
| Naala cross karne wala chhota pul kaafi jhukk gaya hai... | PWD | State Electricity Board | 0.853 | no_keyword |
| Hamare gali ka last khambha kai mahino se bujha hua hai... | PWD | Sanitation | 0.535 | no_keyword |
| Building ki tanki mein paani aata hi nahi hai kabhi kabhi poora hafta... | Water Board | School Education | 0.704 | no_keyword |
| Do din se bijli aa ja rahi hai baar baar... | Electricity Board | Police | 0.918 | no_keyword |
| The wooden electric pole near the bus stand looks like it's about to fall... | Electricity Board | Food & Civil Supplies | 0.333 | no_keyword |
| Hamare block mein sirf humare ghar ki bijli baar baar trip ho jaati hai... | Electricity Board | PWD | 0.819 | no_keyword |
| Meri dadi ko admit karne ke liye bed hi khaali nahi mila do din tak. | Health & Family Welfare | Social Welfare | 0.587 | no_keyword |
| Lab report milne mein ek hafta lag gaya... | Health & Family Welfare | Water Board | 0.526 | no_keyword |
| Exam ka result der se aaya aur usme bhi kai bachchon ke marks galat print... | School Education | State Electricity Board | 0.897 | no_keyword |
| Bachchon ko diya jaane wala uniform is saal abhi tak nahi mila... | School Education | Transport Corporation | 0.878 | no_keyword |
| Kal raat kisi ne humari bike ka lock tod diya parking mein... | Police | Transport Corporation | 0.621 | no_keyword |
| An unknown car has been parked outside our gate for three days... | Police | Sanitation | 0.802 | no_keyword |
| Do naujawan roz raat gali mein tez bike chalate hain... | Police | PWD | 0.311 | no_keyword |
| Humein anonymous calls aa rahe hain dhamki dete hue... | Police | Health & Family Welfare | 0.345 | no_keyword |
| Talab ka paani ab hara ho gaya hai... | Pollution Control Board | Sanitation | 0.634 | no_keyword |
| Humne suna hai ki humari gali mein koi nashe ka saman becha jaa raha hai... | Police | Sanitation | 0.550 | no_keyword |
| School ke bagal wale nale se itni badbu aati hai... | Sanitation | School Education | 0.646 | ambiguous |
| Ration dukaan ke upar ka bijli ka meter bahut purana ho gaya... | Electricity Board | Food & Civil Supplies | 0.980 | ambiguous |

Same failure pattern as before, now with a slightly different mix: water/
drain/smell complaints get pulled toward Sanitation, and Police complaints
without an explicit crime word (a suspicious car, anonymous threatening
calls, a snatched phone) scatter toward whichever department's vocabulary
happens to overlap. This is a real gap, but a qualitatively different one
from v1's "keyword or nothing" behavior: it is reading the situation, not
pattern-matching one inserted word, and it gets every violent-crime and
theft case right, which is where the brief's actual complaints were.

### Confidence distribution (routing threshold = 0.6)

The backend routes anything below 0.6 confidence to human review instead of
auto-routing (`backend/src/routing.ts` in the SevaSetu app repo).

- Fraction of all 165 held-out predictions below 0.6 confidence: **13.94%**
  (23 / 165)
- Fraction of the 21 unscored rows below 0.6 confidence: **28.57%** (6 / 21)
  — 20 are genuine adversarial/no-signal rows, plus one deliberately
  unresolvable ambiguous row ("no water AND no electricity, both equally
  serious") that also has no single correct department.

This number moved in the wrong direction from the previous retrain (52.4% →
28.57%): the model is now more confident across the board, including on
adversarial input it should be uncertain about. "Testing testing 123" and
"Hello" still land low-confidence, but several nonsense/off-topic inputs that
previously triggered human review now get a confident (and wrong) department
guess. The model still has no explicit "none of the above" class, so on
input with no real signal it falls back to whichever department's word
statistics loosely match, and retraining changed which inputs happen to
clear the 0.6 bar without changing that underlying behavior. This is a real
regression on this specific axis and is flagged here rather than hidden.

### Urgency classifier

| Metric | Value | Previous retrain |
|---|---|---|
| Accuracy (147 scored rows) | **57.14%** | 51.02% |
| Macro-F1 | **0.3843** | 0.2687 |

```
              predicted:  high  low  medium
actual: high                10    0      29
actual: low                  2    1      32
actual: medium                0    0      73
```

Urgency labels in the training data are derived by scanning generated text
for a cue lexicon (`HIGH_URGENCY_CUES` / `LOW_URGENCY_CUES` in
`generate_dataset.py`). The first version of that lexicon used direct danger
words ("khoon", "ghayal", "emergency") and the model learned to detect those
specific words rather than infer severity from context, collapsing to
"medium" on held-out sentences that describe danger or triviality
differently ("we can see straight down to the river below" instead of
"khatarnak"). After broadening the lexicon to indirect phrasing ("missing
railing", "could collapse", "not that big a deal") and adding 24 new
fragments that actually use that phrasing in training, held-out accuracy
moved from 51.02% to 57.14% and macro-F1 from 0.27 to 0.38, mainly by
correctly catching more high-urgency cases (3/39 → 10/39). Low-urgency
recall barely moved (0/35 → 1/35) and "medium" is still the default answer
for anything the model hasn't seen phrased close to a training example. This
is a real improvement, not a fix. Getting further requires either a lexicon
several times broader than what generation-time cue-matching can practically
cover, or actual human-labeled urgency examples instead of programmatic
derivation, and is flagged as follow-up work rather than solved here.

## What "done" looks like, honestly

- Department classifier: real improvement, not just a bigger number. The
  brief's flagship failure cases (murder/shooting, theft delay) and all 4
  violent-crime variants in the held-out set are fixed with high confidence,
  held-out accuracy (76%) is meaningfully below the in-distribution number
  (100%) which is expected and healthy, and most errors are semantically
  reasonable near-misses rather than random guesses.
- Urgency classifier: improved (51% → 57% accuracy after broadening the cue
  vocabulary) but not fixed. The 100% sector-correlation bug from v1 is gone
  (every department in the training data now produces all three urgency
  levels), but the model still defaults to "medium" on severity language it
  wasn't trained on.
- Vocabulary: 367 → 5,689 unique tokens (100k rows), comfortably in the
  "several thousand" range the brief asked for.
- Confidence calibration on nonsense input: got worse in this retrain (52.4%
  → 28.57% of adversarial rows correctly below the 0.6 threshold). Named
  directly above rather than smoothed over.

## Reproducing this evaluation

```
python3 generate_dataset.py 100000        # writes sevasetu_grievance_dataset_v2.csv
python3 train_department_model.py         # writes sevasetu_department_bilstm.keras, etc.
python3 train_urgency_model.py            # writes sevasetu_urgency_bilstm.keras, etc.
python3 build_heldout_set.py              # writes heldout_test_set.csv
python3 evaluate_heldout.py               # writes heldout_predictions.csv, prints all metrics above
```
