#!/usr/bin/env python3
"""A minimal RFB server offering QEMU's audio extension, to test a client.

Serves one connection, advertises the audio pseudo-encoding, waits for the
client to enable audio, then streams a sine it generates itself. Nothing in
that path resamples or mixes, so the client's output can be compared against
an exact expected amplitude: at --amplitude 20000 with 16-bit samples a
correct client emits 20000/32768 = 0.610352.

    python qemu_audio_server.py --port 5900              # then: vncviewer :0
    python qemu_audio_server.py --port 5900 --no-audio   # control arm

--no-audio serves the identical session with the pseudo-encoding withheld,
where a correct client must play nothing at all.

Standard library only. Written from the wire format, sharing no code with any
VNC implementation. MIT OR Apache-2.0.
"""
import argparse, math, socket, struct, sys, time

RFB_VERSION = b"RFB 003.008\n"
SEC_TYPE_NONE = 1

MSG_SET_PIXEL_FORMAT, MSG_SET_ENCODINGS = 0, 2
MSG_FB_UPDATE_REQUEST, MSG_KEY, MSG_POINTER, MSG_CUT_TEXT = 3, 4, 5, 6
MSG_QEMU_CLIENT = MSG_QEMU_SERVER = 255
MSG_FB_UPDATE = 0

PSEUDO_ENCODING_QEMU_AUDIO = -259
SUBMSG_AUDIO = 1
AUDIO_END, AUDIO_BEGIN, AUDIO_DATA = 0, 1, 2          # server -> client
ENABLE_AUDIO, DISABLE_AUDIO, SET_AUDIO_FORMAT = 0, 1, 2  # client -> server
FORMATS = {0: "U8", 1: "S8", 2: "U16", 3: "S16", 4: "U32", 5: "S32"}
FORMAT_S16 = 3

WIDTH, HEIGHT, NAME = 640, 480, b"qemu-audio-bench"


def rx(sock, n):
    buf = bytearray()
    while len(buf) < n:
        try:
            chunk = sock.recv(n - len(buf))
        except socket.timeout:
            # Only the first byte of a message says "nothing to read"; a
            # timeout part way through one just means it arrived split.
            if buf:
                continue
            raise
        if not chunk:
            raise ConnectionError(f"peer closed after {len(buf)} of {n} bytes")
        buf += chunk
    return bytes(buf)


def handshake(sock):
    sock.sendall(RFB_VERSION)
    print(f"client version: {rx(sock, 12).decode().strip()}", file=sys.stderr)
    sock.sendall(bytes([1, SEC_TYPE_NONE]))
    chosen = rx(sock, 1)[0]
    if chosen != SEC_TYPE_NONE:
        raise ValueError(f"client chose security type {chosen}, only None is offered")
    sock.sendall(struct.pack(">I", 0))   # SecurityResult: OK (required in 3.8)
    rx(sock, 1)                          # ClientInit shared-flag
    sock.sendall(struct.pack(">HH BB BB HHH BBB xxx I", WIDTH, HEIGHT,
                             32, 24, 0, 1, 255, 255, 255, 16, 8, 0, len(NAME)) + NAME)


def sine(phase, frames, freq, rate, channels, amp):
    """S16LE, interleaved. Returns samples and the phase to resume from, so
    chunks join without the click a discontinuity would put in the spectrum."""
    out = bytearray()
    step = 2.0 * math.pi * freq / rate
    for _ in range(frames):
        v = max(-32768, min(32767, int(amp * math.sin(phase))))
        out += struct.pack("<h", v) * channels
        phase += step
        if phase > 2.0 * math.pi:
            phase -= 2.0 * math.pi
    return bytes(out), phase


def serve(conn, args):
    handshake(conn)
    enabled, negotiated, sent, phase, deadline = False, None, 0, 0.0, None
    next_send = None
    conn.settimeout(0.05)

    while True:
        if deadline is not None and time.monotonic() >= deadline:
            break

        # Stream on a clock rather than only when the client falls silent: a
        # client that keeps asking for framebuffer updates never leaves a gap.
        if enabled:
            now = time.monotonic()
            if next_send is None:
                next_send, deadline = now, now + args.seconds
            while now >= next_send:
                frames = args.rate // 20
                payload, phase = sine(phase, frames, args.frequency,
                                      args.rate, args.channels, args.amplitude)
                conn.sendall(struct.pack(">BBHI", MSG_QEMU_SERVER, SUBMSG_AUDIO,
                                         AUDIO_DATA, len(payload)) + payload)
                sent += len(payload)
                next_send += frames / float(args.rate)

        try:
            t = rx(conn, 1)[0]
        except socket.timeout:
            continue
        except (ConnectionError, OSError):
            break

        if t == MSG_SET_PIXEL_FORMAT:
            rx(conn, 19)
        elif t == MSG_SET_ENCODINGS:
            rx(conn, 1)
            count, = struct.unpack(">H", rx(conn, 2))
            encs = struct.unpack(f">{count}i", rx(conn, 4 * count))
            print(f"SetEncodings: {count} encodings, audio pseudo-encoding "
                  f"{'REQUESTED' if PSEUDO_ENCODING_QEMU_AUDIO in encs else 'absent'}",
                  file=sys.stderr)
        elif t == MSG_FB_UPDATE_REQUEST:
            rx(conn, 9)
            if args.audio:   # a pseudo-encoding rectangle: no pixels, no data
                conn.sendall(struct.pack(">BxH", MSG_FB_UPDATE, 1)
                             + struct.pack(">HHHHi", 0, 0, 0, 0,
                                           PSEUDO_ENCODING_QEMU_AUDIO))
            else:            # still answer, or the client just looks hung
                conn.sendall(struct.pack(">BxH", MSG_FB_UPDATE, 0))
        elif t == MSG_KEY:
            rx(conn, 7)
        elif t == MSG_POINTER:
            rx(conn, 5)
        elif t == MSG_CUT_TEXT:
            rx(conn, 3)
            length, = struct.unpack(">I", rx(conn, 4))
            rx(conn, length)
        elif t == MSG_QEMU_CLIENT:
            sub = rx(conn, 1)[0]
            op, = struct.unpack(">H", rx(conn, 2))
            if sub != SUBMSG_AUDIO:
                raise ValueError(f"unknown QEMU submessage {sub}")
            if op == SET_AUDIO_FORMAT:
                fmt, channels = struct.unpack(">BB", rx(conn, 2))
                freq, = struct.unpack(">I", rx(conn, 4))
                negotiated = (fmt, channels, freq)
                print(f"SetAudioFormat: {FORMATS.get(fmt, fmt)}, {channels} channel(s), "
                      f"{freq} Hz", file=sys.stderr)
                if fmt != FORMAT_S16:
                    print("  note: this bench only generates S16", file=sys.stderr)
                args.rate = freq or args.rate
                args.channels = channels or args.channels
            elif op == ENABLE_AUDIO:
                print("EnableAudio: streaming", file=sys.stderr)
                conn.sendall(struct.pack(">BBH", MSG_QEMU_SERVER, SUBMSG_AUDIO, AUDIO_BEGIN))
                enabled = True
            elif op == DISABLE_AUDIO:
                print("DisableAudio", file=sys.stderr)
                if enabled:
                    conn.sendall(struct.pack(">BBH", MSG_QEMU_SERVER, SUBMSG_AUDIO, AUDIO_END))
                enabled = False
            else:
                raise ValueError(f"unknown QEMU audio operation {op}")
        else:
            raise ValueError(f"unknown client message type {t}")

    if enabled:
        try:
            conn.sendall(struct.pack(">BBH", MSG_QEMU_SERVER, SUBMSG_AUDIO, AUDIO_END))
        except OSError:
            pass

    print(f"\nnegotiated format : {negotiated}", file=sys.stderr)
    print(f"audio bytes sent  : {sent}", file=sys.stderr)
    if args.audio:
        print(f"expected peak     : {args.amplitude / 32768.0:.6f}  "
              f"({args.amplitude}/32768)", file=sys.stderr)
    else:
        print("expected peak     : 0.0 (control arm)", file=sys.stderr)

    if args.audio and sent == 0:
        print("FAIL: the client never enabled audio, so nothing was streamed.",
              file=sys.stderr)
        return 1
    return 0


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--port", type=int, default=5900)
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--amplitude", type=int, default=20000)
    p.add_argument("--frequency", type=float, default=440.0)
    p.add_argument("--rate", type=int, default=48000)
    p.add_argument("--channels", type=int, default=2)
    p.add_argument("--seconds", type=float, default=5.0)
    p.add_argument("--no-audio", dest="audio", action="store_false",
                   help="withhold the pseudo-encoding: the control arm")
    args = p.parse_args()
    if not 0 <= args.amplitude <= 32767:
        p.error("--amplitude must be within 0..32767")

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as srv:
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.bind((args.host, args.port))
        srv.listen(1)
        print(f"listening on {args.host}:{args.port} (display :{args.port - 5900})"
              + (" -- audio OFFERED" if args.audio else " -- audio WITHHELD"),
              file=sys.stderr)
        conn, peer = srv.accept()
        print(f"client connected from {peer[0]}:{peer[1]}", file=sys.stderr)
        with conn:
            try:
                return serve(conn, args)
            except (ConnectionError, OSError) as exc:
                print(f"connection ended: {exc}", file=sys.stderr)
                return 1


if __name__ == "__main__":
    sys.exit(main())
