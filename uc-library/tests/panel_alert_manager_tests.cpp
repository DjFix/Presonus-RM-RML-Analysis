#include "presonus/panel/alert_manager.hpp"
#include <array>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <new>
#include <type_traits>
#include <vector>
using Presonus::Panel::AlertManager;
using Presonus::Panel::IAlertDelegate;
using Access = presonus::panel::AlertManagerAccess;
static_assert(
    std::is_base_of_v<Core::Portable::Singleton<AlertManager>, AlertManager>);
static_assert(std::has_virtual_destructor_v<AlertManager>);
extern "C" void c1(AlertManager *) asm("_ZN8Presonus5Panel12AlertManagerC1Ev");
extern "C" void c2(AlertManager *) asm("_ZN8Presonus5Panel12AlertManagerC2Ev");
extern "C" void d1(AlertManager *) asm("_ZN8Presonus5Panel12AlertManagerD1Ev");
extern "C" void d0(AlertManager *) asm("_ZN8Presonus5Panel12AlertManagerD0Ev");
extern "C" void alert_invoke_native_destructor(AlertManager *, unsigned);
static AlertManager *tracked, *other;
static unsigned deletes, deleteCurrent;
static unsigned currentLabel() {
  return Access::current() == nullptr   ? 0
         : Access::current() == tracked ? 1
         : Access::current() == other   ? 2
                                        : 99;
}
void operator delete(void *p) noexcept {
  if (p && p == tracked) {
    ++deletes;
    deleteCurrent = currentLabel();
  }
  std::free(p);
}
void operator delete(void *p, std::size_t) noexcept { ::operator delete(p); }
static std::vector<std::array<unsigned, 8>> events;
static std::array<unsigned, 2> delegateTokens;
static std::array<char, 32> strings;
static std::array<const char *, 4> pointers{
    nullptr, strings.data(), strings.data() + 16, strings.data() + 1};
static IAlertDelegate *token(unsigned n) {
  return n ? reinterpret_cast<IAlertDelegate *>(&delegateTokens[n - 1])
           : nullptr;
}
static unsigned identity(IAlertDelegate *p) {
  return p == token(1) ? 1 : p == token(2) ? 2 : 99;
}
static unsigned pointer(const char *p) {
  for (unsigned i = 0; i < pointers.size(); ++i)
    if (p == pointers[i])
      return i;
  std::abort();
}
static unsigned bits(int n) {
  static_assert(sizeof(n) == 4);
  unsigned v;
  std::memcpy(&v, &n, 4);
  return v;
}
static int integer(unsigned n) {
  int v;
  std::memcpy(&v, &n, 4);
  return v;
}
static void alert(IAlertDelegate *p, int kind, const char *a, const char *b,
                  const char *c, int x, int y) {
  events.push_back({1, identity(p), bits(kind), pointer(a), pointer(b),
                    pointer(c), bits(x), bits(y)});
}
static void dismiss(IAlertDelegate *p) {
  events.push_back({2, identity(p), 0, 0, 0, 0, 0, 0});
}
static const unsigned patterns[8][4] = {
    {0, 0, 0, 0}, {1, 1, 1, 1}, {2, 2, 2, 2}, {1, 2, 0, 1},
    {2, 1, 2, 0}, {0, 1, 0, 2}, {1, 0, 2, 0}, {2, 0, 0, 1}};
static unsigned u32(const unsigned char *p) {
  return unsigned(p[0]) | (unsigned(p[1]) << 8) | (unsigned(p[2]) << 16) |
         (unsigned(p[3]) << 24);
}
static void append(std::vector<unsigned char> &out, unsigned n) {
  for (unsigned i = 0; i < 4; ++i)
    out.push_back(static_cast<unsigned char>(n >> (8 * i)));
}
static std::vector<unsigned char> run(const std::array<unsigned, 10> &args) {
  auto [ctor, dtor, current, pattern, kind, a, b, c, x, y] = args;
  AlertManager otherObject;
  other = &otherObject;
  tracked = static_cast<AlertManager *>(::operator new(sizeof(AlertManager)));
  std::memset(tracked, 0xa5, sizeof(AlertManager));
  Access::current(current == 0 ? nullptr : current == 1 ? tracked : other);
  if (ctor == 0)
    c1(tracked);
  else
    c2(tracked);
  if (Access::delegate(*tracked) != nullptr || currentLabel() != current)
    std::abort();
  // Linux native vtable inspection only; original ARM layout is not asserted.
  void **vtable;
  std::memcpy(&vtable, tracked, sizeof(vtable));
  if (vtable[0] != reinterpret_cast<void *>(&d1) ||
      vtable[1] != reinterpret_cast<void *>(&d0))
    std::abort();
  events.clear();
  deletes = 0;
  deleteCurrent = 0xffffffff;
  unsigned last = 0;
  for (unsigned delegate : patterns[pattern]) {
    tracked->setDelegate(token(delegate));
    last = delegate;
    if (Access::delegate(*tracked) != token(delegate))
      std::abort();
    tracked->doAlert(integer(kind), pointers[a], pointers[b], pointers[c],
                     integer(x), integer(y));
    tracked->dismissAlert();
  }
  alert_invoke_native_destructor(tracked, dtor);
  std::vector<unsigned char> out;
  for (unsigned n : {0u, current, last, currentLabel(), deletes, deleteCurrent,
                     static_cast<unsigned>(events.size())})
    append(out, n);
  for (auto &event : events)
    for (unsigned n : event)
      append(out, n);
  for (unsigned i = events.size(); i < 8; ++i)
    for (unsigned j = 0; j < 8; ++j)
      append(out, 0);
  Access::current(nullptr);
  void *memory = tracked;
  tracked = nullptr;
  if (dtor == 0)
    ::operator delete(memory);
  return out;
}
int main(int argc, char **argv) {
  if (argc != 2)
    return 2;
  presonus::panel::configureAlertDelegateSlots({alert, dismiss});
  events.reserve(8);
  std::ifstream f(argv[1], std::ios::binary);
  std::array<unsigned char, 12> header{};
  f.read(reinterpret_cast<char *>(header.data()), header.size());
  if (!f || std::memcmp(header.data(), "ALRTv001", 8))
    return 3;
  unsigned records = u32(header.data() + 8);
  for (unsigned index = 0; index < records; ++index) {
    std::array<unsigned char, 40> input{};
    std::array<unsigned char, 284> expected{};
    f.read(reinterpret_cast<char *>(input.data()), input.size());
    f.read(reinterpret_cast<char *>(expected.data()), expected.size());
    if (!f)
      return 4;
    std::array<unsigned, 10> args;
    for (unsigned i = 0; i < 10; ++i)
      args[i] = u32(input.data() + 4 * i);
    auto actual = run(args);
    if (actual.size() != expected.size() ||
        std::memcmp(actual.data(), expected.data(), expected.size())) {
      unsigned at = 0;
      while (at < expected.size() && actual[at] == expected[at])
        ++at;
      std::fprintf(stderr,
                   "Alert fixture%u ctor%u dtor%u current%u pattern%u byte%u "
                   "got%u want%u\n",
                   index, args[0], args[1], args[2], args[3], at, actual[at],
                   expected[at]);
      return 5;
    }
  }
  std::printf("%u original ARM AlertManager lifecycle/forward cases passed "
              "with actual CCL Singleton; native D1/D0 slots invoked through "
              "separate-TU dispatcher\n",
              records);
}
