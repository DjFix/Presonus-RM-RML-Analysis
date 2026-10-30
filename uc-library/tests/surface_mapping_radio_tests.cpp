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
class Map final : public M {
public:
  Map() : M(presonus::surface::MappingRouteInit{}) {}
  void own(Core::Portable::Parameter *p) { paramList.add(p); }
  void paramChanged(Core::Portable::Parameter *, int) override {}
  void onIdle() override { std::abort(); }
  int getModifiers() const override { std::abort(); }
  int getBankScrollingOffset() const override { std::abort(); }
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
int main(int argc, char **argv) {
  if (argc != 2)
    return 2;
  std::ifstream in(argv[1]);
  std::string op;
  int selected, first, last;
  unsigned edit, mask, count, wantedResult, checked = 0;
  std::array<unsigned, 3> values{}, wantedValues{};
  while (in >> op >> selected >> first >> last >> edit >> mask >> values[0] >>
         values[1] >> values[2] >> wantedResult >> wantedValues[0] >>
         wantedValues[1] >> wantedValues[2] >> count) {
    std::vector<std::string> wanted(count);
    for (auto &s : wanted)
      in >> s;
    std::array<Core::Portable::ParamInfo, 4> definitions{};
    Map map;
    std::array<Param *, 3> parameters{};
    for (int i = 0; i < 4; ++i) {
      auto &info = definitions[i];
      info.type = Core::Portable::ParamInfo::kFloat;
      info.tag = i == 3 ? 99 : i;
      info.minValue = -2;
      info.maxValue = 2;
      info.defaultValue = i == 3 ? 0.f : floating(values[i]);
      if (i == 3) {
        map.own(new Core::Portable::NumericParam(info));
      } else if (mask & (1U << i)) {
        parameters[i] = new Param(info);
        parameters[i]->tag = i;
        map.own(parameters[i]);
      }
    }
    events.clear();
    capture = true;
    unsigned result = 0xffffffff;
    if (op == "S")
      map.setRadioGroup(selected, first, last, edit != 0);
    else if (op == "T") {
      Presonus::IMappingController &controller = map;
      controller.setRadioGroup(selected, first, last, edit != 0);
    } else if (op == "G")
      result = static_cast<unsigned>(map.getRadioValue(first, last));
    else {
      const Presonus::IMappingController &controller = map;
      result = static_cast<unsigned>(controller.getRadioValue(first, last));
    }
    capture = false;
    auto after = values;
    for (int i = 0; i < 3; ++i)
      if (parameters[i])
        after[i] = bits(parameters[i]->NumericParam::getValue());
    if (result != wantedResult || after != wantedValues || events != wanted) {
      std::cerr << "case " << checked << ' ' << op << " mismatch\n";
      return 3;
    }
    ++checked;
  }
  {
    Map empty;
    empty.setRadioGroup(0, 0, 2, false);
    if (empty.getRadioValue(0, 2) != -1)
      return 4;
  }
  std::cout << "{\"passed\":true,\"cases\":" << checked
            << ",\"empty_list_source_guard\":true}\n";
}
