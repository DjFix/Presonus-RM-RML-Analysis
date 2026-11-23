#include "presonus/mixer/DecayTimeFormatterT1.hpp"
#include "presonus/mixer/DecayTimeFormatterT4.hpp"
#include <cstddef>
#include <cstdlib>
#include <cstring>
#include <iostream>

namespace {
void *tracked = nullptr;
unsigned releases = 0;
unsigned sizedReleases = 0;
void release(void *address, bool sized) {
  if (address == tracked && tracked != nullptr) {
    if (sized)
      ++sizedReleases;
    else
      ++releases;
  }
  std::free(address);
}
} // namespace
void operator delete(void *address) noexcept { release(address, false); }
void operator delete(void *address, std::size_t) noexcept {
  release(address, true);
}

namespace {
[[gnu::noinline]] void destroy(Core::Formatter *formatter) { delete formatter; }
} // namespace
int main() {
  presonus::mixer::registerTaggedDecayTimeFormatters();
  const auto *formatter = Core::FormatterRegistry::find("decaytimeT4");
  if (!formatter || std::strcmp(formatter->getName(), "decaytimeT4"))
    return 2;
  presonus::mixer::registerTaggedDecayTimeFormatters();
  if (Core::FormatterRegistry::find("decaytimeT4") != formatter)
    return 3;
  char result[32] = {};
  Core::Formatter::Data data{nullptr, result, sizeof(result), 12.5f, nullptr};
  formatter->print(data);
  if (std::strcmp(result, "12.50") || formatter->scan(data))
    return 4;
  for (int n = 0; n < 3; ++n) {
    auto *receiver = new Presonus::Mixer::DecayTimeFormatterT4;
    releases = 0;
    sizedReleases = 0;
    tracked = receiver;
    destroy(receiver);
    tracked = nullptr;
    if (sizedReleases != 0)
      return 6;
    std::cout << "delete " << releases << '\n';
  }
}
