#include "presonus/PanControl.hpp"
#include <cstdint>
#include <cstring>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>

static std::vector<std::string> events;
static const Core::Portable::ParamInfo info =
    PARAM_FLOAT(1, "test", -10, 10, 0, 1, nullptr, 0, 0, 0);
class TestParameter : public Core::Portable::NumericParam {
public:
  TestParameter() : NumericParam(::info) {}
  float input = 0;
  bool originalPresent = false;
  std::string text;
  float getValue() const override {
    events.push_back("value");
    return input;
  }
  void toString(char *out, int size) const override {
    events.push_back("string");
    std::snprintf(out, size, "%s", text.c_str());
  }
  Core::Portable::Parameter *getOriginal() override {
    events.push_back("original");
    return originalPresent ? this : nullptr;
  }
};
class TestPan : public Presonus::PanControl {
public:
  using Presonus::PanControl::invalidate;
  void invalidate(Core::RectRef) override { events.push_back("invalidate"); }
};
int main() {
  std::string line;
  while (std::getline(std::cin, line)) {
    std::istringstream in(line);
    int kind, present, hasExplicit, msg, changed, fallback;
    uint32_t bits, explicitBits;
    std::array<int, 5> ids;
    std::string label;
    in >> kind >> bits >> present >> hasExplicit >> explicitBits >> msg >>
        changed >> fallback;
    for (auto &id : ids)
      in >> id;
    in >> std::quoted(label);
    if (!in)
      return 2;
    TestParameter parameter, side;
    std::memcpy(&parameter.input, &bits, 4);
    std::memcpy(&side.input, &explicitBits, 4);
    parameter.text = label;
    parameter.originalPresent = fallback;
    TestParameter baseParameter;
    TestPan pan;
    pan.setParameter(&baseParameter);
    std::array<Core::Portable::Parameter *, 5> binding{};
    std::array<TestParameter, 10> pool;
    if (kind == 1 || kind == 2)
      binding[kind == 1 ? 0 : 1] = present ? &parameter : nullptr;
    if (kind == 3 || kind == 5) {
      binding[2] = present ? &parameter : nullptr;
      binding[3] = hasExplicit ? &side : nullptr;
    }
    if (kind == 4)
      for (int i = 0; i < 5; ++i)
        binding[i] = ids[i] ? &pool[ids[i]] : nullptr;
    pan.bindPanParameters(binding);
    events.clear();
    uint32_t result = 0;
    if (kind == 1)
      result = pan.isStereo();
    if (kind == 2)
      result = pan.isLinked();
    if (kind == 5)
      result = pan.isRightSideOfLink();
    if (kind == 3) {
      float input, output;
      std::memcpy(&input, &bits, 4);
      output = pan.computeLinkedPanValue(input);
      std::memcpy(&result, &output, 4);
    }
    if (kind == 4)
      pan.paramChanged(changed ? &pool[changed] : nullptr, msg);
    std::cout << result;
    for (auto *p : pan.panParameters()) {
      int id = 0;
      if (kind == 4)
        for (int n = 1; n < 10; ++n)
          if (p == &pool[n])
            id = n;
      std::cout << ' ' << id;
    }
    std::cout << ' ';
    for (const auto &event : events)
      std::cout << event << ',';
    std::cout << '\n';
  }
}
