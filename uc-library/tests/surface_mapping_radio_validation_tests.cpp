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
  void updateConnections() override { std::abort(); }
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
  std::string op;
  int tag, first, last, off, handler, pattern;
  unsigned value, count, checked = 0;
  const std::array<int, 10> tags = {0, 1, 2, 6, 13, 20, 33, 34, 35, 37};
  while (in >> op >> tag >> value >> first >> last >> off >> handler >>
         pattern) {
    std::array<unsigned, 10> wanted{};
    for (auto &v : wanted)
      in >> v;
    in >> count;
    std::vector<std::string> want(count);
    for (auto &v : want)
      in >> v;
    std::array<Core::Portable::ParamInfo, 11> infos{};
    Map map;
    std::array<Param *, 10> params{};
    for (int i = 0; i < 11; ++i) {
      auto &v = infos[i];
      v.type = Core::Portable::ParamInfo::kFloat;
      v.tag = i == 10 ? tag : tags[i];
      v.minValue = -2;
      v.maxValue = 2;
      v.defaultValue =
          i == 10 ? floating(value) : (pattern ? (i % 2 ? 1.f : .25f) : 0.f);
      if (i < 10) {
        params[i] = new Param(v);
        params[i]->tag = tags[i];
        map.own(params[i]);
      }
    }
    Param event(infos[10]);
    event.event = true;
    Handler h;
    h.handled = handler == 2;
    presonus::surface::MappingInputAccess::bind(map, nullptr, nullptr,
                                                handler ? &h : nullptr);
    events.clear();
    capture = true;
    if (op == "G")
      map.verifyRadioGroup(&event, first, last,
                           static_cast<M::RadioOffBehaviour>(off));
    else
      map.verifyRadioParam(&event);
    capture = false;
    std::array<unsigned, 10> after{};
    for (int i = 0; i < 10; ++i)
      after[i] = bits(params[i]->NumericParam::getValue());
    if (events != want || after != wanted) {
      std::cerr << "case " << checked << " mismatch\n";
      for (auto &v : events)
        std::cerr << v << " ";
      std::cerr << "\nexpected ";
      for (auto &v : want)
        std::cerr << v << " ";
      return 3;
    }
    ++checked;
  }
  std::cout << "{\"passed\":true,\"cases\":" << checked << "}\n";
}
