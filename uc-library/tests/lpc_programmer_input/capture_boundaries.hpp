#pragma once
#include "presonus/application/LPCProgrammerGeometry.hpp"
#include <cassert>
#include <cerrno>
#include <cstdint>
#include <cstring>
#include <iostream>
#include <sstream>
#include <string>
#include <time.h>
#include <unistd.h>
#include <vector>
struct Event {
  int result;
  unsigned byte, advance;
};
static std::vector<Event> events;
static unsigned reads, clocks;
static std::uint64_t nowMs;
extern "C" ssize_t __wrap_read(int descriptor, void *data, size_t size) {
  assert(descriptor == 73 && size == 1);
  const Event event = reads < events.size() ? events[reads] : Event{0, 0, 1};
  ++reads;
  nowMs += event.advance;
  if (event.result == 1)
    *static_cast<unsigned char *>(data) = event.byte;
  if (event.result < 0)
    errno = EAGAIN;
  return event.result;
}
extern "C" ssize_t __wrap___read_chk(int descriptor, void *data, size_t size,
                                     size_t capacity) {
  // Preserve the real fortified boundary's capacity requirement; never issue
  // a real read. Only the compiler-observed one-byte operation is supported.
  assert(size == 1 && capacity >= size);
  return __wrap_read(descriptor, data, size);
}
extern "C" int __wrap_clock_gettime(clockid_t clock, timespec *value) {
  assert(clock == CLOCK_MONOTONIC);
  ++clocks;
  value->tv_sec = nowMs / 1000;
  value->tv_nsec = (nowMs % 1000) * 1000000;
  return 0;
}
static unsigned nibble(char c) { return c <= '9' ? c - '0' : c - 'a' + 10; }
