---
name: band-score
description: |
  Turn a song recording (original, optionally its MR/instrumental) and a reference lead sheet into band practice material:
  an edited practice MP3 plus part scores in the order drums → vocal → bass → synth → electric guitar, aligned to beats and chords.
  Use when the user gives an MP3 and asks for 악보, 채보, 파트 악보, 밴드 악보, 악기별 분리, or a shorter practice MP3.
---

# Band Score

Two roles with a file contract between them. Keep them apart so scoring can be redone without re-separating.

| Role | Owns | Never decides |
|---|---|---|
| **Separation (audio)** | decoding to lossless PCM, original↔MR alignment, applying edits identically to every source and stem, stem WAVs, `manifest.json` | beats, bars, chords, notes |
| **Scoring (music)** | structure map, beat/bar grid, chord chart, cut points, part notes, MIDI/LilyPond/PDF, correction log | — |

`manifest.json`: input file hashes, reference mix, sample rate and sample count, original→edited time map, per-source offset, separation model/version, and each stem's source and known limits. Grid and chords belong to scoring; if the reference mix changes, rebuild the grid.

Reference mix = the MR when one is given, otherwise the original. Song-specific files (structure map, previews, approvals) live in a persistent song work folder, never in this skill or `/tmp`. Preserve source audio, raw model JSON and approved inputs so a restart does not destroy reproducibility.

Listening: check whether this session can actually listen to audio. If it cannot, record each join or judgment as unheard and ask the user to confirm it by ear.

## 1. Separate (audio)

- Decode every input to WAV first; MP3 is listening output only.
- `uv run --python 3.11 --with demucs --with torchaudio --with numpy --with soundfile python -I -m demucs -n htdemucs_6s -o sep <wavs>`
  (verified on macOS arm64, Python 3.11, demucs 4.1.0, torch 2.14.1; without the explicit numpy the import failed in that environment.)
- With an MR: take instruments from the MR stems and the vocal from the original's vocal stem, after checking the MR's vocal stem for chorus or bleed. Do not subtract MR from the original to get vocals; they are usually different mixes, not phase-identical.
- htdemucs_6s has no synth stem. `piano` + `other` are listening aids for synth, not an isolated synth. `guitar` is not guaranteed to be electric only.
- Offset is defined as `original_time = reference_time + offset`. Measure it at matching beats in at least three places (start, middle, end). If it varies, tell apart beat-detection error, structural difference and real drift before correcting.

## 2. Map structure (scoring)

- Read the lead sheet first: exact bar count, pickup, last bar, key, meter, tempo. Count bars on the rendered image, not on extracted text.
- Beat grid from the reference mix's drum stem (`librosa.beat.beat_track`, seeded with the sheet tempo) is a candidate. The tracker can lock onto offbeat hits or slip half a beat, and bar chroma alone can pick the wrong beat of the bar.
- Fix beat and bar phase with the vocal stem: convert vocal onsets to beat positions and compare them with the sheet rhythm (pickups, rests, ties) in several sections not used for the fit. Piano/vocal onset strength per beat subdivision is supporting evidence only.
- Chord chroma cannot tell repeated sections apart (same progression). Transcribe the vocal stem with timestamps (e.g. `mlx-whisper` `whisper-large-v3-turbo`, in the song's language, sheet lyrics as `initial_prompt`).
- Chroma maxima and transcribed lyrics are candidate evidence, not readings. Place each occurrence by lyric, section order, timing and the sheet together; leave it marked unclear when they disagree.
- Output a table: audio bar, reference seconds, sheet bar (or none: intro, silence, tag, link), lyric, occurrence number, confidence. Key change and interlude stay automatic-analysis candidates until heard.
- When the recording disagrees with the sheet, record the difference. Do not silently overwrite either.

## 3. Edit the practice MP3

- Scoring proposes cut points at the same musical position in both occurrences (e.g. start of the same sheet bar); audio applies them to every source and stem, shifted by each source's offset.
- Make listening previews of each candidate and report the exact removed ranges in seconds and bars, including leading silence. Final files that depend on the choice wait for the user; analysis, drafts and skill work continue.
- Run `uv run --with numpy --with soundfile python scripts/apply_edit.py spec.json` with `{"segments":[[0,10],[20,30]],"sources":{"mix":{"path":"mix.wav","offset":0}},"out_dir":"edit","fade_s":0.04}`; paths are relative to the working directory. Inputs must share a sample rate; resample first. Missing leading/trailing samples are zero-padded.
- The helper overlaps adjacent segments by `fade_s` (default 0.04), shortening the output by that duration per join; `fade_s: 0` concatenates without overlap. Record those shifts in the edit time map. For a beat-centred join, extend the preceding end and following start by half the fade in the segment specification; the helper does not add those handles. Say whether the join sits on a strong or weak beat.
- A short crossfade does not prove a clean join: syllables, held notes and beat at each join need listening.
- Map the unedited grid through the edit's time map, then check the beats on both sides of each join and the final bar; re-detect only if that check fails (beat tracking on the edited file wobbles near joins). Record the bar and beat position on each side of every join: a cut that is not a whole number of bars moves every later bar line off the source's.
- PCM mix and stems must share start and sample count; MP3, MIDI and PDF are checked by musical position and ending instead.

## 4. Score the parts

Order: drums → vocal → bass → synth → electric guitar. Draft the chord chart first, but let drums and bass correct it.

Bar numbers: first full bar of the practice audio = 1, used by every part, MIDI and the structure map, and note which practice bar is lead-sheet bar 1. Place any partial lead-in bar and the vocal's pickup where the audio actually enters.

Drums:
- If band-energy onset rules on the drum stem cannot separate the voices, compare with ADTOF-pytorch (`xavriley/ADTOF-pytorch@85c192e`, bundled weights): `adtof --audio drums.wav --out drums.mid --device cpu`. Classes map to GM 35 kick, 38 snare, 47 tom, 42 hi-hat, 49 cymbal (crash and ride together), 100 fps, no latency compensation.
- Measure the model's and the grid's offset against stem onsets per song and record them in the song log. Follow the rhythm-revision procedure below before quantising; a small residual after calibrating both to the same onsets is not an independent accuracy check.
- Consistent output is not correctness. Give the user a few representative bars as stem → synthesised score → MR + synthesised score, and ask about specific candidate hits.

Pitched parts and MIDI:
- basic-pitch (0.4.0 needs `setuptools<70` in the env): run inference once per stem, then compare a few threshold/min-length candidates on one section and check another section; keep the default when the candidate is not better there. Report the figures as agreement with the stem (CQT of a plain synth render, one-to-one onsets), never as transcription accuracy.
- Flag extracted notes in near-silent stem passages (e.g. the first 150 ms below 3 % of overall stem RMS). Check the mix and other stems before removal: separation may have lost the real instrument. Keep unsupported candidates out of confirmed notation, retain them in the evidence log, and distinguish noise from unresolved separation loss.
- MuScriptor is an alternative transcription source; use it as the primary source for instruments where phrase listening supports it: `HF_HUB_OFFLINE=1 uv run --python 3.11 --with muscriptor==0.4.0 muscriptor transcribe <stem>.wav -f json --instruments electric_bass --model large --device mps --dtype float16 --no-quantize` (weights are gated: cached snapshot or authenticated access after accepting the license; measured peak memory was about 11 GB in one large-model MPS run, not a guarantee; run one stem at a time; `list-instruments` names the groups). Its times are 10 ms model tokens that cluster on the beat grid, not preserved micro-timing, and it has no velocity. Flag notes in silence or past the audible ending using the cross-stem checks above. Audit duplicate instrument layers and drum-class mappings before rendering; do not apply the bass choice automatically to other parts. Compare raw JSON with exported MIDI for offsets, and record model revision, settings, full input versus crops and crop overlap consistency.
- Pick the pitch source per instrument by ear, not by agreement figures: render one phrase as stem → source A → source B with the same synth and loudness and ask the user. On one song the bass from MuScriptor was judged far more accurate than basic-pitch, although both agreed about equally with the approved section. Known failures: basic-pitch reads harmonics of low bass notes as separate notes an octave or fifth up; pYIN collapses fast alternating notes into their common sub-harmonic. Evidence that only ranks two candidates from the same wrong source (CQT rise, harmonic levels) cannot fix either.
- Notes in `other` that `piano` does not cover are reported by section; unidentified pads/bells stay out of the piano track until the user decides.
- Use one tempo map for all tracks and record the time contract explicitly: reference_audio_time = MIDI_time + offset, plus any piecewise edit map. Either retain the leading audio silence or remove it with a documented offset; do not mix these conventions. Use a local tempo change at a join only when musical evidence supports it. Read MIDI back and compare bar starts to the grid. A cut may remove a fractional bar: map the actual source times, never match edited and full-song endings by bar number alone.

- To choose between MIDI candidates (e.g. two agents extracting independently), freeze one evaluation script before either candidate exists: vocal excluded, same synth with cached per-pitch drum samples, per-part loudness matched to the MR stems, MR-vs-render CQT agreement, sections and per-stem onsets as diagnostic figures, plus a one-beat-shifted baseline; select the instrument source by phrase listening rather than the highest aggregate score. Running A,B and B,A must give the same scores; differences within 0.001 are a tie.
- A higher overall agreement can come from extra notes (harmonics, bleed). Report onset agreement next to it. Repeated equal-interval model chords need independent stem attacks; matching a beat grid alone does not prove a real re-attack. A user-approved bass-synchronised guitar part is an arrangement, not proof of transcription accuracy; preserve independent fills and log the exceptions.

Rhythm revision before engraving:
- Keep raw extraction times. Compare approved and newly extracted sections using the same grid and reference-time offset; do not mix quantised notation with raw model timing unnoticed. Verify unchanged sections by pitch, onset, end and velocity, not note counts alone.
- Separate model delay, wrong beat/bar phase, onset jitter, and note-end errors. A fixed model delay verified in several independent passages may be corrected across that model's output with a logged offset; do not turn a local musical discrepancy into a global shift. A drum grid does not prove another instrument has no expressive timing. Inspect each part against its own stem, and keep strum spread, swing, triplets and real flams/rolls when supported.
- Create a separate quantised comparison candidate using the demonstrated subdivision (including 32nds when needed), not a mandatory 8th/16th/32nd grid. Log movements, preserve raw notes, and never merge separate attacks that land in one cell; refine locally or retain unresolved timing. Read MIDI back and check note counts, pitches, velocities, overlaps and unchanged sections.
- Check held-note endings and rests as well as starts. Pitch-tracker dropouts are not note-offs: compare vocal/part energy, pitch bands and decay against the mix. Preserve printed harmony in score and MIDI. Inspect final fills beyond the nominal last bar before trimming; distinguish new attacks from reverb and document fermata timing.
- Listen to a short before/after passage; when this session cannot listen, ask the user one focused question with comparable previews. Treat better alignment metrics as supporting evidence, not musical approval.

Playability before reducing notes:
- Record instrument tuning/range, available frets, playing technique and player constraints. Existing fingering code is a candidate generator, not proof of performability. Judge a phrase at performance tempo, including held notes, releases and the next position, rather than isolated onset chords.
- Bass: assign notes to distinct strings when simultaneously sounding; test position shifts, open-string alternatives, sustained-string conflicts and multi-note passages. Low positions and small shifts are preferences, not reasons to change pitch or force monophony. Do not assume four consecutive frets are comfortable in the low register; flag stretches for the player. Keep internal finger assignments even when TAB finger numbers are omitted.
- Guitar: test string/fret assignments and feasible finger/barre placements, then transitions and held-string conflicts. For pick-only playing, check the picking route, string skips and muting; do not silently require hybrid/finger picking or truly simultaneous attacks on separated strings. Distinguish a strummed chord, arpeggio and lead line. Draw the actual selected chord shape above its attack, not an unrelated chord-name dictionary shape.
- Piano: assign notes to both hands and voices over the phrase, considering span, black/white-key geometry, repeated notes, leaps, held notes and release time. An octave is a conservative review trigger when hand span is unknown, not an automatic deletion rule; flag wider shapes for confirmation. Pedal sustains released keys but does not make unreachable simultaneous attacks playable. Preserve skilled players' inner voices and moving accompaniment.
- Treat abrupt register jumps, implausible stretches, overlapping pitches and impossible transitions in any part as triggers for a cross-instrument check. Compare the same event in the target stem, other stems and original/reference mix: attack time, pitch trajectory, harmonic series and decay. Test bleed, octave/harmonic errors, legitimate high/low playing and overdubs as competing explanations. A louder spectral band or duplicate pitch in another stem does not identify the source by itself. Keep, correct, reassign or hold the note only with logged evidence; do not automatically octave-shift, delete or move it to the instrument with the widest range. Ask for focused listening when evidence cannot separate the alternatives.
- Classify each difficult passage as feasible, player-dependent, or unresolved/impossible under the stated constraints. Try alternate fingering/hand distribution first; awkward fingering alone does not prove a false note. Propose only local changes within the user's arrangement scope and record what musical information changes.

Score from MIDI:
- Preserve the source MIDI and derive the playing score from a versioned note list. Do not impose blanket limits on notes per chord, attacks per bar, voices, or rhythmic subdivisions, and do not shorten sustained notes merely because another note starts. Preserve melody, harmony, fills and actual re-attacks. Change an event only for documented transcription evidence or a specific playing constraint; distinguish corrections from user-authorised arrangement and log pitch, onset, duration and voicing changes. Keep score and playback consistent: after approved octave changes, removed duplicates or chord arrangements, rebuild the playing MIDI and its preview from that version, preserve the raw source separately and compare untouched tracks exactly. A rhythm-slash chord permits a representative playable voicing; record it rather than playing the stale extracted chord.
- Vocal score comes from the lead sheet (melody, second voice, lyrics), not from the vocal MIDI; mark sections where the recording differs.
- Every instrument PDF carries the vocal melody, lyrics and chord symbols on a staff above the part, sharing bar numbers and line breaks with the vocal score.
- When requested, show common accompaniment as chord names plus the original attack rhythm; retain single-note lines and solos as TAB. Treat a chord-chart substitution as an approved arrangement and log differences from extracted pitches. Use only necessary grip diagrams, placed above their attacks in one row; remove familiar redundant diagrams before shrinking text. Confirm the page budget with the player and keep title/part labels on one line.
- Judge layout by readability and compactness, not page count. Fold only what really repeats in the quantised notation (bar-by-bar match, logged): % / two-bar repeat signs for identical drum bars, repeat barlines with 1st/2nd endings (stacked verse lyrics) or D.S./Coda for repeated sections, multi-bar rests for silence. Keep practice bar numbers and the audio's playing order easy to follow.
- Keep alignment-only lead-ins and reverb-only tails out of the playing score; include real ending attacks and fills even when they extend beyond the lead sheet's nominal last bar.
- Check each repeat against its own audio before reusing a bar; do not force a bass note to the chord root.
- Label every part and section as confirmed transcription, unconfirmed draft, or approved arrangement. Do not invent what was not heard: stock drum patterns for unclear hits, guitar bends, synth inner voices.

## 5. Render and check

- Every PDF, MIDI and the practice MP3 use one bar table. Compare bar count and section starts, not just durations.
- Ask before folding near-repeats into a unified arrangement; faithful-to-recording is the default.
- Bass and guitar as TAB (standard tuning unless told otherwise) with rhythm stems over the TAB; use the phrase-level playability checks above and log unresolved fingering. Drums as drum tab (one line per voice, x/o on the grid).
- Render the PDF and look at every page: bar numbers, chords, key/time signatures, page turns, note/lyric collisions, TAB tuning and range.
- A successful render is not evidence of musical accuracy.
- Apply one correction to one representative bar and confirm it reaches PDF and MIDI without re-separation and without shifting the bar table.
