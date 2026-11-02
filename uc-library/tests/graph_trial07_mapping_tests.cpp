#include "presonus/dice/packet_services.hpp"
#include "presonus/surface/MappingComponent.hpp"
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <deque>
#include <iomanip>
#include <iostream>
#include <map>
#include <string>
#include <vector>
namespace presonus::dice {
std::int64_t packetClockRawTicks() { return 1000000000000LL; }
} // namespace presonus::dice
namespace {
using Core::Portable::NumericParam;
using Core::Portable::Parameter;
using Core::Portable::ParamInfo;
using presonus::mapping::Access;
std::vector<std::string> trace;
bool recording = false;
void emit(const std::string &s) {
  if (recording)
    trace.push_back(s);
}
std::string str(const char *p) { return p ? p : "-"; }
std::string tag(Parameter *p) { return std::to_string(p ? p->getTag() : -1); }
struct Param : NumericParam {
  using NumericParam::NumericParam;
  void enable(bool v) override {
    emit("enable " + tag(this) + " " + std::to_string(v));
    NumericParam::enable(v);
  }
  void setValue(float v, bool edit = false) override {
    emit("set " + tag(this) + " " + std::to_string(static_cast<int>(v)) + " " +
         std::to_string(edit));
    NumericParam::setValue(v, edit);
  }
  void resetValue(bool edit = false) override {
    const bool old = recording;
    emit("reset " + tag(this) + " " + std::to_string(edit));
    recording = false;
    NumericParam::resetValue(edit);
    recording = old;
  }
};
struct Handler : presonus::mapping::Handler {
  int role;
  explicit Handler(int r) : role(r) {}
  void call(int slot, Parameter *p = nullptr) {
    emit("handler " + std::to_string(role) + " " + std::to_string(slot) + " " +
         (slot == 40 ? tag(p) : "-"));
  }
  void selectedChanged() override { call(60); }
  void defaultMapping() override { call(16); }
  void displayAssignment() override { call(36); }
  void modifiersChanged() override { call(20); }
  void idle() override { call(24); }
  void mappingParamChanged(Parameter *p) override { call(40, p); }
};
struct Mapping : Presonus::Surface::MappingComponent {
  Mapping() : MappingComponent(presonus::surface::MappingRouteInit{}) {}
  int getBankScrollingOffset() const override { return 0; }
  Parameter *getParamByTag(int v) const override {
    return getParameterByTag(v);
  }
  Parameter *getMainScreenParamByTag(int) const override { return nullptr; }
  bool isDisplayEncoderLocked() const override { return false; }
  bool areFadersLockedToMainMix() const override { return false; }
  void selectedChannelUpdated() override {}
  void add(Parameter *p) { paramList.add(p); }
};
struct Bindings : presonus::mapping::Bindings {
  Core::Portable::Component *screen = nullptr;
  void connect(const char *n, Parameter *p, const char *u,
               bool b) const override {
    emit("connect " + str(n) + " " + tag(p) + " " + str(u) + " " +
         std::to_string(b));
  }
  void color(const char *n, const char *c, bool b) const override {
    emit("color " + str(n) + " " + str(c) + " " + std::to_string(b));
  }
  void disconnectMixerParams() const override { emit("disconnect"); }
  void blink(const char *n, const char *b) const override {
    emit("blink " + str(n) + " " + str(b));
  }
  Core::Portable::Component *
  mainScreen(Core::Portable::Component *) const override {
    return screen;
  }
  void updateDAW(bool b) const override { emit("daw " + std::to_string(b)); }
};
} // namespace
// Test-only GNU ld wrapper captures the original external-call boundary.
// Production calls the existing canonical helper directly; its real behavior
// is independently exercised by surface_mapping_radio_validation_tests.
extern "C" void
__wrap__ZN8Presonus7Surface16MappingComponent16verifyRadioParamEPN4Core8Portable9ParameterE(
    Presonus::Surface::MappingComponent *, Core::Portable::Parameter *p) {
  emit("verify " + tag(p));
}
int main(int argc, char **argv) {
  if (argc != 18)
    return 2;
  std::map<std::string, int> cfg;
  const char *keys[] = {"handlers", "present", "color", "tag",  "mode",  "mods",
                        "value",    "msg",     "root",  "same", "blink", "ex0",
                        "long0",    "was0",    "ex1",   "long1"};
  const int target = std::atoi(argv[1]);
  for (int i = 0; i < 16; ++i)
    cfg[keys[i]] = std::atoi(argv[i + 2]);
  std::deque<ParamInfo> infos;
  Mapping mapping;
  std::map<int, Param *> params;
  for (int ordinal = 0; ordinal < 81; ++ordinal) {
    const int n = ordinal <= 40 ? ordinal : 10000 + ordinal - 41;
    const ParamInfo info =
        PARAM_FLOAT(n, "fixture", -100, 100, 0, 1, nullptr, nullptr, 0, 0);
    infos.push_back(info);
    auto *p = new Param(infos.back());
    mapping.add(p);
    params[n] = p;
    int v = cfg["value"];
    if (n == 8 || n == 9 || n == 10)
      v = (cfg["mods"] & (n == 9 ? 1 : n == 10 ? 2 : 4)) != 0;
    p->setValue(static_cast<float>(v));
  }
  // For missing-parameter cases, use a separate empty source Component port.
  Mapping empty;
  auto &m = cfg["present"] ? mapping : empty;
  Bindings bindings;
  Handler h1(1), h2(2), h3(3);
  Access::bind(m, bindings, cfg["handlers"] & 1 ? &h1 : nullptr,
               cfg["handlers"] & 2 ? &h2 : nullptr,
               cfg["handlers"] & 4 ? &h3 : nullptr,
               cfg["same"] ? (cfg["handlers"] & 2 ? &h2 : nullptr) : nullptr);
  if (cfg["root"] && cfg["present"])
    bindings.screen = &mapping;
  auto timer = [&](Presonus::DelayTimer &t, int k) {
    presonus::timing::DelayTimerAccess::set(
        t, {1000000 - (cfg["long" + std::to_string(k)] ? 2000 : 0), 1000,
            cfg["was" + std::to_string(k)] ? 2000 : 0, .001f,
            cfg["ex" + std::to_string(k)] != 0});
  };
  timer(Access::hold(m), 0);
  timer(Access::blink(m), 1);
  Access::blinkState(m) = cfg["blink"] != 0;
  recording = true;
  int result = 0;
  switch (target) {
  case 1:
    m.onSelectedChannelChanged();
    break;
  case 2:
    m.connectControl(cfg["tag"], "fixture_control",
                     cfg["color"] ? "fixture_color" : nullptr);
    break;
  case 3:
    m.onDeviceDisconnected();
    break;
  case 4:
    m.setDefaultMapping();
    break;
  case 5:
    m.updateDisplayEncoderAssignment();
    break;
  case 6:
    m.paramChanged(params.at(cfg["tag"]), cfg["msg"]);
    break;
  case 7:
    m.onIdle();
    break;
  case 8:
    m.onFootswitchModeChanged(cfg["mode"]);
    break;
  case 9:
    result = m.getModifiers();
    break;
  case 10:
    m.connectControls();
    break;
  default:
    return 3;
  }
  recording = false;
  for (const auto &s : trace)
    std::cout << s << '\n';
  for (const auto &entry : params) {
    const float value = entry.second->getValue();
    std::uint32_t bits;
    std::memcpy(&bits, &value, 4);
    std::cout << "PARAM " << entry.first << ' ' << bits << '\n';
  }
  std::cout << "STATE " << Access::blinkState(m) << ' '
            << Access::hold(m).isExecuting() << ' '
            << Access::blink(m).isExecuting() << ' ' << result << '\n';
}
