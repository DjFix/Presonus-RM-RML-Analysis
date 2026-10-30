#ifdef NDEBUG
#undef NDEBUG
#endif
#include "presonus/mixer/ScaledTimeFormatter.hpp"
#include <cassert>
#include <cstring>
#include <fstream>
#include <iostream>
#include <new>
#include <string>
extern "C" void d1(void *) asm("_ZN8Presonus5Mixer19ScaledTimeFormatterD1Ev");
extern "C" void d0(void *) asm("_ZN8Presonus5Mixer19ScaledTimeFormatterD0Ev");
extern "C" void *__real__Znwm(std::size_t);
extern "C" void __real__ZdlPv(void *) noexcept;
extern "C" void __real__ZdlPvm(void *, std::size_t) noexcept;
namespace {
void *observed = nullptr;
bool capture = false, alive = false;
unsigned allocations = 0, sized = 0, unsized = 0;
} // namespace
extern "C" void *__wrap__Znwm(std::size_t n) {
  auto *p = __real__Znwm(n);
  if (capture) {
    assert(!alive);
    observed = p;
    alive = true;
    ++allocations;
  }
  return p;
}
extern "C" void __wrap__ZdlPv(void *p) noexcept {
  bool mine = alive && observed == p;
  __real__ZdlPv(p);
  if (mine) {
    alive = false;
    ++unsized;
  }
}
extern "C" void __wrap__ZdlPvm(void *p, std::size_t n) noexcept {
  bool mine = alive && observed == p;
  if (mine)
    assert(n == sizeof(Presonus::Mixer::ScaledTimeFormatter));
  __real__ZdlPvm(p, n);
  if (mine) {
    alive = false;
    ++sized;
  }
}
__attribute__((noinline)) void deleting(Core::Formatter *p) { delete p; }
unsigned word(float x) {
  unsigned w;
  std::memcpy(&w, &x, 4);
  return w;
}
float floating(unsigned w) {
  float x;
  std::memcpy(&x, &w, 4);
  return x;
}
int main(int argc, char **argv) {
  assert(argc == 2);
  std::ifstream input(argv[1]);
  assert(input);
  unsigned rows = 0;
  std::string role, operation, expected;
  unsigned value, size;
  Presonus::Mixer::ScaledTimeFormatter formatter(
      presonus::mixer::ScaledTimeFormatterPortTag{});
  const Core::Formatter *base = &formatter;
  while (input >> role >> operation >> value >> size >> expected) {
    char text[256];
    std::memset(text, 0xa5, sizeof text);
    std::memcpy(text, "SEED", 5);
    Core::Formatter::Data data{nullptr, text, static_cast<int>(size),
                               floating(value), nullptr};
    auto before = data;
    if (operation == "print")
      base->print(data);
    else
      assert(!base->scan(data));
    assert(data.object == before.object && data.string == before.string &&
           data.size == before.size && word(data.value) == value &&
           data.range == before.range);
    std::string hex;
    const char *digits = "0123456789abcdef";
    for (auto *p = reinterpret_cast<unsigned char *>(text); *p; ++p) {
      hex += digits[*p >> 4];
      hex += digits[*p & 15];
    }
    assert(hex == (expected == "-" ? "" : expected));
    assert(static_cast<unsigned char>(text[255]) == 0xa5);
    ++rows;
  }
  for (unsigned mode = 0; mode < 3; ++mode)
    for (unsigned i = 0; i < 8; ++i) {
      capture = true;
      auto *object = new Presonus::Mixer::ScaledTimeFormatter(
          presonus::mixer::ScaledTimeFormatterPortTag{});
      capture = false;
      auto **vt = *reinterpret_cast<void ***>(object);
      assert(vt[0] == reinterpret_cast<void *>(d1) &&
             vt[1] == reinterpret_cast<void *>(d0));
      if (mode == 0) {
        d1(object);
        assert(alive);
        ::operator delete(object);
      } else if (mode == 1)
        d0(object);
      else
        deleting(object);
      assert(!alive);
    }
  assert(allocations == 24 && sized == 16 && unsized == 8);
  std::cout << "{\"passed\":true,\"fixture_rows\":" << rows
            << ",\"real_lifetimes\":24,\"actual_sized_frees\":16,\"actual_"
               "unsized_frees\":8}"
            << std::endl;
}
