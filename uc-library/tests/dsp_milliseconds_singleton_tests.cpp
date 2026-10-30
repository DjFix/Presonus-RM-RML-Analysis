#ifdef NDEBUG
#undef NDEBUG
#endif
#include "presonus/mixer_dsp/AdditionalFormatters.hpp"
#include <atomic>
#include <cassert>
#include <cstring>
#include <iostream>
#include <thread>
extern "C" void
millisecondsD1(void *) asm("_ZN8Presonus3Dsp21MillisecondsFormatterD1Ev");
extern "C" int __real___cxa_atexit(void (*)(void *), void *, void *);
namespace {
struct Callback {
  void (*function)(void *);
  void *object;
  void *dso;
};
Callback callbacks[2]{};
std::atomic<unsigned> callbackCount{0};
} // namespace
extern "C" int __wrap___cxa_atexit(void (*fn)(void *), void *object,
                                   void *dso) {
  if (fn == millisecondsD1) {
    unsigned i = callbackCount.fetch_add(1);
    assert(i < 2);
    callbacks[i] = {fn, object, dso};
  }
  return __real___cxa_atexit(fn, object, dso);
}
__attribute__((noinline)) bool dispatch(Core::Formatter *object, bool fine) {
  char text[128]{};
  Core::Formatter::Range range{0, 100};
  Core::Formatter::Data d{nullptr, text, 128, 1.25f, &range};
  object->print(d);
  if (std::strcmp(text, fine ? "1.250 ms" : "1.2 ms"))
    return false;
  std::strcpy(text, "2");
  return object->scan(d) && d.value == 2.f;
}
int main(int argc, char **argv) {
  using Presonus::Dsp::MillisecondsFormatter;
  assert(argc == 2);
  MillisecondsFormatter *ordinary = nullptr, *fine = nullptr;
  bool threaded = std::strcmp(argv[1], "threads") == 0;
  if (threaded) {
    std::thread workers[8];
    MillisecondsFormatter *results[8]{};
    std::atomic<bool> start{false};
    for (unsigned i = 0; i < 8; ++i)
      workers[i] = std::thread([&, i] {
        while (!start.load(std::memory_order_acquire))
          std::this_thread::yield();
        results[i] = MillisecondsFormatter::instance(i % 2);
      });
    start.store(true, std::memory_order_release);
    for (auto &t : workers)
      t.join();
    ordinary = results[0];
    fine = results[1];
    for (unsigned i = 0; i < 8; ++i)
      assert(results[i] == (i % 2 ? fine : ordinary));
  } else {
    bool first = std::strcmp(argv[1], "true") == 0;
    auto *p = MillisecondsFormatter::instance(first);
    ordinary = MillisecondsFormatter::instance(false);
    fine = MillisecondsFormatter::instance(true);
    assert(p == (first ? fine : ordinary));
  }
  assert(ordinary && fine && ordinary != fine);
  assert(std::strcmp(ordinary->getName(), "ms") == 0);
  assert(std::strcmp(fine->getName(), "ms.fine") == 0);
  assert(dispatch(ordinary, false) && dispatch(fine, true));
  assert(callbackCount.load() == 2);
  assert(callbacks[0].object == ordinary && callbacks[1].object == fine);
  assert(callbacks[0].function == millisecondsD1 &&
         callbacks[1].function == millisecondsD1);
  assert(callbacks[0].dso == callbacks[1].dso);
  for (unsigned i = 0; i < 1000; ++i) {
    assert(MillisecondsFormatter::instance(false) == ordinary);
    assert(MillisecondsFormatter::instance(true) == fine);
  }
  assert(callbackCount.load() == 2);
  std::cout << "{\"passed\":true,\"threaded\":" << (threaded ? "true" : "false")
            << ",\"retained_calls\":2000,\"actual_exit_registrations\":2,"
               "\"exact_D1_callback_targets\":true,\"callbacks_forwarded_to_"
               "CRT\":true,\"destructor_callback_execution_observed\":false}"
            << std::endl;
}
