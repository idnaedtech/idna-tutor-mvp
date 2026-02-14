# Input Classifier — All Categories & Phrases

## ACK (Student understood / agrees)

**English:** haan, ha, yes, okay, ok, got it, understood, right, correct, yeah, yep, sure
**Hindi:** हां, हाँ, ठीक है, समझ गया, समझ गयी, अच्छा, बिल्कुल, जी, जी हां, पता है
**Hinglish:** samajh gaya, samajh gayi, theek hai, accha, acha, hmm, hmmm, bilkul

## IDK (Student doesn't understand)

**English:** I don't know, no idea, don't understand, confused, what?, huh?, not sure, explain again
**Hindi:** समझ में नहीं आया, नहीं समझा, फिर से बताइए, दुबारा बताओ, क्या मतलब है, मुझे नहीं पता, पता नहीं, कुछ समझ नहीं आया
**Hinglish:** samajh nahi aaya, nahi samjha, phir se batao, dubara batao, kya matlab hai, pata nahi, explain karo

## ANSWER (Mathematical/numeric response)

Detection: Contains numbers, fractions (x/y), mathematical expressions, or
spelled-out numbers. Handled by answer_checker module, not phrase matching.

## CONCEPT_REQUEST (Wants teaching/explanation)

**English:** explain, what is, how do I, tell me about, teach me, show me
**Hindi:** बताइए, समझाइए, concept बताओ, कैसे करते हैं, formula बताओ, method बताओ
**Hinglish:** explain karo, concept batao, kaise karte hain, formula batao, method batao, example do

## COMFORT (Frustrated/upset/uncomfortable)

**English:** you're rude, you are rude, don't shout, too fast, slow down, not helpful,
you're not helping, I don't like this, I give up, this is too hard, I'm frustrated,
I can't do this, stop it
**Hindi:** मुझे अच्छा नहीं लग रहा, बहुत मुश्किल है, समझ में नहीं आ रहा, रुको,
धीरे बोलो, मुझे नहीं आता, छोड़ो, बहुत तेज़ बोल रहे हो, आप rude हो,
मैं नहीं कर सकता, बंद करो, मुझे गुस्सा आ रहा है
**Hinglish:** bahut mushkil hai, samajh nahi aa raha, ruko, dheere bolo, chhodo,
bahut tez bol rahe ho, I give up, too hard hai

**Action:** Comfort response ONLY. No teaching, no questions. Stay in current state.

## STOP (End session)

**English:** bye, goodbye, stop, quit, end, finish, let's stop, I want to stop, enough
**Hindi:** बाय, रुको, बंद करो, बस, चलो बंद करते हैं
**Hinglish:** bye, band karo, bas, chalo band karte hain, let's stop here, enough for today

## TROLL (Off-topic/jokes)

Detection: No mathematical content + no classifier match + not an emotional signal.
**Action:** Brief acknowledgment + gentle redirect: "Accha! Chalo wapas math pe aate hain?"
