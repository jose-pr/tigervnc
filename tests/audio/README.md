# A deterministic bench for the QEMU audio extension

`qemu_audio_server.py` is a minimal RFB server that advertises QEMU's audio
pseudo-encoding and streams a sine wave it generates itself. It exists so that
testing a client's audio support does not require running QEMU.

```
python tests/audio/qemu_audio_server.py --port 5900
vncviewer :0
```

## Why not just use QEMU

You can, and for an end-to-end check you should — the extension is QEMU's, and
audio comes from QEMU's own `-vnc` display with an `audiodev` attached, never
from a VNC server running inside the guest.

But for the narrower question of *"does the client decode and play the stream
correctly"*, QEMU brings in a real sound card, a guest OS and a mixer. It also
brings a trap: if the card the client plays into is the same one being
streamed, it will happily record an echo of the client's own output and report
it as success, with the level rising as it feeds back on itself.

## What this gives you instead

Nothing in this path resamples, mixes or touches hardware, so the amplitude a
correct client emits is an **exact** number rather than "something nonzero":

| `--amplitude` | expected peak |
| --- | --- |
| 20000 | `20000/32768` = **0.610352** |

Measured with a probe client: peak `0.610352`, ~439.4 Hz against a 440 Hz
request, over 153600 bytes.

## Run the control arm too

```
python tests/audio/qemu_audio_server.py --port 5900 --no-audio
```

This serves the identical session with the pseudo-encoding withheld. A correct
client then plays **nothing at all**, and the server reports `audio bytes
sent: 0`.

It is worth the extra thirty seconds: without it a bench cannot distinguish
"audio works" from "the capture rig reports sound whatever happens". A pass on
the audio arm means much less if the no-audio arm was never shown to fail.

The server also exits non-zero if audio was offered and the client never
enabled it, so a run that streamed nothing cannot be mistaken for a green one.

## Options

| flag | default | |
| --- | --- | --- |
| `--port` | 5900 | display `:0` |
| `--host` | 127.0.0.1 | |
| `--amplitude` | 20000 | 0..32767, signed 16-bit |
| `--frequency` | 440.0 | Hz |
| `--rate` | 48000 | fallback if the client sets no format |
| `--channels` | 2 | fallback if the client sets no format |
| `--seconds` | 5.0 | how long to stream once enabled |
| `--no-audio` | off | withhold the pseudo-encoding (control arm) |

The client's `SetAudioFormat` wins over `--rate` and `--channels`. Only S16 is
generated; a client asking for another format is told so on stderr.

## Provenance

Written from the wire format of the QEMU audio extension — the client and
server message pair and pseudo-encoding -259 — and shares no code with
TigerVNC or with any other VNC implementation. That independence is the point:
if this and the viewer agree, the agreement is evidence, which would not be
true had one been written from the other.

Python standard library only; no dependencies to install.

Offered under MIT OR Apache-2.0, so it can be taken into the tree under
whatever terms suit.
