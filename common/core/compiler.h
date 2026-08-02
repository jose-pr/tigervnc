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

#ifndef __CORE_COMPILER_H__
#define __CORE_COMPILER_H__

/*
 * A handful of GCC/Clang-only attributes have no MSVC equivalent; these
 * macros expand to the attribute where supported and to nothing otherwise.
 */
#if defined(__GNUC__) || defined(__clang__)
#define CORE_FORMAT_PRINTF(fmt_idx, args_idx) \
  __attribute__((__format__ (__printf__, fmt_idx, args_idx)))
#define CORE_FORMAT_ARG(idx) __attribute__ ((format_arg (idx)))
#define CORE_WARN_UNUSED_RESULT __attribute__ ((warn_unused_result))
#else
#define CORE_FORMAT_PRINTF(fmt_idx, args_idx)
#define CORE_FORMAT_ARG(idx)
#define CORE_WARN_UNUSED_RESULT
#endif

#endif // __CORE_COMPILER_H__
