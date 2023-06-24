***NOTE: In progress!! Come back later!***

# PiPlayer

A relatively easy-to-use utility to set up one or more RaspberryPi's as a video player.

PiPlayer will install vlc on your Pi(s), transfer videos, and set them to play on startup.

## Installation 

You should have one or more Pi's on your local network. The Pi's should have:

* the latest raspbian with console only install
* auto-login enabled
* passwordless authentication with ssh keys

On your computer, install PiPlayer with:

```bash
pip install piplayer
```

## Usage

### Basic usage

You can send one or more videos directly to individual Pi's like so:

```bash
piplayer --host HOSTNAME --video VIDEONAME.mp4
```

This will transfer the video file(s) to the Pi, and make them play on startup in a loop. The `--video` option can take multiple video files.

### Project file

For more complex scenarios, you can also create project instructions as a YAML file. Here's an example project file:

```yaml
players:
  - host: player1.local
    videos: vid1.mp4
  - host: player2.local
    videos: ["vid2.mp4", "vid3.mp4"]
```

To use:

```bash
piplayer --project PROJECTFILE.yaml
```

#### Required settings:

`players` is an array, containing at minimum a `host` and `video` entry.

**host**: the hostname or ip of the Pi on the local network

**videos**: the local path(s) to video files to be sent to the Pi  
This can be a single video, an array, or a glob pattern (like `myvids/*.mp4`).

#### Optional settings:

The following settings are optional:

**loop**: should the playlist loop?  
Can be `true` or `false`. Defaults to `true`.

**random**: play the videos in random order   
Can be `true` or `false`. Defaults to `false`.

**user**: the username on the Pi  
Defaults to `pi`.

**gap**: (TODO!) time in seconds to pause between each video (shows a black screen)  
Defaults to `0.0`.

**start_at**: (TODO!) start the playlist at a specific time.  
Defaults to `0.0`.

If you want to apply the same settings to all the Pi's, add a `settings` dictionary like so:

```yaml
settings:
    user: cooluser 
    random: true
    gap: 2
```

These settings will be sent to all the Pi's listed in the `players` section (but individual player settings have precedence).
