#include "presonus/dsp/OMAPTargetHandler.hpp"

#include <array>
#include <cstring>
#include <iostream>
#include <string>

using Presonus::Dsp::OMAPTargetHandler;

namespace {
struct TestProperty : Core::Property {
  explicit TestProperty(unsigned seed)
      : Property(static_cast<Core::PropertyType>(seed), sizeof(TestProperty)),
        payload{seed, seed ^ 0x5aa55aa5, ~seed} {}
  std::array<unsigned, 3> payload;
};

[[gnu::noinline]] void invokeVirtual(OMAPTargetHandler &handler,
                                     Core::Property &property) {
  handler.getProperty(property);
}
} // namespace

int main() {
  std::string route;
  unsigned seed;
  while (std::cin >> route >> seed) {
    OMAPTargetHandler handler(OMAPTargetHandler::SourcePortConstruction{});
    std::array<unsigned char, sizeof(OMAPTargetHandler)> receiver{};
    std::memcpy(receiver.data(), &handler, receiver.size());
    TestProperty property(seed);
    const auto before = property;
    if (route == "ordinary")
      handler.OMAPTargetHandler::getProperty(property);
    else if (route == "vtable")
      invokeVirtual(handler, property);
    else
      return 1;
    const bool unchanged =
        std::memcmp(receiver.data(), &handler, receiver.size()) == 0 &&
        property.type == before.type && property.size == before.size &&
        property.payload == before.payload;
    std::cout << route << ' ' << seed << ' ' << unchanged << '\n';
  }
}
