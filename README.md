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

It also appears this is probably the easiest way for me to get the flashcard feature working:

https://foosoft.net/projects/anki-connect/

I'm sure in the future I'll turn my nose up at Anki and prefer a custom solution, but for now, it syncs with my phone and seems like a generally good solution.

### Imagined workflows

*Learn tunes off an album*:
There's an album I really like. It has annoying track names that don't reveal the tunes on the album. I enter the album name and it downloads the metadata for the album. I then enter an overlay that asks which tracks to play. With each track it reveals both the track name and the tunes in that album. I play a track. Within the "learn from track" overlay, I can select any of the three tunes, enter its start and end time, and add it to my tune database. I can loop the tune after entering its start and end time, and if its a supported format I can slow the tune down. Once learned, I can update its learn status in the database (it would be nice if this was satisfying, maybe it could change color?).

*Find a good recording of a tune*:
Input a tune name, scrape off the session recordings and track numbers for the tune, then go to spotify and play them in succession. The user can indicate which one is good, and that information can be saved with the tune in the tune database.

*Write sets with your tunes:*
Filter by tunes you know but aren't in a set. Filter by tunes that are "starred" meaning you like them a lot right now. Look at compatible keys. Mark a few of them and write them into a set. This information is stored in the tune database, and they are backlinked so that the tunes "know" what sets they are in, just as the sets "know" what tunes are in them. Go to the "sets" overlay. It can be sorted by date added, so you can practice recently added sets. The set's should be editable as well, with completion, from your batch of tunes.

*Strengthen your recall:*
You hear a great tune in the session. You're fingers even know it! But you've forgotten the name and you forget you even know it. You ask someone for the name. You open the app/website overlay on your phone, and write down the name, and send it off. It's put in an "inbox" somewhere of tunes that need to be "namified". Later you clear the inbox: you find a good recording of the tune (or supply one from your phone), select and save abc notation for the tune. Then the tune with the recording and/or abc is added automatically to Anki under your "Tunes" deck. The recall will be strengthened. You can also "star" the tune meaning you currently like it and want to add it to sets and emphasize practicing it.

### features
- [x] store tunes in a standard format
- [x] display a given tune
- [x] consume a tune list with standard format
- [x] search thesession for tune melodies
- [ ] store abc notation for tune for offline viewing
- [ ] allow the user to select which version of the tune they prefer
- [ ] make sets from tune list (with fzf completion)
- [ ] store tune recordings, associating them with the tune metadata
- [ ] search TheSession for sets involving a tune and play them in succession to select a good recording
- [ ] tune pratice overlay
  - [ ] metronome
  - [ ] sheet music
  - [x] play a certain section of a recording on loop
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