# Track traditional tune collection

Uses homebrew python3 installation and homebrew fzf.
An python3 virtual environment is used and can be installed using the requirements.txt file.

### Commentary
Ideally it should be quite easy to add a tune, and also quite easy to update the tune in the future. But getting in a tune that I want to be practicing seems like a quite desirable feature. Eventually I want to be able to do this from my phone with just a name.

here's some good ideas: https://thesession.org/discussions/46809

easyabc is an old program that has some good features:
https://easyabc.sourceforge.net/

could also have which instruments a tune is mastered on.
e.g. FiddleStatus field if I pick up fiddle.

Found an option for abc display, and flash cards:
https://github.com/abcjs-music/obsidian-plugin-abcjs
coupled with
https://github.com/st3v3nmw/obsidian-spaced-repetition

This keeps me in the plaintext world which is convenient and nice.

Though I do also want to store all of my audio files, potentially bare and potentially with tune.
This also means that I should key not based on tune name but rather on a guid.

The ultimate goal of this app is to actually practice tunes. To start I can export tunes into a flashcard app and a sheet music display app. Eventually I could integrate these features directly into the app, with a custom spaced repetition algorithm and built in abc notation viewer.

Because it is an aural tradition, one of the most important features in practicing is the ability to playback audio. This will probably involve the spotify API for many of these tunes since I don't have a local copy for most of them, though this would be a good goal. I want to be able to loop a certain section of a spotify track.

Spotify doesn't have a playback speed option, though there was this idea online:

> If you have audio files or streams, use media players like VLC or custom players built with frameworks like Web Audio API (for web-based applications) that allow playback speed control.

So perhaps I can try integrating the two. Or just learn tunes up to tempo for now

### features
- [x] store tunes in a standard format
- [x] display a given tune
- [x] consume a tune list with standard format
- [x] search thesession for tune melodies
- [ ] store abc notation for tune for offline viewing
- [ ] allow the user to select which version of the tune they prefer
- [ ] make sets from tune list (with fzf completion)
- [ ] store tune recordings, associating them with the tune metadata
- [ ] tune pratice overlay
  - [ ] metronome
  - [ ] sheet music
  - [ ] play a certain section of a recording on loop
  - [ ] slow down recording without changing pitch
- [ ] show what sets a tune is in
- [ ] show the abc notation as image
- [ ] display tunes that should be learned
- [ ] add a tune via a url form and update home database of tunes
- [ ] store different formats for a tune, mp3, links (starting at specific time)
- [ ] integrate with spotify, and replay a section of a track corresponding with the tune
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
- starred: whether it is an emphasized tune, one i currently like
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

### Plaintext tune list

The current format that is expected to be consumed by the parsing algorithm is as follows:

Expects something like:
LEARN:
    - tunes
PRACTICE:
    - tunes
REELS:
A
    - tunes
JIGS:
G
    - tunes