#include "core/system/coredebug.h"
#include "presonus/surface/MappingComponent.hpp"
#include "presonus/surface/NetworkSetupComponent.hpp"
#include "presonus/surface_panel/ControlHelpers.hpp"
#include <array>
#include <cstdarg>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <string>
#include <string_view>
#include <vector>

namespace {
using namespace Core::Portable;
using namespace Presonus::Surface;

bool recording = false;
const Component *rootComponent = nullptr;
std::vector<std::string> events;

void event(std::string text) {
  if (recording)
    events.push_back(std::move(text));
}

struct Observer : ParamObserverBase {
  int notifications = 0;
  void paramChanged(Parameter *, int) override { ++notifications; }
};

struct Probe : NumericParam {
  explicit Probe(const ParamInfo &info) : NumericParam(info) {}
  int count() const { return observerList.count(); }
  ParamValue getValue() const override {
    if (getTag() == 123)
      event("read");
    return NumericParam::getValue();
  }
  void setValue(ParamValue value, bool edit) override {
    if (getTag() != 1000) {
      std::uint32_t bits = 0;
      std::memcpy(&bits, &value, sizeof(bits));
      char hex[9];
      std::snprintf(hex, sizeof(hex), "%08x", bits);
      event("set:" + std::to_string(getTag()) + ":" + hex + ":" +
            std::to_string(edit));
    }
    NumericParam::setValue(value, edit);
  }
};

struct ComponentProbe : Component {
  using Component::Component;
  bool recordLookup = false;
  void add(Probe *parameter) { paramList.add(parameter); }
  Component *findChild(const char *name) const override {
    if (recordLookup)
      event("find:" + std::string(name));
    return Component::findChild(name);
  }
};

struct OfflinePort : Presonus::IPanelPort {
  std::vector<std::array<std::uint8_t, 4>> packets;
  int readMsg(Uart_Msg_Type &) override {
    throw std::logic_error("unexpected port read");
  }
  int writeMsg(Uart_Msg_Type &message) override {
    packets.push_back(message.bytes);
    return 0;
  }
};
struct MappingProbe : MappingComponent {
  MappingProbe() : MappingComponent(presonus::surface::MappingRouteInit{}) {}
  bool isDisplayEncoderLocked() const override { return false; }
  void selectedChannelUpdated() override {}
};

struct OfflineNetworkDependencies
    : presonus::surface::SurfaceNetworkDependencies {
  using Item = Presonus::UC::NetworkItem;
  [[noreturn]] static void unexpected() {
    throw std::logic_error("unexpected network setup service");
  }
  int kind(const Item &) const override { unexpected(); }
  Item *associatedItem(const Item &) const override { unexpected(); }
  void title(const Item &, Core::CStringBuffer<128> &) const override {
    unexpected();
  }
  const char *host(const Item &) const override { unexpected(); }
  int mappingCount() const override { unexpected(); }
  const char *mappingName(int) const override { unexpected(); }
  int targetType() const override { unexpected(); }
  bool stored(const char *, Item *) const override { unexpected(); }
  void acquire(Item *) override { unexpected(); }
  void release(Item *, bool) override { unexpected(); }
  void *component(Item *) override { unexpected(); }
  void *mixerCast(void *) override { unexpected(); }
  void *dawCast(void *) override { unexpected(); }
  void setMixer(void *) override { unexpected(); }
  void setDAW(void *) override { unexpected(); }
  void setTransport(void *) override { unexpected(); }
  void itemInfo(int, Item *) override { unexpected(); }
  void storeSelected(const char *, Item *, int) override { unexpected(); }
  void setNetworkRoot(Component *) override { unexpected(); }
  void selectModelItem(Item *) override { unexpected(); }
  int wiredAssignMode() const override { unexpected(); }
  void configureNetwork(const char *) override { unexpected(); }
  void resumeAdaptors() override { unexpected(); }
  void enableNetwork(bool) override { unexpected(); }
  void setupLocalIP() override { unexpected(); }
};

struct OfflineNetworkProvider : presonus::surface::SurfaceNetworkProvider {
  int localAddresses(Core::Sockets::IPAddress *, int) const override {
    OfflineNetworkDependencies::unexpected();
  }
  bool parseAddress(Core::Sockets::SocketAddress &,
                    const char *) const override {
    OfflineNetworkDependencies::unexpected();
  }
};

void send(void *context, Uart_Msg_Type &message) {
  static_cast<OfflinePort *>(context)->writeMsg(message);
}
void badMode(void *, bool) {
  throw std::logic_error("unexpected offline mode callback");
}
void badTouch(void *, Touchscreen_Type &) {
  throw std::logic_error("unexpected offline touch callback");
}

constexpr const char *elf =
    "304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0";
const ParamInfo params[] = {
    PARAM_INT(2, "main", 0, 1, 0, 0, 0, 0, 0),
    PARAM_INT(31, "target", 0, 1, 0, 0, 0, 0, 0),
    PARAM_INT(32, "calibrate", 0, 1, 0, 0, 0, 0, 0),
    PARAM_INT(33, "fader", 0, 1, 0, 0, 0, 0, 0),
    PARAM_INT(34, "audio", 0, 1, 0, 0, 0, 0, 0),
    PARAM_INT(38, "test", 0, 1, 0, 0, 0, 0, 0),
    PARAM_INT(903, "touch", 0, 1, 0, 0, 0, 0, 0),
    PARAM_INT(1000, "progress", 0, 10, 7, 0, 0, 0, 0),
};

struct Rig {
  Observer observer;
  Observer progressProbe;
  Component networkParameters{"network parameters"};
  OfflineNetworkDependencies networkDependencies;
  OfflineNetworkProvider networkProvider;
  Presonus::DelayTimer networkTimer{0};
  presonus::surface::SurfaceNetworkState networkState{networkParameters,
                                                      networkDependencies,
                                                      networkProvider,
                                                      networkTimer,
                                                      {},
                                                      {}};
  OfflinePort port;
  ComponentProbe root{"root"};
  ComponentProbe *screen = new ComponentProbe("mainscreen");
  std::array<Probe *, 8> probes{};
  ParamList panelParams;
  Probe *panelProgress = new Probe(params[7]);
  presonus::surface::PanelRegistrarCommandState command{&port};
  presonus::surface::RegistrarTestState testState{
      {&port, send, badMode, badTouch, nullptr}};
  PanelRegistrar registrar{panelParams, command};
  presonus::surface::RootServices services;
  SurfaceRootComponent application;

  explicit Rig(bool registrarPresent)
      : application(registrarPresent ? SurfaceRootComponent(registrar)
                                     : SurfaceRootComponent()) {
    root.addChild(screen);
    rootComponent = &root;
    for (std::size_t i = 0; i < probes.size(); ++i) {
      probes[i] = new Probe(params[i]);
      (i < 6 ? *screen : root).add(probes[i]);
    }
    panelParams.add(panelProgress);
    panelProgress->addObserver(&progressProbe);
    registrar.bindTests(testState);
    services.children = &root;
    services.rootParameters = &root;
    services.observer = &observer;
    services.mainScreens.push_back(
        {screen,
         reinterpret_cast<MainScreenComponent *>(std::uintptr_t(0x1234)), elf,
         "_ZTIN8Presonus7Surface19MainScreenComponentE", 0x1a0434});
    application.bindServices(services);
  }
};

void require(bool success) {
  if (!success)
    throw std::logic_error("CCL observer, value or offline registrar mismatch");
}
} // namespace

extern "C" {
Parameter *
__real__ZNK4Core8Portable9Component17getParameterByTagEi(const Component *,
                                                         int);
Parameter *__wrap__ZNK4Core8Portable9Component17getParameterByTagEi(
    const Component *component, int tag) {
  event(std::string("tag:") +
        (component == rootComponent ? "root:" : "screen:") +
        std::to_string(tag));
  return __real__ZNK4Core8Portable9Component17getParameterByTagEi(component,
                                                                  tag);
}
Parameter *__real__ZNK8Presonus7Surface14PanelRegistrar17getParameterByTagEi(
    const PanelRegistrar *, int);
Parameter *__wrap__ZNK8Presonus7Surface14PanelRegistrar17getParameterByTagEi(
    const PanelRegistrar *component, int tag) {
  event("tag:registrar:" + std::to_string(tag));
  return __real__ZNK8Presonus7Surface14PanelRegistrar17getParameterByTagEi(
      component, tag);
}
void __real__ZN4Core8Portable9Parameter11addObserverEPNS0_14IParamObserverE(
    Parameter *, IParamObserver *);
void __wrap__ZN4Core8Portable9Parameter11addObserverEPNS0_14IParamObserverE(
    Parameter *parameter, IParamObserver *observer) {
  event("add:" + std::to_string(parameter->getTag()));
  __real__ZN4Core8Portable9Parameter11addObserverEPNS0_14IParamObserverE(
      parameter, observer);
}
void __real__ZN4Core8Portable9Parameter14removeObserverEPNS0_14IParamObserverE(
    Parameter *, IParamObserver *);
void __wrap__ZN4Core8Portable9Parameter14removeObserverEPNS0_14IParamObserverE(
    Parameter *parameter, IParamObserver *observer) {
  event("remove:" + std::to_string(parameter->getTag()));
  __real__ZN4Core8Portable9Parameter14removeObserverEPNS0_14IParamObserverE(
      parameter, observer);
}
void __real__ZN8Presonus7Surface14PanelRegistrar7runTestENS1_8TestModeEb(
    PanelRegistrar *, PanelRegistrar::TestMode, bool);
void __wrap__ZN8Presonus7Surface14PanelRegistrar7runTestENS1_8TestModeEb(
    PanelRegistrar *registrar, PanelRegistrar::TestMode mode, bool enabled) {
  event("run:" + std::to_string(mode) + ":" + std::to_string(enabled));
  __real__ZN8Presonus7Surface14PanelRegistrar7runTestENS1_8TestModeEb(
      registrar, mode, enabled);
}
void __real__ZN8Presonus7Surface14PanelRegistrar29requestUpdatedFaderParametersEv(
    PanelRegistrar *);
void __wrap__ZN8Presonus7Surface14PanelRegistrar29requestUpdatedFaderParametersEv(
    PanelRegistrar *registrar) {
  event("request");
  __real__ZN8Presonus7Surface14PanelRegistrar29requestUpdatedFaderParametersEv(
      registrar);
}
void __real__ZN4Core11DebugPrintfEPKcz(const char *, ...);
void __wrap__ZN4Core11DebugPrintfEPKcz(const char *fmt, ...) {
  std::string_view message(fmt);
  if (message.starts_with("SurfaceRootComponent::") && message.ends_with("\n"))
    event("debug:" + std::string(message.substr(0, message.size() - 1)));
  char buffer[1024];
  std::va_list args;
  va_start(args, fmt);
  std::vsnprintf(buffer, sizeof(buffer), fmt, args);
  va_end(args);
  __real__ZN4Core11DebugPrintfEPKcz("%s", buffer);
}
} // extern "C"

int main(int argc, char **argv) {
  if (argc != 5)
    return 2;
  const std::string_view task(argv[1]);
  const float value = std::strtof(argv[2], nullptr);
  const bool registrar = std::atoi(argv[3]) != 0;
  const int childMode = std::atoi(argv[4]);
  Rig rig(registrar);
  const ParamInfo argInfo = PARAM_FLOAT(123, "arg", -10, 10, 0, 0, 0, 0, 0, 0);
  Probe argument(argInfo);
  argument.setValue(value, false);
  rig.services.touchscreenActive = value != 0;
  rig.testState.touchscreen = value != 0;
  const int initialObservers = task == "s03" || task == "s07" ||
                               task == "s08" || task == "s09" ||
                               (task == "s04" && value == 0);
  if (initialObservers)
    for (auto *probe : rig.probes)
      probe->addObserver(&rig.observer);

  auto &root = rig.application;
  if (task == "s05" || task == "r06") {
    const char *name = task == "s05" ? "mapping" : "networksetup";
    if (task == "s05") {
      auto *typed = new MappingProbe;
      typed->setName(name);
      rig.services.mappingComponents.push_back(typed);
      rig.root.addChild(typed);
    } else {
      auto *typed = new NetworkSetupComponent(rig.networkState);
      typed->setName(name);
      rig.services.networkSetupComponents.push_back(typed);
      rig.root.addChild(typed);
    }
    if (childMode != 1) {
      auto *typed = rig.root.findChild(name);
      typed->setName("other");
      if (childMode == 2)
        rig.root.addChild(new Component(name));
    }
    rig.root.recordLookup = true;
  }

  recording = true;
  bool found = false;
  if (task == "s01")
    root.paramChangedLaunchAudioUtilities();
  else if (task == "s02")
    root.paramChangedLaunchFaderUtilities(value != 0);
  else if (task == "s03")
    root.paramChangedQuitTestTouchscreen();
  else if (task == "s04")
    root.paramChangedLaunchCalibrateTouchPage(value != 0);
  else if (task == "s05")
    found = root.getMappingComponent() != nullptr;
  else if (task == "r06")
    found = root.getNetworkSetupComponent() != nullptr;
  else if (task == "s07")
    root.paramChangedExitTestTouchscreenPage(&argument);
  else if (task == "s08")
    root.paramChangedExitFaderUtilitiesPage(&argument);
  else if (task == "s09")
    root.paramChangedExitCalibrateTouchPage(&argument);
  else if (task == "s10")
    root.paramChangedCalibrationTarget(&argument);
  else
    return 2;
  recording = false;

  if (task == "s01")
    require(rig.probes[4]->count() == 1 && rig.probes[4]->getValue() == 1 &&
            rig.observer.notifications == 0);
  if (task == "s02") {
    require(rig.probes[3]->count() == int(value != 0) &&
            rig.probes[3]->getValue() == float(value != 0));
    if (value != 0)
      require(rig.port.packets == std::vector<std::array<std::uint8_t, 4>>{
                                      {103, 14, 1, 0}, {103, 14, 2, 0}});
  }
  if (task == "s03" && value != 0)
    require(rig.probes[0]->getValue() == 1 && !rig.testState.touchscreen &&
            rig.probes[5]->count() == 0 && rig.probes[6]->count() == 0);
  if (task == "s04") {
    if (value != 0) {
      require(rig.probes[2]->getValue() == 1 && rig.probes[2]->count() == 1 &&
              rig.panelProgress->getValue() == 0 &&
              rig.panelProgress->count() == 2 &&
              rig.port.packets ==
                  std::vector<std::array<std::uint8_t, 4>>{{103, 12, 1, 0}});
    } else
      require(rig.probes[2]->count() == 0 && rig.probes[7]->count() == 0 &&
              rig.panelProgress->count() == 1 && rig.port.packets.empty());
  }
  if (task == "s07" && value > -1 && value < 1)
    require(!rig.testState.touchscreen && rig.probes[5]->count() == 0 &&
            rig.probes[6]->count() == 0);
  if (task == "s08")
    require(rig.probes[3]->count() == (value <= -1 || value >= 1));
  if (task == "s09") {
    const bool exit = value > -1 && value < 1;
    require(rig.probes[2]->count() == !exit && rig.probes[7]->count() == !exit);
    if (exit && registrar)
      require(rig.port.packets ==
              std::vector<std::array<std::uint8_t, 4>>{{103, 12, 0, 0}});
    else
      require(rig.port.packets.empty());
  }
  if (task == "s10")
    require(rig.probes[1]->getValue() == float(value >= 8) &&
            rig.probes[1]->count() == int(value >= 8));
  for (const auto &text : events)
    std::cout << "EVENT " << text << '\n';
  if (task == "s05" || task == "r06")
    std::cout << "FOUND " << found << '\n';
  if (task == "s03" || task == "s07")
    std::cout << "ACTIVE " << rig.services.touchscreenActive << '\n';
}
