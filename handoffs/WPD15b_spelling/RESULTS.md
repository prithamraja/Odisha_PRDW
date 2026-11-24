# WP-D15b spelling harness — results

Names: {'district': 9, 'block': 16, 'gp': 20}; Ask's cut-offs {'district': 85, 'block': 85, 'gp': 85}; shortest single word tried 5.

## Pass marks

1. **Set A** (298 questions): fields changed 2; loose readings 2; "could not find" 0.
2. **Set B, names of 7+ letters:** 3975 of 4092 read right (97.1%). Names of 5-6 letters (reported apart): 162 of 246 (65.8%).
3. **Set B wrong readings:** 12 (0.28%); outside the known near-names: 0 (0.00%).
4. **Lines and asks:** loose readings without their line: 0; asks not resolving: 0; set C asks not resolving: 0.
5. **Set C:** 14 of 14 as expected.
6. **Size** ({'gp': 6800, 'block': 314, 'district': 30}, 27-word question, 200 runs): median 65.45 ms, p95 77.73 ms (max 87.76); memory added at start-up 10.2 MB; start-up 18.3 s.

## Set C

| Question | OK | What the officer sees first |
|---|---|---|
| What should I know about Kalimella? | yes | Reading "Kalimella" as Kalimela block. For the Gram Panchayat, ask about "Kalimela GP". |
| How is Malkangri doing? | yes | Reading "Malkangri" as Malkangiri district. |
| How is Barpalli block doing? | yes | Reading "Barpalli" as Barpali block. |
| Anything in Bhubaneshwar block? | yes | Reading "Bhubaneshwar" as Bhubaneswar block. |
| How is Chikili doing? | yes | Reading "Chikili" as Chikilli Gram Panchayat. |
| Tell me about Khurda | yes | (no line) |
| how is kalimela doing | yes | (no line) |
| Is Mendrajpur behind on anything? | yes | Reading "Mendrajpur" as Mendarajpur Gram Panchayat. |
| What has been found in Atabira? | yes | Reading "Atabira" as Attabira block. |
| What should I know about Kandhmal? | yes | Reading "Kandhmal" as Kandhamal district. |
| What has the analysis found in Koraputt? | yes | Reading "Koraputt" as Koraput district. |
| Is Laxmipoor behind on anything? | yes | (no line) |
| How is Laxmipoor block doing? | yes | I could not find a place called "Laxmipoor" in the data. / Close names in the data: Laxmipur block. |
| How is Rampur block doing? | yes | I could not find a place called "Rampur" in the data. |

## Set B misses, names of 7+ letters

- Bargarh (district) <- 'Bargad' [garh->gad], frame 0
- Bargarh (district) <- 'Bargad' [garh->gad], frame 1
- Bargarh (district) <- 'Bargad' [garh->gad], frame 2 -> not found
- Bargarh (district) <- 'Bargada' [garh->gada], frame 0
- Bargarh (district) <- 'Bargada' [garh->gada], frame 1
- Bargarh (district) <- 'Bargada' [garh->gada], frame 2 -> not found
- Cuttack (district) <- 'Coottack' [u->oo], frame 0
- Cuttack (district) <- 'Coottack' [u->oo], frame 1
- Cuttack (district) <- 'Coottack' [u->oo], frame 2 -> not found
- Koraput (district) <- 'Korapoot' [u->oo], frame 0
- Koraput (district) <- 'Korapoot' [u->oo], frame 1
- Koraput (district) <- 'Korapoot' [u->oo], frame 2 -> not found
- Rayagada (district) <- 'Rayagarha' [gad->garh], frame 0
- Rayagada (district) <- 'Rayagarha' [gad->garh], frame 1
- Rayagada (district) <- 'Rayagarha' [gad->garh], frame 2 -> not found
- Rayagada (district) <- 'Rayagarh' [gada->garh], frame 0
- Rayagada (district) <- 'Rayagarh' [gada->garh], frame 1
- Rayagada (district) <- 'Rayagarh' [gada->garh], frame 2 -> not found
- Sundargarh (district) <- 'Sundargada' [garh->gada], frame 0
- Sundargarh (district) <- 'Sundargada' [garh->gada], frame 1
- Sundargarh (district) <- 'Sundargada' [garh->gada], frame 2 -> not found
- Attabira (block) <- 'Attabeera' [i->ee], frame 0
- Attabira (block) <- 'Attabeera' [i->ee], frame 1
- Attabira (block) <- 'Attabeera' [i->ee], frame 2 -> not found
- Barpali (block) <- 'Barpalee' [i->ee], frame 0
- Barpali (block) <- 'Barpalee' [i->ee], frame 1
- Barpali (block) <- 'Barpalee' [i->ee], frame 2 -> not found
- Kalimela (block) <- 'Kaleemela' [i->ee], frame 0
- Kalimela (block) <- 'Kaleemela' [i->ee], frame 1
- Kalimela (block) <- 'Kaleemela' [i->ee], frame 2 -> not found
- Laxmipur (block) <- 'Laxmeepur' [i->ee], frame 0
- Laxmipur (block) <- 'Laxmeepur' [i->ee], frame 1
- Laxmipur (block) <- 'Laxmeepur' [i->ee], frame 2 -> not found
- Laxmipur (block) <- 'Laxmipoor' [u->oo], frame 0
- Laxmipur (block) <- 'Laxmipoor' [u->oo], frame 1
- Laxmipur (block) <- 'Laxmipoor' [u->oo], frame 2 -> not found
- Laxmipur (block) <- 'Laxmipore' [pur->pore], frame 0
- Laxmipur (block) <- 'Laxmipore' [pur->pore], frame 1
- Laxmipur (block) <- 'Laxmipore' [pur->pore], frame 2 -> not found
- Sheragada (block) <- 'Sheragarha' [gad->garh], frame 0
- Sheragada (block) <- 'Sheragarha' [gad->garh], frame 1
- Sheragada (block) <- 'Sheragarha' [gad->garh], frame 2 -> not found
- Sheragada (block) <- 'Sheragarh' [gada->garh], frame 0
- Sheragada (block) <- 'Sheragarh' [gada->garh], frame 1
- Sheragada (block) <- 'Sheragarh' [gada->garh], frame 2 -> not found
- Andhrua (gp) <- 'Andhrooa' [u->oo], frame 0
- Andhrua (gp) <- 'Andhrooa' [u->oo], frame 1
- Andhrua (gp) <- 'Andhrooa' [u->oo], frame 2 -> not found
- Bandhpali (gp) <- 'Bandhpalee' [i->ee], frame 0
- Bandhpali (gp) <- 'Bandhpalee' [i->ee], frame 1
- Bandhpali (gp) <- 'Bandhpalee' [i->ee], frame 2 -> not found
- Barimunda (gp) <- 'Bareemunda' [i->ee], frame 0
- Barimunda (gp) <- 'Bareemunda' [i->ee], frame 1
- Barimunda (gp) <- 'Bareemunda' [i->ee], frame 2 -> not found
- Barimunda (gp) <- 'Barimoonda' [u->oo], frame 0
- Barimunda (gp) <- 'Barimoonda' [u->oo], frame 1
- Barimunda (gp) <- 'Barimoonda' [u->oo], frame 2 -> not found
- Bhatigaon (gp) <- 'Bhateegaon' [i->ee], frame 0
- Bhatigaon (gp) <- 'Bhateegaon' [i->ee], frame 1
- Bhatigaon (gp) <- 'Bhateegaon' [i->ee], frame 2 -> not found
- Chikilli (gp) <- 'Cheekilli' [i->ee], frame 0
- Chikilli (gp) <- 'Cheekilli' [i->ee], frame 1
- Chikilli (gp) <- 'Cheekilli' [i->ee], frame 2 -> not found
- Chikilli (gp) <- 'Chikeelli' [i->ee], frame 0
- Chikilli (gp) <- 'Chikeelli' [i->ee], frame 1
- Chikilli (gp) <- 'Chikeelli' [i->ee], frame 2 -> not found
- Chikilli (gp) <- 'Chikillee' [i->ee], frame 0
- Chikilli (gp) <- 'Chikillee' [i->ee], frame 1
- Chikilli (gp) <- 'Chikillee' [i->ee], frame 2 -> not found
- Dutimendi (gp) <- 'Duteemendi' [i->ee], frame 0
- Dutimendi (gp) <- 'Duteemendi' [i->ee], frame 1
- Dutimendi (gp) <- 'Duteemendi' [i->ee], frame 2 -> not found
- Dutimendi (gp) <- 'Dutimendee' [i->ee], frame 0
- Dutimendi (gp) <- 'Dutimendee' [i->ee], frame 1
- Dutimendi (gp) <- 'Dutimendee' [i->ee], frame 2 -> not found
- Dutimendi (gp) <- 'Dootimendi' [u->oo], frame 0
- Dutimendi (gp) <- 'Dootimendi' [u->oo], frame 1
- Dutimendi (gp) <- 'Dootimendi' [u->oo], frame 2 -> not found
- Hirlipali (gp) <- 'Heerlipali' [i->ee], frame 0
- Hirlipali (gp) <- 'Heerlipali' [i->ee], frame 1
- Hirlipali (gp) <- 'Heerlipali' [i->ee], frame 2 -> not found
- Hirlipali (gp) <- 'Hirleepali' [i->ee], frame 0
- Hirlipali (gp) <- 'Hirleepali' [i->ee], frame 1
- Hirlipali (gp) <- 'Hirleepali' [i->ee], frame 2 -> not found
- Hirlipali (gp) <- 'Hirlipalee' [i->ee], frame 0
- Hirlipali (gp) <- 'Hirlipalee' [i->ee], frame 1
- Hirlipali (gp) <- 'Hirlipalee' [i->ee], frame 2 -> not found
- Kalimela (gp) <- 'Kaleemela' [i->ee], frame 0
- Kalimela (gp) <- 'Kaleemela' [i->ee], frame 1
- Kalimela (gp) <- 'Kaleemela' [i->ee], frame 2 -> not found
- Kalyansinghpur (gp) <- 'Kalyansinhgpur' [neighbours swapped], frame 0
- Kalyansinghpur (gp) <- 'Kalyansinhgpur' [neighbours swapped], frame 1
- Kalyansinghpur (gp) <- 'Kalyansingphur' [neighbours swapped], frame 0
- Kalyansinghpur (gp) <- 'Kalyansingphur' [neighbours swapped], frame 1
- Laxmipur (gp) <- 'Laxmeepur' [i->ee], frame 0
- Laxmipur (gp) <- 'Laxmeepur' [i->ee], frame 1
- Laxmipur (gp) <- 'Laxmeepur' [i->ee], frame 2 -> not found
- Laxmipur (gp) <- 'Laxmipoor' [u->oo], frame 0
- Laxmipur (gp) <- 'Laxmipoor' [u->oo], frame 1
- Laxmipur (gp) <- 'Laxmipoor' [u->oo], frame 2 -> not found
- Laxmipur (gp) <- 'Laxmipore' [pur->pore], frame 0
- Laxmipur (gp) <- 'Laxmipore' [pur->pore], frame 1
- Laxmipur (gp) <- 'Laxmipore' [pur->pore], frame 2 -> not found
- Sharagada (gp) <- 'Shragada' [letter dropped], frame 0
- Sharagada (gp) <- 'Shragada' [letter dropped], frame 1
- Sharagada (gp) <- 'Sahragada' [neighbours swapped], frame 0
- Sharagada (gp) <- 'Sahragada' [neighbours swapped], frame 1
- Sharagada (gp) <- 'Shraagada' [neighbours swapped], frame 0
- Sharagada (gp) <- 'Shraagada' [neighbours swapped], frame 1
- Sharagada (gp) <- 'Shoragada' [a->o], frame 0
- Sharagada (gp) <- 'Shoragada' [a->o], frame 1
- Sharagada (gp) <- 'Sharagarha' [gad->garh], frame 0
- Sharagada (gp) <- 'Sharagarha' [gad->garh], frame 1
- Sharagada (gp) <- 'Sharagarha' [gad->garh], frame 2 -> not found
- Sharagada (gp) <- 'Sharagarh' [gada->garh], frame 0
- Sharagada (gp) <- 'Sharagarh' [gada->garh], frame 1
- Sharagada (gp) <- 'Sharagarh' [gada->garh], frame 2 -> not found

## Set B wrong readings

- 'Kalyansinhgpur' (made from Kalyansinghpur gp) read as [('block', 'Kalyansingpur', 96.3)]
- 'Kalyansinhgpur' (made from Kalyansinghpur gp) read as [('block', 'Kalyansingpur', 96.3)]
- 'Kalyansingphur' (made from Kalyansinghpur gp) read as [('block', 'Kalyansingpur', 96.3)]
- 'Kalyansingphur' (made from Kalyansinghpur gp) read as [('block', 'Kalyansingpur', 96.3)]
- 'Shragada' (made from Sharagada gp) read as [('block', 'Sheragada', 94.1)]
- 'Shragada' (made from Sharagada gp) read as [('block', 'Sheragada', 94.1)]
- 'Sahragada' (made from Sharagada gp) read as [('block', 'Sheragada', 88.9)]
- 'Sahragada' (made from Sharagada gp) read as [('block', 'Sheragada', 88.9)]
- 'Shraagada' (made from Sharagada gp) read as [('block', 'Sheragada', 88.9)]
- 'Shraagada' (made from Sharagada gp) read as [('block', 'Sheragada', 88.9)]
- 'Shoragada' (made from Sharagada gp) read as [('block', 'Sheragada', 88.9)]
- 'Shoragada' (made from Sharagada gp) read as [('block', 'Sheragada', 88.9)]

## Set B misses, names of 5-6 letters (reported apart)

- Ganjam (district) <- 'aGnjam' [neighbours swapped], frame 0
- Ganjam (district) <- 'aGnjam' [neighbours swapped], frame 1
- Ganjam (district) <- 'aGnjam' [neighbours swapped], frame 2
- Ganjam (district) <- 'Gnajam' [neighbours swapped], frame 0
- Ganjam (district) <- 'Gnajam' [neighbours swapped], frame 1
- Ganjam (district) <- 'Gnajam' [neighbours swapped], frame 2
- Ganjam (district) <- 'Gajnam' [neighbours swapped], frame 0
- Ganjam (district) <- 'Gajnam' [neighbours swapped], frame 1
- Ganjam (district) <- 'Gajnam' [neighbours swapped], frame 2
- Ganjam (district) <- 'Ganajm' [neighbours swapped], frame 0
- Ganjam (district) <- 'Ganajm' [neighbours swapped], frame 1
- Ganjam (district) <- 'Ganajm' [neighbours swapped], frame 2
- Ganjam (district) <- 'Ganjma' [neighbours swapped], frame 0
- Ganjam (district) <- 'Ganjma' [neighbours swapped], frame 1
- Ganjam (district) <- 'Ganjma' [neighbours swapped], frame 2
- Ganjam (district) <- 'Gonjam' [a->o], frame 0
- Ganjam (district) <- 'Gonjam' [a->o], frame 1
- Ganjam (district) <- 'Gonjam' [a->o], frame 2
- Ganjam (district) <- 'Ganjom' [a->o], frame 0
- Ganjam (district) <- 'Ganjom' [a->o], frame 1
- Ganjam (district) <- 'Ganjom' [a->o], frame 2
- Bheden (block) <- 'hBeden' [neighbours swapped], frame 0
- Bheden (block) <- 'hBeden' [neighbours swapped], frame 1
- Bheden (block) <- 'hBeden' [neighbours swapped], frame 2
- Bheden (block) <- 'Behden' [neighbours swapped], frame 0
- Bheden (block) <- 'Behden' [neighbours swapped], frame 1
- Bheden (block) <- 'Behden' [neighbours swapped], frame 2
- Bheden (block) <- 'Bhdeen' [neighbours swapped], frame 0
- Bheden (block) <- 'Bhdeen' [neighbours swapped], frame 1
- Bheden (block) <- 'Bhdeen' [neighbours swapped], frame 2
- Bheden (block) <- 'Bheedn' [neighbours swapped], frame 0
- Bheden (block) <- 'Bheedn' [neighbours swapped], frame 1
- Bheden (block) <- 'Bheedn' [neighbours swapped], frame 2
- Bheden (block) <- 'Bhedne' [neighbours swapped], frame 0
- Bheden (block) <- 'Bhedne' [neighbours swapped], frame 1
- Bheden (block) <- 'Bhedne' [neighbours swapped], frame 2
- Bheden (block) <- 'Vheden' [b->v], frame 0
- Bheden (block) <- 'Vheden' [b->v], frame 1
- Bheden (block) <- 'Vheden' [b->v], frame 2
- Bheden (gp) <- 'hBeden' [neighbours swapped], frame 0
- Bheden (gp) <- 'hBeden' [neighbours swapped], frame 1
- Bheden (gp) <- 'hBeden' [neighbours swapped], frame 2
- Bheden (gp) <- 'Behden' [neighbours swapped], frame 0
- Bheden (gp) <- 'Behden' [neighbours swapped], frame 1
- Bheden (gp) <- 'Behden' [neighbours swapped], frame 2
- Bheden (gp) <- 'Bhdeen' [neighbours swapped], frame 0
- Bheden (gp) <- 'Bhdeen' [neighbours swapped], frame 1
- Bheden (gp) <- 'Bhdeen' [neighbours swapped], frame 2
- Bheden (gp) <- 'Bheedn' [neighbours swapped], frame 0
- Bheden (gp) <- 'Bheedn' [neighbours swapped], frame 1
- Bheden (gp) <- 'Bheedn' [neighbours swapped], frame 2
- Bheden (gp) <- 'Bhedne' [neighbours swapped], frame 0
- Bheden (gp) <- 'Bhedne' [neighbours swapped], frame 1
- Bheden (gp) <- 'Bhedne' [neighbours swapped], frame 2
- Bheden (gp) <- 'Vheden' [b->v], frame 0
- Bheden (gp) <- 'Vheden' [b->v], frame 1
- Bheden (gp) <- 'Vheden' [b->v], frame 2
- Itipur (gp) <- 'tIipur' [neighbours swapped], frame 0
- Itipur (gp) <- 'tIipur' [neighbours swapped], frame 1
- Itipur (gp) <- 'tIipur' [neighbours swapped], frame 2
- Itipur (gp) <- 'Iitpur' [neighbours swapped], frame 0
- Itipur (gp) <- 'Iitpur' [neighbours swapped], frame 1
- Itipur (gp) <- 'Iitpur' [neighbours swapped], frame 2
- Itipur (gp) <- 'Itpiur' [neighbours swapped], frame 0
- Itipur (gp) <- 'Itpiur' [neighbours swapped], frame 1
- Itipur (gp) <- 'Itpiur' [neighbours swapped], frame 2
- Itipur (gp) <- 'Itiupr' [neighbours swapped], frame 0
- Itipur (gp) <- 'Itiupr' [neighbours swapped], frame 1
- Itipur (gp) <- 'Itiupr' [neighbours swapped], frame 2
- Itipur (gp) <- 'Itipru' [neighbours swapped], frame 0
- Itipur (gp) <- 'Itipru' [neighbours swapped], frame 1
- Itipur (gp) <- 'Itipru' [neighbours swapped], frame 2
- Itipur (gp) <- 'Eetipur' [i->ee], frame 0
- Itipur (gp) <- 'Eetipur' [i->ee], frame 1
- Itipur (gp) <- 'Eetipur' [i->ee], frame 2
- Itipur (gp) <- 'Iteepur' [i->ee], frame 0
- Itipur (gp) <- 'Iteepur' [i->ee], frame 1
- Itipur (gp) <- 'Iteepur' [i->ee], frame 2
- Itipur (gp) <- 'Itipoor' [u->oo], frame 0
- Itipur (gp) <- 'Itipoor' [u->oo], frame 1
- Itipur (gp) <- 'Itipoor' [u->oo], frame 2
- Itipur (gp) <- 'Itipore' [pur->pore], frame 0
- Itipur (gp) <- 'Itipore' [pur->pore], frame 1
- Itipur (gp) <- 'Itipore' [pur->pore], frame 2

## Reported, not pass marks

- Set A questions with an unmarked word tried and left alone: 207 (examples: [['stand'], ['unusual'], ['being'], ['doing'], ['doing'], ['places', 'behaving'], ['Break'], ['Break']])
- Spans tried per set A question: middle 1.0, most 21; words skipped: middle 7.0, most 18
- Unmarked words in set B scoring 80 or more but under the cut-off (left alone): 906

## What-if: the cut-off at 80 (harness only, not shipped)

- Set B, 7+ letters: 4065 of 4092 (99.3%); 5-6 letters: 234 of 246 (95.1%)
- Set B wrong readings: 12; outside the near-names: 0
- Set A: loose readings 2 [('How many GPs in Kordha uploaded GPDP in FY 24-25?', [('Kordha', 'district', 'Khordha', 92.3)]), ('What percentage of Gram Panchayats in Bhubaneshwar block have uploaded their GPDP in 2024-2025?', [('Bhubaneshwar', 'block', 'Bhubaneswar', 95.7)])]; "could not find" 0; fields changed 2
