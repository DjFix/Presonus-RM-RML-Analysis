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
  bool event = false;
  float getValue() const override {
    if (!inside)
      emit(event ? "get:event" : "get:" + std::to_string(tag));
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
class Handler final : public Presonus::MixerAssignmentHandler {
public:
  bool handled = false;
  const char *getName() const override { std::abort(); }
  void updateConnections() override { emit("update"); }
  void onMappingParamChanged(Core::Portable::Parameter *) override {
    std::abort();
  }
  bool getParamFocusInfo(FocusInfo &, Core::Portable::Parameter *) override {
    std::abort();
  }
  bool handleMappingRadioGroup(Core::Portable::Parameter *) override {
    emit("handler");
    return handled;
  }
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
  std::string operation;
  unsigned enabled, handler, checked = 0, count;
  while (in >> operation >> enabled >> handler) {
    std::array<unsigned, 4> values{}, wanted{};
    for (auto &v : values)
      in >> v;
    for (auto &v : wanted)
      in >> v;
    in >> count;
    std::vector<std::string> expected(count);
    for (auto &v : expected)
      in >> v;
    std::array<Core::Portable::ParamInfo, 4> infos{};
    Map map;
    std::array<Param *, 4> params{};
    for (int i = 0; i < 4; ++i) {
      auto &info = infos[i];
      info.type = Core::Portable::ParamInfo::kFloat;
      info.tag = 34 + i;
      info.minValue = -2;
      info.maxValue = 2;
      info.defaultValue = floating(values[i]);
      params[i] = new Param(info);
      params[i]->tag = 34 + i;
      map.own(params[i]);
    }
    Handler adapter;
    presonus::surface::MappingInputAccess::bind(map, nullptr, nullptr,
                                                handler ? &adapter : nullptr);
    events.clear();
    capture = true;
    if (operation == "G")
      map.setGeqMode(enabled != 0);
    else if (operation == "P")
      map.setPreampsMeterMode(enabled != 0);
    else
      return 4;
    capture = false;
    std::array<unsigned, 4> after{};
    for (int i = 0; i < 4; ++i)
      after[i] = bits(params[i]->NumericParam::getValue());
    if (after != wanted || events != expected) {
      std::cerr << "case " << checked << " mismatch\n";
      return 3;
    }
    ++checked;
  }
  std::cout << "{\"passed\":true,\"cases\":" << checked << "}\n";
}
