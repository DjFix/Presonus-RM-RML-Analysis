#pragma once
#include "presonus/uux/FirmwareUpdaterPaths.hpp"
#include <cassert>
#include <cerrno>
#include <csetjmp>
#include <cstdint>
#include <cstring>
#include <iostream>
#include <string>
#include <sys/types.h>
#include <sys/wait.h>
#include <system_error>
#include <time.h>
#include <unistd.h>
namespace fixture {
unsigned kind, forkBits, systemBits, pidBits, loops, animate, present,
    statusBits;
unsigned timeout, waits, clocks, sleeps, callbacks, systems, forks, exits;
std::uint64_t startNs, hash;
int exitCode, waitError;
std::jmp_buf jump;
const char *command;
int asInt(unsigned bits) {
  int value;
  static_assert(sizeof value == sizeof bits);
  std::memcpy(&value, &bits, sizeof value);
  return value;
}
void reset() {
  waits = clocks = sleeps = callbacks = systems = forks = exits = 0;
  hash = 1469598103934665603ull;
  waitError = 0;
}
void byte(unsigned char b) { hash = (hash ^ b) * 1099511628211ull; }
void string(const char *text) {
  while (*text)
    byte(static_cast<unsigned char>(*text++));
  byte('|');
}
struct Listener final : Presonus::UUX::FirmwareUpdateListener {
  void doAlert(const char *, const char *, const char *) override {
    assert(false);
  }
  void dismissAlert() override { assert(false); }
  void onProgress(const char *title, const char *message,
                  float value) override {
    assert(present && std::strcmp(title, "Applying firmware update.") == 0);
    assert(std::strlen(message) <= 127);
    ++callbacks;
    string(title);
    string(message);
    unsigned bits;
    std::memcpy(&bits, &value, sizeof bits);
    for (unsigned i = 0; i < 4; ++i)
      byte((bits >> (8 * i)) & 255u);
  }
};
} // namespace fixture
extern "C" pid_t __wrap_fork() {
  assert(fixture::kind == 0 || fixture::kind == 1);
  ++fixture::forks;
  return fixture::asInt(fixture::forkBits);
}
extern "C" int __wrap_system(const char *command) {
  assert((fixture::kind == 0 || fixture::kind == 1) && fixture::forkBits == 0);
  assert(std::strcmp(command, fixture::command) == 0);
  ++fixture::systems;
  return fixture::asInt(fixture::systemBits);
}
extern "C" [[noreturn]] void __wrap_exit(int code) {
  assert((fixture::kind == 0 || fixture::kind == 1) && fixture::forkBits == 0);
  ++fixture::exits;
  fixture::exitCode = code;
  std::longjmp(fixture::jump, 1);
}
extern "C" pid_t __wrap_waitpid(pid_t pid, int *status, int flags) {
  assert(fixture::kind == 1 && static_cast<unsigned>(pid) == fixture::pidBits);
  assert(flags == WNOHANG);
  ++fixture::waits;
  if (fixture::waitError) {
    errno = fixture::waitError;
    return -1;
  }
  if (fixture::timeout || fixture::waits <= fixture::loops)
    return 0;
  *status = fixture::asInt(fixture::statusBits);
  return 42;
}
extern "C" int __wrap_clock_gettime(clockid_t clock, timespec *value) {
  assert(fixture::kind == 1 && clock == CLOCK_MONOTONIC);
  std::uint64_t ns = fixture::startNs;
  if (fixture::clocks) {
    if (fixture::timeout == 1)
      ns = (fixture::startNs / 1000000000ull + 800) * 1000000000ull;
    else if (fixture::timeout == 2)
      ns = (fixture::startNs / 1000000000ull + 800) * 1000000000ull -
           (fixture::clocks == 1 ? 500000000ull : 0);
    else
      ns += (fixture::clocks - 1) * 1000000000ull;
  }
  ++fixture::clocks;
  value->tv_sec = ns / 1000000000ull;
  value->tv_nsec = ns % 1000000000ull;
  return 0;
}
extern "C" int __wrap_usleep(useconds_t microseconds) {
  assert(fixture::kind == 1 && microseconds == 1000000);
  ++fixture::sleeps;
  return 0;
}

namespace fixture {
inline void requireProductionMethods() {
  using U = Presonus::UUX::FirmwareUpdater;
  int (U::*volatile setter)(Core::CStringBuffer<256> &) = &U::setUsbImagePath;
  int (U::*volatile url)(Core::CStringBuffer<256> &) = &U::setUuxUpgradeUrl;
  int (U::*volatile local)() = &U::doLocalFirmwareUpdate;
  int (U::*volatile usb)() = &U::doUsbFirmwareUpdate;
  int (U::*volatile execute)(const char *) = &U::executeBashUpgradeScript;
  int (U::*volatile spin)(int) = &U::spinUpgradeDisplay;
  (void)setter;
  (void)url;
  (void)local;
  (void)usb;
  (void)execute;
  (void)spin;
}
} // namespace fixture
