#include "presonus/mixer/DecayTimeFormatterT6.hpp"
#include "presonus/mixer/DecayTimeFormatterT7.hpp"
#include <array>
#include <cstddef>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <new>
#include <string_view>

namespace {
using Tagged = Presonus::Mixer::DecayTimeFormatterT7;
constexpr std::string_view names[] = {
    "decaytimeT6",
    "decaytimeT7",
    "decaytimeT8",
    "decaytimeT9",
};
constexpr std::size_t count = std::size(names);
std::array<const Core::Formatter *, count * 2> registrations{};
std::size_t observed = 0;
bool observing = false;
void *receiver = nullptr;
unsigned unsized = 0;
unsigned sized = 0;
void release(void *p, bool sizedForm) {
  if (p && p == receiver) {
    if (sizedForm)
      ++sized;
    else
      ++unsized;
  }
  std::free(p);
}
[[gnu::noinline]] void destroy(Core::Formatter *p) { delete p; }
} // namespace
void operator delete(void *p) noexcept { release(p, false); }
void operator delete(void *p, std::size_t) noexcept { release(p, true); }

extern "C" void
__real__ZN4Core17FormatterRegistry3addEPNS_9FormatterE(Core::Formatter *);
extern "C" void
__wrap__ZN4Core17FormatterRegistry3addEPNS_9FormatterE(Core::Formatter *value) {
  if (observing) {
    if (observed < registrations.size())
      registrations[observed] = value;
    ++observed;
  }
  __real__ZN4Core17FormatterRegistry3addEPNS_9FormatterE(value);
}

int main() {
  observing = true;
  presonus::mixer::registerAdditionalTaggedDecayTimeFormatters();
  presonus::mixer::registerAdditionalTaggedDecayTimeFormatters();
  observing = false;
  if (observed != registrations.size())
    return 2;
  for (std::size_t i = 0; i < count; ++i) {
    const auto *value = registrations[i];
    if (value != registrations[i + count] || names[i] != value->getName() ||
        Core::FormatterRegistry::find(value->getName()) != value)
      return 3;
  }
  for (const auto *prototype : registrations)
    std::cout << "registry " << prototype->getName() << '\n';
  const auto *tagged = Core::FormatterRegistry::find("decaytimeT7");
  Presonus::Mixer::DecayTimeFormatter base(presonus::mixer::FormatterPortTag{});
  char actual[32]{}, expected[32]{};
  for (float value : {9.125f, 10.f, 12.5f}) {
    Core::Formatter::Data a{nullptr, actual, sizeof(actual), value, nullptr};
    Core::Formatter::Data b{nullptr, expected, sizeof(expected), value,
                            nullptr};
    tagged->print(a);
    base.print(b);
    if (std::strcmp(actual, expected) || tagged->scan(a) != base.scan(b))
      return 4;
    auto *target = new Tagged;
    receiver = target;
    unsized = sized = 0;
    destroy(target);
    receiver = nullptr;
    if (sized || unsized != 1)
      return 5;
    alignas(Tagged) std::byte bytes[sizeof(Tagged)];
    auto *companion = new (bytes) Tagged;
    receiver = companion;
    unsized = sized = 0;
    companion->~Tagged();
    receiver = nullptr;
    if (unsized || sized)
      return 6;
    std::cout << "delete 1 complete 0\n";
  }
}
