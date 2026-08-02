/* Copyright 2022 Mikhail Kupchik
 * Copyright 2026 jose-pr
 *
 * This is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 2 of the License, or
 * (at your option) any later version.
 *
 * This software is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this software; if not, write to the Free Software
 * Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307,
 * USA.
 */

#ifndef __AUDIOOUTPUT_H__
#define __AUDIOOUTPUT_H__

#include <stddef.h>
#include <stdint.h>

// An audio playback device, of which we only ever use one at a time.
//
// Everything here is called from the main thread, in the middle of
// handling a protocol message, so no method may block. An
// implementation is expected to hand the samples to the system and
// return, not to wait for them to be played.

class AudioOutput
{
public:
  virtual ~AudioOutput() {}

  // create() returns the playback device for this platform, or nullptr
  // if this platform has no implementation, or if no usable device
  // could be opened.
  static AudioOutput* create();

  // The format the device wants samples in. These are the sample
  // format codes from rfb/qemuTypes.h, which is also what the server
  // will be asked for, so no conversion is needed anywhere.
  virtual uint8_t getSampleFormat() const = 0;
  virtual uint8_t getChannels() const = 0;
  virtual uint32_t getFrequency() const = 0;

  // start() is called each time the server begins streaming, and
  // stop() when it stops. Samples arrive via play() in between, in
  // chunks of no particular size.
  virtual void start() = 0;
  virtual void stop() = 0;
  virtual void play(const uint8_t* samples, size_t length) = 0;
};

#endif
