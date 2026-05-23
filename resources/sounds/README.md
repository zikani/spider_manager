# Sound Files for Spider Manager

This directory contains sound files for download event notifications.

## Required Sound Files

The following sound files should be placed in this directory:

### 1. download_complete.wav (or .mp3, .ogg)
- **Purpose:** Played when a download completes successfully
- **Suggested:** Short, pleasant notification sound
- **Duration:** 1-2 seconds

### 2. download_failed.wav (or .mp3, .ogg)
- **Purpose:** Played when a download fails
- **Suggested:** Error/alert sound
- **Duration:** 1-2 seconds

### 3. queue_finished.wav (or .mp3, .ogg)
- **Purpose:** Played when all downloads in the queue are finished
- **Suggested:** Completion/chime sound
- **Duration:** 2-3 seconds

## Audio Format Requirements

- **Supported formats:** WAV, MP3, OGG (depending on Qt6 multimedia backend)
- **Recommended format:** WAV (uncompressed) for best compatibility
- **Sample rate:** 44.1kHz or 48kHz
- **Bit depth:** 16-bit or 24-bit
- **Channels:** Mono or Stereo

## Default Sounds

If no custom sound files are provided, the application will use system default sounds
or remain silent until sound files are configured in preferences.

## Finding Free Sounds

You can find free sound effects from these sources:
- Freesound.org (requires attribution for some sounds)
- Zapsplat.com (free account available)
- Pixabay audio (free, no attribution required)
- OpenGameArt.org (game-friendly sounds)

## Configuration

Sound files can be configured in the application preferences:
1. Go to Tools → Preferences
2. Navigate to the "Sounds" tab
3. Browse to select sound files for each event
4. Use the "Play" button to preview sounds
5. Enable/disable sounds for each event individually
