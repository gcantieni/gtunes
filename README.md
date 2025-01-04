# Track traditional tune collection

Uses homebrew python3 installation.

### Commentary
Ideally it should be quite easy to add a tune, and also quite easy to update the tune in the future. But getting in a tune that I want to be practicing seems like a quite desirable feature. Eventually I want to be able to do this from my phone with just a name.

here's some good ideas: https://thesession.org/discussions/46809

easyabc is an old program that has some good features:
https://easyabc.sourceforge.net/

could also have which instruments a tune is mastered on.
e.g. FiddleStatus field if I pick up fiddle.


### features
- [ ] store tunes in a standard format
- [ ] display a given tune
- [ ] display tunes that should be learned
- [ ] add a tune via a url form and update home database of tunes.
- [ ] store different formats for a tune, mp3, links (starting at specific time)
- [ ] output to spreadsheet
- [ ] output to plaintext list or cheatsheet with first few notes of each tune
- [ ] output to anki, adding tune as a flashcard
- [ ] keep track of sets of tunes

### Tune object

- name: name of tune
- type: one of
    - jig
    - reel
    - barn dance
    - slip jig
    - hop jig
- abc: string array. abc notation for tune, with different versions. first member of the list is the default tune version displayed.
- status: how well i know it. this could be sourced from anki in the future. can be simple int from 1-5, 1 being don't know it at all, 5 means i can start it from another tune with no prompting.
- tradition:
    - irish
    - old time
    - french canadian
- composer: string
- comments: string array of additional comments about the tune
- date added: date string
- date updated: date string

### Set object
represents a collection of tunes that goes well together

TuneSet
- tunes: array of Tune objects