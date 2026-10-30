#include "core/system/coretime.h"
#include "presonus/delay_timer.hpp"
#include "presonus/dice/packet_services.hpp"
#include <array>
#include <cfenv>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <limits>
#include <vector>
using Presonus::DelayTimer;
using Access = presonus::timing::DelayTimerAccess;
using State = presonus::timing::DelayTimerState;
extern "C" void timer_c1(DelayTimer *,
                         float) asm("_ZN8Presonus10DelayTimerC1Ef");
extern "C" void timer_c2(DelayTimer *,
                         float) asm("_ZN8Presonus10DelayTimerC2Ef");
extern "C" void timer_d1(DelayTimer *) asm("_ZN8Presonus10DelayTimerD1Ev");
extern "C" void timer_d2(DelayTimer *) asm("_ZN8Presonus10DelayTimerD2Ev");
static bool enabled = false;
static std::int64_t clockTicks;
static unsigned clockCalls = 0;
extern "C" std::int64_t __real__ZN8presonus4dice19packetClockRawTicksEv();
extern "C" std::int64_t __wrap__ZN8presonus4dice19packetClockRawTicksEv() {
  if (enabled) {
    ++clockCalls;
    return clockTicks;
  }
  return __real__ZN8presonus4dice19packetClockRawTicksEv();
}
static unsigned word(const unsigned char *p) {
  return unsigned(p[0]) | (unsigned(p[1]) << 8) | (unsigned(p[2]) << 16) |
         (unsigned(p[3]) << 24);
}
static std::uint64_t quad(const unsigned char *p) {
  return word(p) | (std::uint64_t(word(p + 4)) << 32);
}
static std::int64_t signedWord(std::uint64_t n) {
  std::int64_t result;
  std::memcpy(&result, &n, 8);
  return result;
}
static float floating(unsigned n) {
  float result;
  std::memcpy(&result, &n, 4);
  return result;
}
static unsigned bits(float f) {
  unsigned result;
  std::memcpy(&result, &f, 4);
  return result;
}
static void append(std::vector<unsigned char> &out, std::uint64_t n,
                   unsigned size) {
  for (unsigned i = 0; i < size; ++i)
    out.push_back(static_cast<unsigned char>(n >> (8 * i)));
}
static std::vector<unsigned char>
run(const std::array<unsigned char, 48> &input) {
  const auto op = word(input.data()), arg = word(input.data() + 4);
  clockTicks = signedWord(quad(input.data() + 8));
  clockCalls = 0;
  enabled = true;
  State state{signedWord(quad(input.data() + 16)),
              signedWord(quad(input.data() + 24)),
              signedWord(quad(input.data() + 32)),
              floating(word(input.data() + 40)), word(input.data() + 44) != 0};
  auto *timer = static_cast<DelayTimer *>(::operator new(sizeof(DelayTimer)));
  if (op == 0)
    timer_c1(timer, floating(arg));
  else if (op == 1)
    timer_c2(timer, floating(arg));
  else {
    timer_c1(timer, 1.0f);
    Access::set(*timer, state);
  }
  std::uint64_t result = 0;
  if (op == 2)
    timer_d1(timer);
  else if (op == 3)
    timer_d2(timer);
  else if (op == 4)
    timer->reset();
  else if (op == 5)
    timer->beginAction(floating(arg));
  else if (op == 6)
    result = timer->endAction();
  else if (op == 7)
    result = timer->wasLongEnough();
  else if (op == 8)
    result = timer->isExecuting();
  else if (op == 9)
    result = timer->isLongEnoughYet();
  else if (op == 10)
    result = bits(timer->getProgressNormalized());
  else if (op == 11)
    result = static_cast<std::uint64_t>(timer->getElapsedMilliseconds());
  else if (op > 11)
    std::abort();
  // Destructor records use their pre-destruction semantic state; no native
  // ended-lifetime object or padding read is performed.
  if (op != 2 && op != 3)
    state = Access::get(*timer);
  std::vector<unsigned char> out;
  append(out, result, 8);
  append(out, static_cast<std::uint64_t>(state.start), 8);
  append(out, static_cast<std::uint64_t>(state.duration), 8);
  append(out, static_cast<std::uint64_t>(state.elapsed), 8);
  append(out, bits(state.reciprocal), 4);
  append(out, state.executing, 4);
  append(out, clockCalls, 4);
  if (op != 2 && op != 3)
    timer_d1(timer);
  ::operator delete(timer);
  enabled = false;
  return out;
}
static void startupSequence() {
  enabled = true;
  clockCalls = 0;
  clockTicks = 1234567890;
  DelayTimer timer(2.0f);
  timer.beginAction(0.0f);
  auto s = Access::get(timer);
  if (s.start != 1234 || s.duration != 2000 || s.elapsed || !s.executing)
    std::abort();
  clockTicks = (1234LL + 1999) * 1000000 + 999999;
  if (timer.isLongEnoughYet() || timer.wasLongEnough() ||
      timer.getElapsedMilliseconds() != 1999)
    std::abort();
  if (!(timer.getProgressNormalized() > 0.999f &&
        timer.getProgressNormalized() < 1.0f))
    std::abort();
  clockTicks = (1234LL + 2000) * 1000000;
  if (!timer.isLongEnoughYet() || !timer.endAction() || timer.isExecuting() ||
      !timer.wasLongEnough())
    std::abort();
  auto calls = clockCalls;
  if (timer.endAction() || clockCalls != calls ||
      timer.getProgressNormalized() != -1.0f)
    std::abort();
  timer.beginAction(5.0f);
  s = Access::get(timer);
  timer.beginAction(floating(0x7fc12345));
  auto retained = Access::get(timer);
  if (retained.duration != s.duration ||
      bits(retained.reciprocal) != bits(s.reciprocal))
    std::abort();
  clockTicks -= 1000000;
  if (timer.getElapsedMilliseconds() != -1 ||
      timer.getProgressNormalized() >= 0)
    std::abort();
  timer.reset();
  if (timer.isExecuting() || timer.wasLongEnough() ||
      timer.getProgressNormalized() != -1.0f || Access::get(timer).elapsed)
    std::abort();
  enabled = false;
  if (Core::SystemClock::getFrequency() != 1000000000ULL)
    std::abort();
  auto first = presonus::dice::packetClockRawTicks();
  auto second = presonus::dice::packetClockRawTicks();
  if (first <= 0 || second < first)
    std::abort();
}
int main(int argc, char **argv) {
  static_assert(sizeof(float) == 4 && sizeof(std::int64_t) == 8 &&
                std::numeric_limits<float>::is_iec559);
  if (argc != 2 || std::fegetround() != FE_TONEAREST)
    return 2;
  std::ifstream f(argv[1], std::ios::binary);
  std::array<unsigned char, 12> header{};
  f.read(reinterpret_cast<char *>(header.data()), 12);
  if (!f || std::memcmp(header.data(), "DTMRv001", 8))
    return 3;
  unsigned count = word(header.data() + 8), nanResults = 0,
           nanPayloadDifferences = 0;
  for (unsigned i = 0; i < count; ++i) {
    std::array<unsigned char, 48> input;
    std::array<unsigned char, 44> expected;
    f.read(reinterpret_cast<char *>(input.data()), 48);
    f.read(reinterpret_cast<char *>(expected.data()), 44);
    if (!f)
      return 4;
    auto actual = run(input);
    bool quietNaN = false;
    if (word(input.data()) == 10) {
      auto a = word(actual.data()), e = word(expected.data());
      if (std::isnan(floating(e))) {
        if (!std::isnan(floating(a)) || !(a & 0x00400000) || !(e & 0x00400000))
          return 5;
        quietNaN = true;
        ++nanResults;
        if (a != e) {
          ++nanPayloadDifferences;
          if (nanPayloadDifferences <= 8)
            std::printf("NaN result case%u original=%08x native=%08x "
                        "(classification only)\n",
                        i, e, a);
        }
      }
    }
    for (unsigned j = 0; j < 44; ++j)
      if (actual[j] != expected[j] && !(quietNaN && j < 4)) {
        std::fprintf(stderr,
                     "Mismatch case%u op%u offset%u original%u native%u\n", i,
                     word(input.data()), j, expected[j], actual[j]);
        return 6;
      }
  }
  startupSequence();
  std::printf("PASS %u original DelayTimer fixtures; NaN results %u, payload "
              "differences %u explicitly excluded; composed startup and actual "
              "CCL clock passed\n",
              count, nanResults, nanPayloadDifferences);
}
