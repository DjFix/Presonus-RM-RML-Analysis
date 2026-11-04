#include "presonus/panel/control.hpp"
#include "presonus/reconstruction200/large02_w10.hpp"
#include "presonus/surface_panel/OutputPin.hpp"
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <vector>
struct Touchscreen_Type {
  unsigned char bytes[4];
};
namespace {
int brightness = 0, closes = 0, opened = 0;
std::vector<std::vector<unsigned>> sets;
std::vector<unsigned> modeCalls;
std::vector<unsigned> faderCalls;
std::vector<std::vector<int>> brightnessLifecycle;
std::vector<std::vector<int>> forwarded;
class ObservedParam final : public Core::Portable::NumericParam {
public:
  explicit ObservedParam(const Core::Portable::ParamInfo &info)
      : NumericParam(info) {}
  void setValue(float value, bool edit) override {
    unsigned raw;
    std::memcpy(&raw, &value, 4);
    sets.push_back(
        {static_cast<unsigned>(getTag()), raw, static_cast<unsigned>(edit)});
    NumericParam::setValue(value, edit);
  }
};
struct Port final : Presonus::IPanelPort {
  std::vector<std::vector<unsigned>> packets;
  int readMsg(Uart_Msg_Type &) override { std::abort(); }
  int writeMsg(Uart_Msg_Type &message) override {
    packets.push_back({message.bytes.begin(), message.bytes.end()});
    return 0;
  }
};
struct Boundary {
  Port *port;
  int *result;
};
void send(void *p, Uart_Msg_Type &message) {
  static_cast<Boundary *>(p)->port->writeMsg(message);
}
void testMode(void *, bool enabled) { modeCalls.push_back(enabled); }
void touch(void *p, Touchscreen_Type &) {
  *static_cast<Boundary *>(p)->result = 1;
}
std::vector<unsigned> handlerTrace;
// Test doubles capture ONLY the unresolved concrete virtual-handler boundary.
// Actual AssignmentHandler/MixerAssignmentHandler castTo providers are used.
class NonMixerProbe final : public Presonus::AssignmentHandler {
public:
  const char *getName() const override { std::abort(); }
  void updateConnections() override { std::abort(); }
};
class FocusProbe final : public Presonus::MixerAssignmentHandler {
public:
  FocusProbe(int ordinal, int scenario, Core::Portable::Parameter *alternate)
      : ordinal_(ordinal), scenario_(scenario), alternate_(alternate) {}
  const char *getName() const override { std::abort(); }
  void updateConnections() override { std::abort(); }
  void onMappingParamChanged(Core::Portable::Parameter *) override {
    std::abort();
  }
  bool getParamFocusInfo(FocusInfo &info,
                         Core::Portable::Parameter *parameter) override {
    if (parameter->getTag() != 900)
      std::abort();
    handlerTrace.push_back(ordinal_);
    if (ordinal_ == 0) {
      info.sourcePort.label = "ignored";
      if (scenario_ & 16)
        info.sourcePort.alternateOriginal = alternate_;
      return false;
    }
    if (ordinal_ == 1) {
      info.sourcePort.label = "focus";
      return !(scenario_ & 32);
    }
    if (!(scenario_ & 32))
      std::abort();
    return false;
  }

private:
  int ordinal_, scenario_;
  Core::Portable::Parameter *alternate_;
};
std::uint32_t bits(float v) {
  std::uint32_t b;
  std::memcpy(&b, &v, 4);
  return b;
}
template <class T> void array(const T &items) {
  std::cout << '[';
  bool first = true;
  for (auto value : items) {
    if (!first)
      std::cout << ',';
    first = false;
    std::cout << +value;
  }
  std::cout << ']';
}
} // namespace
// Test-only libc boundary: no sysfs/device operation reaches the host.
extern "C" std::FILE *__wrap_fopen(const char *, const char *) {
  ++opened;
  return reinterpret_cast<std::FILE *>(0x1234);
}
extern "C" int __wrap_fprintf(std::FILE *, const char *, ...) { return 1; }
extern "C" int __wrap_fclose(std::FILE *) {
  ++closes;
  return 0;
}
extern "C" std::size_t __wrap_fwrite(const void *, std::size_t, std::size_t n,
                                     std::FILE *) {
  return n;
}
extern "C" int __wrap_setvbuf(std::FILE *, char *, int, std::size_t) {
  return 0;
}
extern "C" int __wrap_fputc(int c, std::FILE *) {
  brightness = (c == '1');
  return c;
}
extern "C" int __wrap___fprintf_chk(std::FILE *, int, const char *, ...) {
  return 1;
}
extern "C" void
realFaderCalibration(Presonus::Surface::PanelRegistrar *, bool) asm(
    "__real__ZN8Presonus7Surface14PanelRegistrar22invokeFaderCalibrationEb");
extern "C" void
wrapFaderCalibration(Presonus::Surface::PanelRegistrar *, bool) asm(
    "__wrap__ZN8Presonus7Surface14PanelRegistrar22invokeFaderCalibrationEb");
extern "C" void wrapFaderCalibration(Presonus::Surface::PanelRegistrar *p,
                                     bool enabled) {
  faderCalls.push_back(enabled);
  realFaderCalibration(p, enabled);
}
extern "C" void realPinCtor(Presonus::Panel::OutputPin *,
                            int) asm("__real__ZN8Presonus5Panel9OutputPinC1Ei");
extern "C" void wrapPinCtor(Presonus::Panel::OutputPin *,
                            int) asm("__wrap__ZN8Presonus5Panel9OutputPinC1Ei");
extern "C" void wrapPinCtor(Presonus::Panel::OutputPin *p, int pin) {
  brightnessLifecycle.push_back({0, pin});
  realPinCtor(p, pin);
}
extern "C" void
realPinSet(Presonus::Panel::OutputPin *,
           int) asm("__real__ZN8Presonus5Panel9OutputPin3setEi");
extern "C" void
wrapPinSet(Presonus::Panel::OutputPin *,
           int) asm("__wrap__ZN8Presonus5Panel9OutputPin3setEi");
extern "C" void wrapPinSet(Presonus::Panel::OutputPin *p, int value) {
  brightnessLifecycle.push_back({1, value});
  realPinSet(p, value);
}
extern "C" void realPinDtor(Presonus::Panel::OutputPin *) asm(
    "__real__ZN8Presonus5Panel9OutputPinD1Ev");
extern "C" void wrapPinDtor(Presonus::Panel::OutputPin *) asm(
    "__wrap__ZN8Presonus5Panel9OutputPinD1Ev");
extern "C" void wrapPinDtor(Presonus::Panel::OutputPin *p) {
  realPinDtor(p);
  brightnessLifecycle.push_back({2, 0});
}
extern "C" int realForward0(Presonus::Surface::PanelRegistrar *, int) asm(
    "__real__ZN8Presonus7Surface14PanelRegistrar14bumpFaderSpeedEi");
extern "C" int wrapForward0(Presonus::Surface::PanelRegistrar *, int) asm(
    "__wrap__ZN8Presonus7Surface14PanelRegistrar14bumpFaderSpeedEi");
extern "C" int wrapForward0(Presonus::Surface::PanelRegistrar *p, int delta) {
  forwarded.push_back({0, delta});
  return realForward0(p, delta);
}
extern "C" int realForward1(Presonus::Surface::PanelRegistrar *, int) asm(
    "__real__ZN8Presonus7Surface14PanelRegistrar25bumpFaderTouchSensitivityEi");
extern "C" int wrapForward1(Presonus::Surface::PanelRegistrar *, int) asm(
    "__wrap__ZN8Presonus7Surface14PanelRegistrar25bumpFaderTouchSensitivityEi");
extern "C" int wrapForward1(Presonus::Surface::PanelRegistrar *p, int delta) {
  forwarded.push_back({1, delta});
  return realForward1(p, delta);
}
int main(int argc, char **argv) {
  if (argc != 4)
    return 2;
  int n = std::atoi(argv[1]), arg = std::atoi(argv[2]),
      enabled = std::atoi(argv[3]);
  constexpr int tags[] = {900, 901, 903, 1000, 2000, 2001};
  Core::Portable::ParamInfo infos[6]{};
  Core::Portable::ParamList parameters;
  for (int i = 0; i < 6; ++i) {
    infos[i].type = Core::Portable::ParamInfo::kFloat;
    infos[i].tag = tags[i];
    std::strcpy(infos[i].name, i == 0 ? "exists" : "other");
    infos[i].minValue = -100000;
    infos[i].maxValue = 100000;
    infos[i].defaultValue = 7;
    parameters.add(new ObservedParam(infos[i]));
  }
  sets.clear();
  Port port;
  int result = 0;
  Boundary boundary{&port, &result};
  presonus::surface::PanelRegistrarCommandState command{&port};
  presonus::surface::RegistrarTestState tests{
      {&boundary, send, testMode, touch, nullptr}};
  tests.color = 9;
  tests.touchscreen = enabled;
  tests.controlValues.fill(0x77777777);
  tests.switchValues.fill(119);
  Presonus::Surface::PanelRegistrar registrar(parameters, command);
  registrar.bindTests(tests);
  Presonus::Surface::SurfaceRootComponent root(registrar), empty;
  Core::Portable::Component tree;
  if (n == 16 && enabled)
    tree.addChild(new Core::Portable::Component("mainscreen"));
  presonus::surface::RootServices services;
  Core::Portable::ParamInfo aliasInfo{}, labelInfo{};
  aliasInfo.type = Core::Portable::ParamInfo::kAlias;
  aliasInfo.tag = 5000;
  labelInfo.type = Core::Portable::ParamInfo::kString;
  labelInfo.tag = 5001;
  Core::Portable::AliasParam focusAlias(aliasInfo);
  Core::Portable::StringParam focusLabel(labelInfo);
  focusLabel.fromString("initial", false);
  if ((n == 6 || n == 10 || n == 17) && (arg & 8))
    focusAlias.setOriginal(parameters.byTag(900));
  Core::Vector<Presonus::AssignmentHandler *> handlers;
  NonMixerProbe nonMixer;
  FocusProbe first(0, arg, parameters.byTag(901)),
      second(1, arg, parameters.byTag(901)),
      last(2, arg, parameters.byTag(901));
  if (!(arg & 256)) {
    handlers.add(nullptr);
    handlers.add(&nonMixer);
    if (!(arg & 512)) {
      handlers.add(&first);
      handlers.add(&second);
      handlers.add(&last);
    }
  }
  presonus::surface::FocusState focusState{(arg & 64) ? nullptr : &focusAlias,
                                           (arg & 128) ? nullptr : &focusLabel,
                                           &handlers};
  services.focus = (arg & 2) ? &focusState : nullptr;
  services.children = &tree;
  if (n == 16 && enabled && arg) {
    auto *component = tree.findChild("mainscreen");
    services.mainScreens.push_back(
        {component,
         reinterpret_cast<Presonus::Surface::MainScreenComponent *>(component),
         "304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0",
         "_ZTIN8Presonus7Surface19MainScreenComponentE", 0x1a0434});
  }
  if (n == 16 && enabled && arg) {
    auto &reference = services.mainScreens.back();
    if (arg == 2)
      reference.elfSha256 = "wrong-input";
    if (arg == 3)
      reference.nativeType = "wrong-type";
    if (arg == 4)
      reference.nativeTypeAddress = 0;
    if (arg == 5)
      reference.component = &tree;
  }
  root.bindServices(services);
  Presonus::Panel::ControlRegistrar controlRegistrar;
  Presonus::Panel::FaderControl fader(10);
  Presonus::Panel::SwitchControl sw(11, 0, true);
  Presonus::Panel::Control control(12);
  if (arg & 4) {
    presonus::panel::ControlAccess::parameter(fader) = parameters.byTag(900);
    presonus::panel::ControlAccess::parameter(sw) = parameters.byTag(900);
    presonus::panel::ControlAccess::parameter(control) = parameters.byTag(900);
  }
  switch (n) {
  case 1:
    registrar.handleCalibrateTouchscreenProgress(enabled, arg);
    break;
  case 2:
    registrar.runTest(
        static_cast<Presonus::Surface::PanelRegistrar::TestMode>(arg), enabled);
    break;
  case 3:
    result = (enabled ? root : empty).bumpFaderSpeed(arg);
    break;
  case 4:
    registrar.setColorRgbLeds(arg);
    break;
  case 5:
    registrar.invokeTestTouchscreen(arg);
    break;
  case 6:
    root.faderChanged(controlRegistrar, 42, 43, (arg & 1) ? &fader : nullptr);
    break;
  case 10:
    root.updateFocusParams((arg & 1) ? &control : nullptr);
    break;
  case 16:
    result = root.getMainScreenComponent() != nullptr;
    break;
  case 17:
    root.switchChanged(controlRegistrar, 42, 43, enabled,
                       (arg & 1) ? &sw : nullptr);
    break;
  case 7:
    registrar.invokePanelTest(
        static_cast<Presonus::Surface::PanelRegistrar::TestMode>(arg), enabled);
    break;
  case 8: {
    Core::Portable::ParamInfo groupInfos[3]{};
    for (int i = 0; i < 3; ++i)
      groupInfos[i].tag = 10 + i;
    registrar.addSwitchControlGroup(42, groupInfos, arg);
    if (tests.groups.size() != 1 ||
        tests.groups[0]->count() != (arg > 0 ? arg : 0))
      return 3;
    for (auto &control : tests.switches)
      if (!control->isImmediate() ||
          presonus::panel::ControlAccess::io(*control) != nullptr)
        return 4;
    break;
  }
  case 9:
    registrar.adjustLcdBrightness(arg);
    result = brightness;
    break;
  case 11:
    registrar.invoke48vTest(arg);
    break;
  case 12:
    registrar.invokeCalibrateTouchTest(arg);
    break;
  case 13:
    result = (enabled ? root : empty).bumpFaderTouchSensitivity(arg);
    break;
  case 14: {
    Touchscreen_Type message{{static_cast<unsigned char>(arg), 0, 0, 0}};
    registrar.handleTouchscreen(message);
    break;
  }
  case 15:
    result = registrar.findParameter(arg ? "exists" : "missing") != nullptr;
    break;
  case 18:
    registrar.invokeScribbleStripTest(arg);
    break;
  case 19:
    registrar.invokeControlSurfaceTest(arg);
    break;
  case 20: {
    parameters.byTag(900)->setValue(arg, false);
    root.paramChangedLcdBrightness(parameters.byTag(900));
    result = brightness;
    break;
  }
  case 21:
    registrar.turnOnRgbLeds(arg);
    break;
  case 22:
    result = registrar.getParameterByTag(arg) != nullptr;
    break;
  case 23:
    registrar.invokeRgbTest(arg);
    break;
  default:
    return 5;
  }
  if (n == 9 || n == 20) {
    if (opened != 3 || closes != 3)
      return 6;
  }
  // These wrapper fixtures observe dependency arguments/results, independently
  // of the separately evidenced fader provider's state mutation.
  if (n == 3 || n == 13 || n == 20) {
    for (int t : tags)
      parameters.byTag(t)->setValue(7, false);
    port.packets.clear();
    sets.clear();
  }
  if (n == 2 && arg == 107)
    port.packets.clear();
  std::cout << "\nRESULT {\"params\":{";
  for (int i = 0; i < 6; ++i) {
    if (i)
      std::cout << ',';
    std::cout << '"' << tags[i]
              << "\":" << bits(parameters.byTag(tags[i])->getValue());
  }
  std::cout << "},\"packets\":[";
  for (std::size_t i = 0; i < port.packets.size(); ++i) {
    if (i)
      std::cout << ',';
    auto p = port.packets[i];
    if (n == 11 || (n == 2 && arg == 110))
      p.resize(3);
    array(p);
  }
  std::cout << "],\"flags\":";
  array(std::vector<unsigned>{tests.controls, tests.rgb, tests.scribble,
                              tests.color, tests.touchscreen});
  std::cout << ",\"timers\":";
  array(std::vector<unsigned>{tests.touchTimer.isExecuting(),
                              tests.rgbTimer.isExecuting(),
                              tests.scribbleTimer.isExecuting()});
  std::cout << ",\"values\":";
  array(tests.controlValues);
  std::cout << ",\"switches\":";
  array(tests.switchValues);
  std::cout << ",\"result\":" << result;
  if (n == 8) {
    std::cout << ",\"group\":{\"id\":"
              << presonus::panel_binding::ControlGroupAccess::groupId(
                     *tests.groups[0])
              << ",\"tags\":[";
    for (std::size_t i = 0; i < tests.switches.size(); ++i) {
      if (i)
        std::cout << ',';
      std::cout << presonus::panel::ControlAccess::tag(*tests.switches[i]);
    }
    std::cout << "]}";
  }
  std::cout << ",\"sets\":[";
  for (std::size_t i = 0; i < sets.size(); ++i) {
    if (i)
      std::cout << ',';
    array(sets[i]);
  }
  std::cout << "],\"mode\":";
  array(modeCalls);
  std::cout << ",\"durations\":";
  array(std::vector<std::int64_t>{
      presonus::timing::DelayTimerAccess::get(tests.touchTimer).duration,
      presonus::timing::DelayTimerAccess::get(tests.rgbTimer).duration,
      presonus::timing::DelayTimerAccess::get(tests.scribbleTimer).duration});
  std::cout << ",\"faderCalls\":";
  array(faderCalls);
  std::cout << ",\"brightnessLifecycle\":[";
  for (std::size_t i = 0; i < brightnessLifecycle.size(); ++i) {
    if (i)
      std::cout << ',';
    array(brightnessLifecycle[i]);
  }
  std::cout << ']';
  std::cout << ",\"forwarded\":[";
  for (std::size_t i = 0; i < forwarded.size(); ++i) {
    if (i)
      std::cout << ',';
    array(forwarded[i]);
  }
  std::cout << ']';
  std::cout << ",\"focus\":{\"alias\":"
            << (focusAlias.getOriginal() ? focusAlias.getOriginal()->getTag()
                                         : -1)
            << ",\"text\":\"" << static_cast<const char *>(focusLabel.getText())
            << "\"}";
  std::cout << ",\"handlerTrace\":";
  array(handlerTrace);
  std::cout << "}\n";
}
