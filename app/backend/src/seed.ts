/**
 * Seeds the database with a small set of hand-written, varied complaints
 * (not the templated synthetic set) so the dashboard has realistic-looking
 * data to demo against on first run.
 */
import { ingestComplaint } from "./routing.js";
import { stubClassifier } from "./classifier.js";

const SAMPLE_COMPLAINTS: Array<{ text: string; phone?: string; location?: string }> = [
  { text: "Bahut bada gaddha ho gaya hai humare gali mein, do din pehle ek bike wala gir gaya tha.", location: "Kanpur, Uttar Pradesh", phone: "9999123456" },
  { text: "No water supply in our colony for the last 4 days, tanker bhi nahi aaya is baar.", location: "Bhopal, Madhya Pradesh", phone: "9999234567" },
  { text: "Streetlight khaali padi hai pichle mahine se, raat ko chalna mushkil hai.", location: "Patna, Bihar", phone: "9999345678" },
  { text: "Garbage has not been collected from our street in over a week, it's starting to smell very bad.", location: "Pune, Maharashtra" },
  { text: "PHC mein doctor roz time pe nahi aate, patients ghanto wait karte hain.", location: "Jaipur, Rajasthan", phone: "9999456789" },
  { text: "School mein teacher kabhi nahi aati, bachche bina padhai ke baithe rehte hain.", location: "Gaya, Bihar" },
  { text: "The 42 bus route has been cancelled without any notice, students are stuck.", location: "Chennai, Tamil Nadu", phone: "9999567890" },
  { text: "Mere ghar mein chori ho gayi kal raat, FIR darj karwani hai turant.", location: "Lucknow, Uttar Pradesh", phone: "9999678901" },
  { text: "Ration dukaan is month band hai, humein anaj nahi mila.", location: "Ranchi, Jharkhand" },
  { text: "My father's pension has not come for two months now, we depend on it.", location: "Guwahati, Assam", phone: "9999789012" },
  { text: "Land record mein galat naam likha hai, revenue office chakkar laga laga ke thak gaye hain.", location: "Indore, Madhya Pradesh" },
  { text: "Factory se bahut dhuan aata hai roz subah, bachchon ko saans lene mein problem ho rahi hai.", location: "Surat, Gujarat", phone: "9999890123" },
  { text: "Sadak par bahut bada gaddha hai, kal ek scooty wala gir gaya, koi zimmedar nahi hai.", location: "Nagpur, Maharashtra" },
  { text: "There has been no electricity in our area for 6 hours, transformer maybe burnt out.", location: "Hyderabad, Telangana", phone: "9999901234" },
  { text: "Sewage line phat gayi hai, gandha pani ghar ke saamne bhar gaya hai.", location: "Kolkata, West Bengal" },
];

async function main() {
  console.log(`Seeding ${SAMPLE_COMPLAINTS.length} sample complaints...`);
  for (const c of SAMPLE_COMPLAINTS) {
    const result = await ingestComplaint(stubClassifier, c);
    console.log(`  ${result.ticketId} -> ${result.department} [${result.routeType}, conf=${result.departmentConfidence.toFixed(2)}]`);
  }
  console.log("Done.");
}

main();
