# Design

## Audience
Ethiopian and Habesha viewers, at home and in the diaspora, watching on their phones (TikTok, Instagram, Telegram, family WhatsApp groups). Narration in Amharic, English subtitles for diaspora kids and non-Amharic friends.

## Intent
They laugh because they recognise their own mother ("if I come and find it...", "put it on my head!"), tag their siblings, and end feeling warm about the Habesha mom who always finds everything and has an answer for everything.

The film tells two short true stories from our house: the lost bag that Mom finds in one second, and the trash that goes "on her head".

## User test 1: radio cut
File played: `outputs/radio_cut/radio_cut.mp4` (or `.wav`), 75 s, narration + placeholder music, black screen, English subtitles.
Questions asked: Did it make you laugh, and where? Does Mom sound like a real Habesha mom; angry enough in 05, 07, 11? Anything confusing, slow or too long? Would you send it to someone?

TODO: fill with what each tester actually said (at least 3 people).

| Person | What they said | What I will change |
|---|---|---|

## User test 2: near-final cut
File played: `outputs/final/film_9x16.mp4`.

TODO: fill with what each tester actually said (at least 3 people).

| Person | What they said | What changed |
|---|---|---|

## Shot reasons
| Shot | Who speaks | Line (English) | Why this shot exists |
|---|---|---|---|
| shot_01 | narrator | Every Habesha mom has a hidden superpower. | Hook: names the shared experience in the first seconds so Habesha viewers stop scrolling. |
| shot_02 | mom | My daughter, bring me my bag from the bedroom table. | Sets up the request: an ordinary moment every viewer has lived. |
| shot_03 | narrator | I went in. Not on the table. Under the bed, in the wardrobe... I searched everywhere. | The search: exaggerated effort makes the later reveal funnier. |
| shot_04 | child | Mom! It's not here! I can't find it! | The child's surrender: the mistake every kid makes. |
| shot_05 | mom | What?! It's not there?! If I come in there and find it... I'm kicking you! | The moment the child dreads: Mom is really annoyed and coming. The laugh comes from viewers remembering it, not from Mom joking. |
| shot_06 | narrator | Mom walked in. It didn't take her one second. It was on the bed, right in front of me! | The reveal: the bag was in plain sight the whole time. |
| shot_07 | mom | Here it is! What is this?! Where are your eyes?! | Mom's scolding line, the second classic phrase. Serious for the child; funny only in hindsight. |
| shot_09 | narrator | Another day, Mom was busy making wot. I cleaned the house and came with the trash. | Second story setup: Mom is overloaded and busy, which is why the next answer comes out the way it does. |
| shot_10 | child | Mom, where should I put the trash? | The innocent question that sets up the final punchline. |
| shot_11 | mom | Put it on my head! | The biggest laugh for viewers, because every Habesha kid has heard it from a stressed mom. |
| shot_12 | narrator | Habesha moms find everything, and have an answer for everything. For my mom. | Lands the idea: now, together, we laugh. The scolding turns into love, which is what makes people share it. |

Shots 07 and 11 reuse the keyframes of 06 and 09 with a close push-in on Mom's face (cutaways): the generated versions showed her smiling, the opposite of the story (E04, F07).

## Changes from my own review of the first narration (2026-11-25)
| What I noticed | What changed in storyboard.json |
|---|---|
| Mom sounded flat and teasing. In real life she is angry in the moment; we only laugh later when we remember. | Shot 05: angry ("ምን?! የለም?!" added). Shot 07: angry disbelief ("ይሄ ምንድነው?!" added). Shot 11: sarcastic and annoyed. Emotion tags sent to TTS (E03). Mom's images now show her annoyed, not playful. |
| Shot 08 said the idea out loud ("today we laugh, back then it wasn't funny"). The idea should guide the tone, not be a line in the story. | Shot 08 removed. 11 shots, 72 s + 3 s end card. |
| Shots 5–7 sounded unnatural; 1–3 were fine. | Traced to the lite TTS model; all narration now on the main model (E03). |
