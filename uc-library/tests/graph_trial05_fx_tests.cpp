#include "presonus/mixer/FXComponent.hpp"
#include <cstring>
#include <iostream>
#include <string>
#include <vector>
using namespace Core::Portable;
static std::uint32_t bits(float v) {
  std::uint32_t b;
  std::memcpy(&b, &v, 4);
  return b;
}
static float value(std::uint32_t b) {
  float v;
  std::memcpy(&v, &b, 4);
  return v;
}
static const ParamInfo info =
    PARAM_FLOAT(1, "fx", -1e30f, 1e30f, 0, 1, nullptr, nullptr, 0, 0);
struct ParameterProbe : NumericParam {
  std::string name;
  std::vector<std::string> &trace;
  ParameterProbe(std::string n, std::vector<std::string> &t, float v)
      : NumericParam(::info), name(n), trace(t) {
    value = v;
  }
  ParamValue getValue() const override {
    trace.push_back("get:" + name);
    return NumericParam::getValue();
  }
  void setValue(ParamValue v, bool edit) override {
    trace.push_back("set:" + name + ":" + std::to_string(bits(v)) + ":" +
                    std::to_string(edit));
    NumericParam::setValue(v, edit);
  }
};
struct AppProbe : presonus::mixer_fx::AppBoundary {
  std::vector<std::string> &trace;
  presonus::mixer_fx::State *state = nullptr;
  std::uint32_t number;
  AppProbe(std::vector<std::string> &t, std::uint32_t n)
      : trace(t), number(n) {}
  void setControllerDirty() override {
    trace.push_back("dirty:" + std::to_string(state->dirty));
  }
  std::uint32_t getTypeNumber() override {
    trace.push_back("type-number");
    return number;
  }
  void updateTypeName() override { trace.push_back("update-name"); }
  void handleTypeChange(bool edit) override {
    trace.push_back("type-change:" + std::to_string(edit));
  }
};
int main(int argc, char **argv) {
  if (argc != 9)
    return 2;
  int op = std::stoi(argv[1]), count = std::stoi(argv[3]),
      wanted = std::stoi(argv[4]);
  std::uint32_t b = std::stoul(argv[2]), number = std::stoul(argv[8]);
  std::vector<std::string> trace;
  Component owner("fx");
  static const ParamInfo infos[] = {
      PARAM_FLOAT(1, "p0", -1e30f, 1e30f, 0, 1, nullptr, nullptr, 0, 0),
      PARAM_FLOAT(2, "p1", -1e30f, 1e30f, 0, 1, nullptr, nullptr, 0, 0),
      PARAM_FLOAT(3, "p2", -1e30f, 1e30f, 0, 1, nullptr, nullptr, 0, 0),
      PARAM_FLOAT(4, "p3", -1e30f, 1e30f, 0, 1, nullptr, nullptr, 0, 0)};
  owner.addParameters(infos, count);
  ParameterProbe type("type", trace, 0), recalled("recalled", trace, value(b));
  AppProbe app(trace, number);
  presonus::mixer_fx::State state{owner,
                                  type,
                                  recalled,
                                  app,
                                  std::stoi(argv[5]) != 0,
                                  std::stoi(argv[6]) != 0};
  app.state = &state;
  Presonus::Mixer::FXComponent fx(state);
  std::uint32_t result = 0;
  switch (op) {
  case 1:
    fx.setFxDirty();
    break;
  case 2:
    result = bits(fx.mapValues(wanted < 0 ? nullptr : &recalled));
    break;
  case 3:
    result = fx.recallFxType();
    break;
  case 4:
    result = fx.isChildParameter(wanted < 0 ? recalled
                                            : *owner.getParameterAt(wanted));
    break;
  case 5:
    result = fx.refreshFx(std::stoi(argv[7]) != 0);
    break;
  default:
    return 2;
  }
  std::cout << result << " " << state.dirty << " " << state.recalledTypePending
            << "|";
  for (auto &s : trace)
    std::cout << s << ";";
  std::cout << "\n";
}
