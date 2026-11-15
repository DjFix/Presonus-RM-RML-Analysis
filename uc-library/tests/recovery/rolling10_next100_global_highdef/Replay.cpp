#include "presonus/mixer/GlobalComponent.hpp"
#include <cstring>
#include <iostream>
#include <utility>
#include <vector>
using namespace Core::Portable;
BEGIN_PARAMINFO(info)
PARAM_FLOAT_(17, "numeric", -100, 100, 0, .001, "", "", 0, 0, "Numeric",
             nullptr)
END_PARAMINFO
static float number(unsigned bits) {
  float f;
  std::memcpy(&f, &bits, 4);
  return f;
}
static unsigned bits(float f) {
  unsigned b;
  std::memcpy(&b, &f, 4);
  return b;
}
struct Observer : ParamObserverBase {
  std::vector<std::pair<int, int>> events;
  void paramChanged(Parameter *p, int msg) override {
    events.emplace_back(p->getTag(), msg);
  }
};
int main(int argc, char **) {
  bool inventory = argc > 1;
  unsigned input;
  int mode;
  while (std::cin >> input >> mode) {
    NumericParam source(info[0]), destination(info[0]),
        referenceSource(info[0]), referenceDestination(info[0]);
    Observer actual, expected;
    source.setValueFast(number(input));
    referenceSource.setValueFast(number(input));
    destination.setValueFast(mode % 2 ? 1.f : -3.f);
    referenceDestination.setValueFast(mode % 2 ? 1.f : -3.f);
    auto *src = mode == 1 ? nullptr : &source;
    auto *dst = mode == 2 ? nullptr : mode == 3 ? &source : &destination;
    auto *refdst = mode == 2   ? nullptr
                   : mode == 3 ? &referenceSource
                               : &referenceDestination;
    if (inventory) {
      std::cout << bits(source.getValue()) << ' ' << mode << ' ' << bool(src)
                << ' ' << bool(dst) << ' ' << (src == dst) << ' '
                << bits(dst ? dst->getValue() : 0.f) << '\n';
      continue;
    }
    int calls;
    unsigned setbits;
    int edit;
    std::cin >> calls >> setbits >> edit;
    if (dst)
      dst->setController(&actual);
    if (refdst)
      refdst->setController(&expected);
    if (calls) {
      if (!refdst || !src || edit != 1)
        return 2;
      refdst->setValue(number(setbits), true);
    }
    Presonus::Mixer::GlobalComponent owner;
    owner.bindHighDefParameters(src, dst);
    owner.updateHighDef();
    if (bits(source.getValue()) != bits(referenceSource.getValue()) ||
        bits(destination.getValue()) != bits(referenceDestination.getValue()) ||
        actual.events != expected.events)
      return 3;
    std::cout << bits(source.getValue()) << ' ' << bits(destination.getValue())
              << ' ' << actual.events.size();
    for (auto [tag, msg] : actual.events)
      std::cout << ' ' << tag << ' ' << msg;
    std::cout << '\n';
    source.setController(nullptr);
    destination.setController(nullptr);
    referenceSource.setController(nullptr);
    referenceDestination.setController(nullptr);
  }
}
