#include "presonus/panel/protocol_comm.hpp"
#include "presonus/surface_panel/ControlHelpers.hpp"
#include <cstdarg>
#include <iostream>
#include <map>
#include <string>
#include <vector>

using namespace Core::Portable;
using namespace Presonus::Surface;
namespace {
bool recording = false;
std::vector<std::string> trace;
void add(std::string value) {
  if (recording)
    trace.push_back(std::move(value));
}
struct Observer : ParamObserverBase {
  int count = 0;
  void paramChanged(Parameter *, int) override {
    if (recording)
      ++count;
  }
};
struct Probe : NumericParam {
  using NumericParam::NumericParam;
  ParamValue getValue() const override {
    add("get:" + std::to_string(getTag()));
    return NumericParam::getValue();
  }
  void setValue(ParamValue value, bool edit) override {
    add("set:" + std::to_string(getTag()) + ":" +
        std::to_string(static_cast<int>(value)) + ":" + std::to_string(edit));
    NumericParam::setValue(value, edit);
  }
  int observers() const { return observerList.count(); }
};
struct ComponentPort : Component {
  using Component::Component;
  void add(Probe *p) { paramList.add(p); }
  const ParamList &parameters() { return paramList; }
};
struct OfflinePort : Presonus::IPanelPort {
  int readMsg(Uart_Msg_Type &) override { return 0; }
  int writeMsg(Uart_Msg_Type &) override {
    ++writes;
    return 0;
  }
  int writes = 0;
};
void receiveSend(void *context, Uart_Msg_Type &message) {
  static_cast<OfflinePort *>(context)->writeMsg(message);
}
void receiveMode(void *, bool) {}
void receiveTouch(void *, Touchscreen_Type &) {}
} // namespace

extern "C" Parameter *
__real__ZNK4Core8Portable9Component17getParameterByTagEi(const Component *,
                                                         int);
extern "C" Parameter *
__wrap__ZNK4Core8Portable9Component17getParameterByTagEi(const Component *p,
                                                         int tag) {
  add("tag:" + std::to_string(tag));
  return __real__ZNK4Core8Portable9Component17getParameterByTagEi(p, tag);
}
extern "C" void
__real__ZN4Core8Portable9Parameter14removeObserverEPNS0_14IParamObserverE(
    Parameter *, IParamObserver *);
extern "C" void
__wrap__ZN4Core8Portable9Parameter14removeObserverEPNS0_14IParamObserverE(
    Parameter *p, IParamObserver *o) {
  add("remove:" + std::to_string(p->getTag()));
  __real__ZN4Core8Portable9Parameter14removeObserverEPNS0_14IParamObserverE(p,
                                                                            o);
}
extern "C" void
__real__ZN4Core8Portable9Parameter11addObserverEPNS0_14IParamObserverE(
    Parameter *, IParamObserver *);
extern "C" void
__wrap__ZN4Core8Portable9Parameter11addObserverEPNS0_14IParamObserverE(
    Parameter *p, IParamObserver *o) {
  add("add:" + std::to_string(p->getTag()));
  __real__ZN4Core8Portable9Parameter11addObserverEPNS0_14IParamObserverE(p, o);
}
extern "C" void __wrap__ZN4Core11DebugPrintfEPKcz(const char *fmt, ...) {
  std::string message(fmt);
  if (message.find("activeTestCount") != std::string::npos)
    add("debug:count");
  if (message.find("paramChangedLaunchTestTouchscreen") != std::string::npos) {
    va_list args;
    va_start(args, fmt);
    add(std::string("debug:") + va_arg(args, const char *));
    va_end(args);
  }
}
extern "C" void
__real__ZN8Presonus7Surface14PanelRegistrar7runTestENS1_8TestModeEb(
    PanelRegistrar *, PanelRegistrar::TestMode, bool);
extern "C" void
__wrap__ZN8Presonus7Surface14PanelRegistrar7runTestENS1_8TestModeEb(
    PanelRegistrar *p, PanelRegistrar::TestMode mode, bool enabled) {
  add("run:" + std::to_string(static_cast<int>(mode)) + ":" +
      std::to_string(enabled));
  // The native oracle intercepts this provider boundary. The portable replay
  // still invokes the genuine registrar, with an isolated receiver.
  const bool previous = recording;
  recording = false;
  __real__ZN8Presonus7Surface14PanelRegistrar7runTestENS1_8TestModeEb(p, mode,
                                                                      enabled);
  recording = previous;
}
int main(int argc, char **argv) {
  if (argc < 4 || (argc - 4) % 2 != 0)
    return 2;
  const bool registrarBound = std::stoi(argv[1]) != 0;
  [[maybe_unused]] const bool argument = std::stoi(argv[2]) != 0;
  const float defaultValue = std::stof(argv[3]);
  std::map<int, ParamInfo> info;
  std::map<int, Probe *> parameters;
  Observer observer;
  ComponentPort root("root");
  auto *screen = new ComponentPort("mainscreen");
  root.addChild(screen);
  const auto insert = [&](int tag, ComponentPort &parent) {
    const ParamInfo data =
        PARAM_FLOAT(tag, "probe", -10000, 10000, defaultValue, 0, 0, 0, 0, 0);
    auto result = info.emplace(tag, data);
    auto *parameter = new Probe(result.first->second);
    parent.add(parameter);
    parameters.emplace(tag, parameter);
  };
  for (int tag = 100; tag <= 111; ++tag)
    insert(tag, root);
  for (int tag = 115; tag <= 118; ++tag)
    insert(tag, root);
  for (const int tag : {903, 2002, 9000})
    insert(tag, root);
  for (const int tag : {2, 31, 34, 38})
    insert(tag, *screen);
  // Separate registrar parameter list for the provider-side work.
  ParamList registrarParameters;
  const ParamInfo panelInfos[] = {
      PARAM_INT(903, "panelQuit", 0, 100, 0, 0, 0, 0, 0),
      PARAM_INT(2000, "panelScribble", 0, 100, 0, 0, 0, 0, 0),
      PARAM_INT(2001, "panelTouch", 0, 100, 0, 0, 0, 0, 0)};
  for (const auto &panelInfo : panelInfos)
    registrarParameters.add(new NumericParam(panelInfo));
  for (int i = 4; i < argc; i += 2)
    parameters.at(std::stoi(argv[i]))->setValue(std::stof(argv[i + 1]), false);
  parameters.at(31)->addObserver(&observer);
  parameters.at(34)->addObserver(&observer);
  presonus::surface::RootServices services;
  services.rootParameters = &root;
  services.children = &root;
  services.observer = &observer;
  services.mainScreens.push_back(
      {screen, reinterpret_cast<MainScreenComponent *>(std::uintptr_t{0x1234}),
       "304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0",
       "_ZTIN8Presonus7Surface19MainScreenComponentE", 0x1a0434});
  OfflinePort offline;
  presonus::surface::PanelRegistrarCommandState command{&offline};
  presonus::surface::RegistrarTestState tests(
      {&offline, receiveSend, receiveMode, receiveTouch, nullptr});
  PanelRegistrar registrar(registrarParameters, command);
  registrar.bindTests(tests);
  SurfaceRootComponent target =
      registrarBound ? SurfaceRootComponent(registrar) : SurfaceRootComponent();
  target.bindServices(services);
  recording = true;
  target.paramChangedExitUtilPage(parameters.at(9000));
  recording = false;
  std::cout << "state " << services.touchscreenActive << ' ' << observer.count
            << '\n';
  for (auto [tag, parameter] : parameters)
    std::cout << "param " << tag << ' ' << parameter->getValue() << ' '
              << parameter->observers() << '\n';
  for (const auto &event : trace)
    std::cout << "trace " << event << '\n';
}
