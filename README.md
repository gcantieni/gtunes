# Track and learn traditional Irish tunes

### Installation and setup
External dependencies: `fzf`, `python3`, `abcm2ps`

I'm on mac, so for me that just involved:

```sh
brew install fzf abcm2ps
# python3 already installed
```

Installation:

Clone the repo

To activate a Python virtual environment and install the dependencies:
```sh
cd gtunes
python3 -m venv .venv
. .venv/bin/activate

pip install -t requirements.txt

pip install -e .
```

Verify this worked with
```sh
gtn -h
```

### Feature specific setup

#### Spotify integration
`gtn` can search spotify for tracks containing a specific tune. This is much more reliable than simply searching the tune name, as often the track name doesn't have the tune in it. To enable this feature, you need to setup spotify developer credentials in Spotify, which is luckily pretty simple.

To setup spotify credentials (requires a paid spotify account):
- Go to the developer dashboard: https://developer.spotify.com/dashboard
- "Create App"
    - You can enter a localhost url for the redirect url. Mine is http://localhost:1234
    - Enter a description
- Once it's created, go to "Settings" on the top right to get the credentials:
    - Client ID
    - Client Secret (click "View client secret")
- `gtunes` keeps your credentials in a private environment file at the project root, `.env`. Paste in your credentials, e.g.:

```sh
SPOTIPY_CLIENT_ID='b604f0434d3444fbb49afce7564e52c3'
SPOTIPY_CLIENT_SECRET='188fb8c2865d4346912cf1fd1f2e072c'
SPOTIPY_REDIRECT_URI='http://localhost:1234'
```

`gtn spot -h` should give the basic spotify command options.

#### Flashcards: Anki integration
`gtn` can create flashcards the use the magic of spaced repetition to help with tune memorization.

Install Anki. Install AnkiConnect, an API for apps to integrate with Anki. This is best summed up by their website: https://foosoft.net/projects/anki-connect/

NOTE: On MacOS you will have to also run

```sh
defaults write net.ankiweb.dtop NSAppSleepDisabled -bool true
defaults write net.ichi2.anki NSAppSleepDisabled -bool true
defaults write org.qt-project.Qt.QtWebEngineCore NSAppSleepDisabled -bool true
```

If you have a specific flashcard deck you want the tunes to be put in you can set it in the envionment or in the .env file:

```sh
export GTUNE_ANK_DECK="Irish Tunes"
```

The default deck name is "GTunes"

`gtn flash -h` will give usage notes about how to use this feature.

### Goal and vibe
This is currently designed as a specifically me-oriented app to reduce the friction in the process of maintaining a list of Irish tunes that I know, and using that list to learn new Irish tunes, generally from recordings.

Overall, the feeling I want to inspire is a satisfied feeling of hoarding. I want to be able to just dump tunes, recordings, voice memos, and names into my tune database and feel like it is just additive, and like I can actually use these things I'm saving.

### Friction points in my current process
Currently I have a big note with a "Learn" section (for tunes that I don't know at all), a "Practice" section (for tunes that I know at a session if someone starts playing, but I can't start), and a section of tunes I know properly, organized by type and then by key. I have another text document of chaotically written out sets. I have lots of voice memos taken within sessions. I have mp3s of music I've purchased. I have spotify playlists of tunes I want to learn. I have lots of albums of Irish music that I've added to my library and vaguely want to learn.

Specific friction points in my process: (I might not be able to solve all of these but it's good to list them all out)
- "Namifying:" learning to recall a tune based on its name. This greatly helps playing tunes in sessions. I've found the best way to do this is flash cards and spaced repetition. But to make a flash card requires me to go to online, search the tune, select a version, take a screen shot, and paste this in. This gets repetitive when I want to do it to many tunes, and it's largely a rote process that could be automated.
- Finding a good recording of a tune to learn: I often have to go to TheSession.org and look up the tune, and one by one search for the recordings on spotify, and play little snippets to find a good recording. I often forget what a good recording is, and lose my place it.
- Saving and organizing my own recordings of tunes. I have a big mass of voice memos on my phone that I never go back to listen to, because it feels too chaotic--I forget they exist. The process feels combersome to go and manually search through my voice memos for God-only-knows-what-I've-called-it.
- Thinking of sets: I often forget to think about this or write it down. I think because I forget what tune is already in sets that I've written and what isn't, some tunes are in multiple sets. I also forget what tune I want to put in more sets or am liking right now. Right now I write the tune hopefully in my "sets" note and hope I look at it sometime and think about other tunes to do so.
- Tracking how well I know a tune: Right now I have to move a tune around in my tune list a bunch, first from the "Learn", then to the "Practice", and finally into the right section of my "Know" list. It always goes the same way, and it could be much simpilar and involve less cut-and-pasting.
- Tracking recordings that I want to learn: Sometimes I just LOVE an album and I want to learn everything off of it. But I forget until I hear that album again. Sometimes if I'm in the right space I'll have a thesession window open trying to figure out what tunes they're playing and I'll write: Allistrum’s March, link to thesession abc, 14 kitty lie over. I manually form this link between the official name for a tune, the recording and the tune.
- Have all the information if I need it, but limit information if I don't: Sometimes I just want a simple list of tunes, sometimes I want to get all my Em tunes, sometimes I want just my jigs, sometimes I want an intersection of these things, sometimes I want to sheet music and the spotify recording and the youtube video. It depends on the context. My plaintext list annoys me when I wish I'd saved the spotify link I learned it from, but that stuff clutters up my list when I'm just looking through it.

### Minimum viable product
- [x] make flashcards: with the name or thesession id as input, take the first version off the session, extract the first abc version, and put it on an Anki flash card to be learned, perhaps with a recording of it as well
- [x] find spotify recordings of a tune and allow the user to quickly cycle through them to find a favorite.
- [x] list all the tunes off each track of a recording on spotify
- [x] maintain a tune database and export to csv 
- [ ] save a voice memo or other recording with the tune in the tune database

### Nice to have
- [ ] save a playlist of favorite recordings of a tune within the app
- [ ] add to the tune database from phone either through todoist integration, synced plaintext note, a phone app, or a web request
- [x] store a list of sets that back links to each tune (use obsidian?)
- [ ] built in metronome
- [ ] built in slow-down feature for mp3s of tunes
- [ ] store my own variations of a tune in abc or mp3 form

### Plaintext tune list spec

I have written a parser for the current way I write my tune list so that it can be extracted. The current format that is expected to be consumed by the parsing algorithm is as follows:

Expects something like:

```
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
```

where each tune is of the form:

```
- Tune Name- comment1, comment2, key, link
```
where the comments, key, and link are all jumbled together, and key is somthing of the form `[A,B,C,D,E,F,G][m][modal]`