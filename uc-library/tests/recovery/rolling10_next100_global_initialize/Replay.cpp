#include "presonus/mixer/GlobalComponent.hpp"
#include <array>
#include <cstring>
#include <iostream>
#include <string>
#include <vector>
using namespace Core::Portable;
static std::uint32_t bits(float value) {
  std::uint32_t b;
  std::memcpy(&b, &value, 4);
  return b;
}
static float value(std::uint32_t bits) {
  float v;
  std::memcpy(&v, &bits, 4);
  return v;
}
struct Observer : ParamObserverBase {
  Parameter *source, *destination;
  std::vector<std::array<int, 2>> events;
  Observer(Parameter *s, Parameter *d) : source(s), destination(d) {}
  void paramChanged(Parameter *p, int message) override {
    events.push_back({p == source ? 1 : 2, message});
  }
};
int main(int argc, char **argv) {
  const bool provider = argc > 1 && std::string(argv[1]) == "--provider";
  int mask, alias, repeats;
  std::uint32_t sourceBits, destinationBits;
  while (std::cin >> mask >> alias >> sourceBits >> destinationBits >>
         repeats) {
    ParamInfo info{};
    info.type = ParamInfo::kFloat;
    info.minValue = -8;
    info.maxValue = 8;
    NumericParam source(info), other(info);
    source.setValueFast(value(sourceBits));
    other.setValueFast(value(destinationBits));
    NumericParam *destination = alias ? &source : &other;
    Observer observer(&source, destination);
    source.addObserver(&observer);
    if (destination != &source)
      destination->addObserver(&observer);
    destination->setController(&observer);
    {
      Presonus::Mixer::GlobalComponent object;
      object.bindHighDefParameters(mask & 1 ? &source : nullptr,
                                   mask & 2 ? destination : nullptr);
      for (int i = 0; i < repeats; ++i) {
        if (provider)
          object.updateHighDef();
        else {
#ifndef PROVIDER_ONLY
          object.initalize();
#endif
        }
      }
      std::cout << bits(source.getValue()) << ' ' << bits(other.getValue())
                << ' ' << observer.events.size();
      for (auto event : observer.events)
        std::cout << ' ' << event[0] << ' ' << event[1];
      std::cout << '\n';
    }
    // All descriptors, observer and borrowed parameters outlive actual Global
    // CCL base cleanup. No original constructor/destructor credit is claimed.
    destination->setController(nullptr);
    source.removeObserver(&observer);
    if (destination != &source)
      destination->removeObserver(&observer);
  }
}
