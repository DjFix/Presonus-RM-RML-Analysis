#include "presonus/mixer/FxReverbNumFormatter.hpp"
#include "presonus/mixer/PreDelayFormatterT9.hpp"
#include "presonus/mixer/XmenFormatterInitializer.hpp"
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <unistd.h>
using namespace Presonus::Mixer;
#if FORMATTER_INIT_CLASS == 0
using Target = FxReverbNumFormatter;
constexpr const char *expectedName = "reverbnum";
extern "C" void
complete(void *) asm("_ZN8Presonus5Mixer20FxReverbNumFormatterD1Ev");
#else
using Target = PreDelayFormatterT9;
constexpr const char *expectedName = "predelayT9";
extern "C" void
complete(void *) asm("_ZN8Presonus5Mixer19PreDelayFormatterT9D1Ev");
#endif
extern "C" int __real___cxa_guard_acquire(long long *);
extern "C" void __real___cxa_guard_release(long long *);
extern "C" int __real___cxa_atexit(void (*)(void *), void *, void *);
extern "C" void __real__ZdlPv(void *);
extern "C" void realAdd(Core::Formatter *) asm(
    "__real__ZN4Core17FormatterRegistry3addEPNS_9FormatterE");
static bool armed, forceAcquireZero;
static long long *targetGuard;
static Core::Formatter *receiver;
static unsigned callbackCount, exitCount, receiverDeletes;
static const char *events[8];
static unsigned eventCount;
static void event(const char *text) {
  if (armed) {
    if (eventCount == 8)
      std::abort();
    events[eventCount++] = text;
  }
}
extern "C" int __wrap___cxa_guard_acquire(long long *guard) {
  if (armed && (!targetGuard || targetGuard == guard)) {
    targetGuard = guard;
    event("acquire");
    if (forceAcquireZero)
      return 0;
  }
  return __real___cxa_guard_acquire(guard);
}
extern "C" void __wrap___cxa_guard_release(long long *guard) {
  if (guard == targetGuard)
    event("release");
  __real___cxa_guard_release(guard);
}
struct Callback {
  void (*function)(void *);
  void *object;
};
static Callback callback;
static void proxy(void *argument) {
  auto *entry = static_cast<Callback *>(argument);
  if (entry->function != complete || entry->object != receiver)
    std::abort();
  entry->function(entry->object);
  ++exitCount;
}
extern "C" int __wrap___cxa_atexit(void (*function)(void *), void *object,
                                   void *dso) {
  if (armed && function == complete) {
    if (++callbackCount != 1)
      std::abort();
    callback = {function, object};
    event("atexit");
    return __real___cxa_atexit(proxy, &callback, dso);
  }
  return __real___cxa_atexit(function, object, dso);
}
extern "C" void wrappedAdd(Core::Formatter *object) asm(
    "__wrap__ZN4Core17FormatterRegistry3addEPNS_9FormatterE");
extern "C" void wrappedAdd(Core::Formatter *object) {
  if (armed) {
    if (receiver && receiver != object)
      std::abort();
    receiver = object;
    event("add");
    const bool saved = armed;
    armed = false;
    realAdd(object);
    armed = saved;
  } else
    realAdd(object);
}
extern "C" void __wrap__ZdlPv(void *object) {
  if (object == receiver)
    ++receiverDeletes;
  __real__ZdlPv(object);
}
static void report() {
  if (callbackCount != 1 || exitCount != 1 || receiverDeletes)
    std::_Exit(9);
  constexpr char message[] = "exit 1 0\n";
  if (::write(1, message, sizeof(message) - 1) != sizeof(message) - 1)
    std::_Exit(10);
}
int main() {
  std::atexit(report);
  const char *labels[] = {"cold", "warm1", "warm2", "acquire0"};
  for (unsigned index = 0; index != 4; ++index) {
    if (index == 3) {
      long long zero = 0;
      std::memcpy(targetGuard, &zero, sizeof(zero));
      forceAcquireZero = true;
    }
    eventCount = 0;
    armed = true;
    XmenFormatterInitializer::addClass<Target>();
    armed = false;
    if (index == 3) {
      long long one = 1;
      std::memcpy(targetGuard, &one, sizeof(one));
    }
    if (!receiver || std::strcmp(receiver->getName(), expectedName) ||
        Core::FormatterRegistry::find(expectedName) != receiver)
      return 1;
    char text[64]{};
    Core::Formatter::Data data{nullptr, text, 64, 1.f, nullptr};
    receiver->print(data);
#if FORMATTER_INIT_CLASS == 0
    if (std::strcmp(text, "R2"))
      return 2;
#else
    if (std::strcmp(text, "1.00") ||
        static_cast<Target *>(receiver)->sourcePortInitializationByte() != 8)
      return 2;
#endif
    std::cout << labels[index] << ' ';
    for (unsigned i = 0; i != eventCount; ++i) {
      if (i)
        std::cout << ',';
      std::cout << events[i];
    }
    std::cout << '\n';
  }
  std::cout.flush();
}
