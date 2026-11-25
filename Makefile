PY ?= .venv/bin/python

.PHONY: film setup validate smoke reference keyframes narration shots wan music subtitles assemble radio-cut clean

# The whole film from storyboard.json. Every stage is cached: a re-run only regenerates what changed.
film: validate reference keyframes narration shots music assemble

setup:
	python3 -m venv .venv && $(PY) -m pip install -r requirements.txt

validate:   ; $(PY) -m pipeline.validate
smoke:      ; $(PY) scripts/smoke_test.py
reference:  ; $(PY) -m pipeline.reference
keyframes:  ; $(PY) -m pipeline.keyframes
narration:  ; $(PY) -m pipeline.narration
shots:      ; $(PY) -m pipeline.shots
wan:        ; $(PY) -m pipeline.wan && $(PY) -m pipeline.shots
music:      ; $(PY) -m pipeline.music
subtitles:  ; $(PY) -m pipeline.subtitles
assemble:   ; $(PY) -m pipeline.assemble

radio-cut: validate narration
	$(PY) -m pipeline.assemble --radio-cut

clean:
	find outputs -type f ! -name .gitkeep -delete
