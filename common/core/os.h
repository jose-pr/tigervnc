/* Copyright 2026 jose-pr <jose-pr@coqui.dev>
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

#ifndef __CORE_OS_H__
#define __CORE_OS_H__

/*
 * MSVC lacks a number of POSIX APIs that this project's previous Windows
 * toolchain (mingw, a GCC/glibc-compatible environment) provided
 * transparently. Centralize the portable equivalents/shims here rather
 * than scattering per-file fixes.
 */
#ifdef _WIN32

#include <stdlib.h> // _MAX_PATH
#include <string.h> // _stricmp, _strnicmp
#include <winsock2.h> // struct timeval, FILETIME

#ifndef PATH_MAX
#define PATH_MAX _MAX_PATH
#endif

#define strcasecmp _stricmp
#define strncasecmp _strnicmp

typedef int mode_t;

inline int gettimeofday(struct timeval *tv, void *)
{
  /* FILETIME is in 100ns intervals since 1601-01-01; convert to
   * microseconds since the Unix epoch (1970-01-01). */
  static const unsigned long long kEpochDiff = 116444736000000000ULL;
  FILETIME ft;
  unsigned long long t;

  GetSystemTimeAsFileTime(&ft);
  t = ((unsigned long long)ft.dwHighDateTime << 32) | ft.dwLowDateTime;
  t = (t - kEpochDiff) / 10;

  tv->tv_sec = (long)(t / 1000000ULL);
  tv->tv_usec = (long)(t % 1000000ULL);

  return 0;
}

/* POSIX dirname(), minimally: strip the trailing filename component,
 * accepting both path separators since Windows paths use either. Modifies
 * and returns its argument, matching the (permitted) in-place POSIX form. */
inline char *dirname(char *path)
{
  char *slash = strrchr(path, '\\');
  char *fwdslash = strrchr(path, '/');

  if (fwdslash > slash)
    slash = fwdslash;

  if (slash == nullptr) {
    static char dot[] = ".";
    return dot;
  }

  if (slash == path) {
    *(slash + 1) = '\0';
    return path;
  }

  *slash = '\0';
  return path;
}

#endif // _WIN32

#endif // __CORE_OS_H__
