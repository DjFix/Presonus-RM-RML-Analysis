#include "presonus/surface/mapping_input_routes.hpp"
#include <array>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <iostream>
#include <string>
#include <vector>
using M = Presonus::Surface::MappingComponent;
namespace {
bool capture = false;
std::vector<std::string> events;
void emit(std::string s) {
  if (capture)
    events.push_back(s);
}
float floating(unsigned x) {
  float f;
  std::memcpy(&f, &x, 4);
  return f;
}
unsigned bits(float f) {
  unsigned x;
  std::memcpy(&x, &f, 4);
  return x;
}
class Param : public Core::Portable::NumericParam {
  mutable bool inside = false;

public:
  using NumericParam::NumericParam;
  int tag = 0;
  float getValue() const override {
    if (!inside)
      emit("get:" + std::to_string(tag));
    return NumericParam::getValue();
  }
  void setValue(float v, bool edit) override {
    emit("set:" + std::to_string(tag) + ":" + std::to_string(bits(v)) + ":" +
         std::to_string(edit));
    inside = true;
    NumericParam::setValue(v, edit);
    inside = false;
  }
};
class Map : public M {
public:
  Map() : M(presonus::surface::MappingRouteInit{}) {}
  void own(Core::Portable::Parameter *p) { paramList.add(p); }
  void paramChanged(Core::Portable::Parameter *, int) override {}
  void onIdle() override { std::abort(); }
  int getModifiers() const override { std::abort(); }
  Core::Portable::Parameter *getParamByTag(int) const override { std::abort(); }
  Core::Portable::Parameter *getMainScreenParamByTag(int) const override {
    std::abort();
  }
  bool isDisplayEncoderLocked() const override { std::abort(); }
  bool areFadersLockedToMainMix() const override { std::abort(); }
  void onSelectedChannelChanged() override { std::abort(); }
  void selectedChannelUpdated() override { std::abort(); }
  void onDeviceDisconnected() override { std::abort(); }
};
} // namespace
extern "C" Core::Portable::Parameter *
realByTag(const Core::Portable::Component *,
          int) asm("__real__ZNK4Core8Portable9Component17getParameterByTagEi");
extern "C" Core::Portable::Parameter *wrapByTag(
    const Core::Portable::Component *c,
    int tag) asm("__wrap__ZNK4Core8Portable9Component17getParameterByTagEi");
extern "C" Core::Portable::Parameter *
wrapByTag(const Core::Portable::Component *c, int tag) {
  emit("lookup:" + std::to_string(static_cast<unsigned>(tag)));
  return realByTag(c, tag);
}

class Override final : public Map {
public:
  int value = 0;
  mutable int calls = 0;
  int getRadioValue(int first, int last) const override {
    if (first != 0 || last != 3)
      std::abort();
    ++calls;
    return value;
  }
};
int main() {
  char mode;
  int value;
  unsigned expected;
  unsigned cases = 0;
  while (std::cin >> mode >> value >> expected) {
    unsigned actual;
    if (mode == 'O') {
      Override map;
      map.value = value;
      actual = static_cast<unsigned>(map.getBankScrollingOffset());
      if (map.calls != 1)
        return 4;
    } else {
      std::array<Core::Portable::ParamInfo, 4> infos{};
      Map map;
      for (int tag = 0; tag < 4; ++tag) {
        auto &info = infos[tag];
        info.type = Core::Portable::ParamInfo::kFloat;
        info.tag = tag;
        info.minValue = -2;
        info.maxValue = 2;
        info.defaultValue = (value & (1 << tag)) ? 1.f : 0.f;
        map.own(new Core::Portable::NumericParam(info));
      }
      actual = static_cast<unsigned>(map.getBankScrollingOffset());
    }
    if (actual != expected) {
      std::cerr << mode << ' ' << value << ' ' << actual << ' ' << expected;
      return 3;
    }
    ++cases;
  }
  Map empty;
  if (empty.getBankScrollingOffset() != 0)
    return 5;
  std::cout << cases
            << " ARM cases; actual CCL NumericParam and radio routes; "
               "empty-list guard\n";
}
