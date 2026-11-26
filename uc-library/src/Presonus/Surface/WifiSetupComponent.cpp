#include "presonus/surface/WifiSetupComponent.hpp"
#include "core/portable/gui/coreview.h"
#include <cstdio>
namespace Presonus::Surface {
void WifiSetupComponent::onIdle() {
  Core::Portable::Component::onIdle();
  checkNetworkScanning();
}
void WifiSetupComponent::connect() {
  if (state.selected < 0)
    return;
  if (auto *password = getParameterByTag(7)) {
    password->fromString("", false);
    dependencies.startPasswordInput(password, "Enter Network Password:", this);
  }
}
int WifiSetupComponent::getMaxListOffset() const {
  auto *list = Core::Portable::ListParam::cast(getParameterByTag(0));
  if (!list)
    return 0;
  int maximum = static_cast<int>(list->getMax());
  return maximum > 0 ? maximum / 5 * 5 : 0;
}
void WifiSetupComponent::onWheelInput(const Core::Portable::WheelEvent &event) {
  addListOffset(event.delta);
}
void WifiSetupComponent::addListOffset(int delta) {
  auto sum =
      static_cast<std::int32_t>(static_cast<std::uint32_t>(state.listOffset) +
                                static_cast<std::uint32_t>(delta));
  int next = sum < 0 ? 0 : sum;
  if (sum >= 0) {
    int maximum = getMaxListOffset();
    if (next > maximum)
      next = maximum;
  }
  if (next == state.listOffset)
    return;
  state.listOffset = next;
  updateDisplayList();
}
void WifiSetupComponent::paramChanged(Core::Portable::Parameter *p,
                                      int message) {
  Core::Portable::Component::paramChanged(p, message);
  if (message != Core::Portable::Parameter::kEdit)
    return;
  int tag = p->getTag();
  if (tag == 0) {
    updateDisplayList();
    return;
  }
  if (tag == 1000 || tag == 1001 || tag == 1002 || tag == 1003) {
    if (p->getValue() > 0.f)
      addListOffset(tag == 1000 ? -5 : tag == 1001 ? -1 : tag == 1002 ? 5 : 1);
    return;
  }
  if (tag == 1005) {
    connect();
    return;
  }
  if (static_cast<unsigned int>(tag - 100) >= 900 || tag % 2 != 1)
    return;
  if (p->getValue() < 1.f)
    state.selected = -1;
  else {
    for (int row = 0; row < 5; ++row) {
      auto *button = paramList.byTag(101 + row * 2);
      if (button == p)
        state.selected = static_cast<std::int32_t>(
            static_cast<std::uint32_t>(state.listOffset) + row);
      else if (button)
        button->setValue(0.f, false);
    }
  }
  if (auto *enabled = getParameterByTag(1004))
    enabled->setValue(state.selected < 0 ? 0.f : 1.f, true);
}
void WifiSetupComponent::updateDisplayList() {
  if (!page.isVisible())
    return;
  int maximum = getMaxListOffset();
  if (maximum < state.listOffset)
    state.listOffset = maximum;
  auto *list = Core::Portable::ListParam::cast(getParameterByTag(0));
  if (!list)
    return;
  int last = static_cast<int>(list->getMax());
  for (int row = 0; row < 5; ++row) {
    int index = static_cast<std::int32_t>(
        static_cast<std::uint32_t>(state.listOffset) + row);
    auto *text = paramList.byTag(100 + row * 2);
    auto *button = paramList.byTag(101 + row * 2);
    bool present = index <= last;
    Core::CStringBuffer<128> label;
    if (present)
      list->getStringForValue(label.getBuffer(), 128, index);
    text->fromString(label, false);
    button->setValue(present && state.selected == index ? 1.f : 0.f, false);
    button->enable(present);
  }
}
void WifiSetupComponent::updateNetworkList(bool scanning) const {
  auto *names = Core::Portable::ListParam::cast(getParameterByTag(0));
  auto *flags = Core::Portable::ListParam::cast(getParameterByTag(1));
  auto *signals = Core::Portable::ListParam::cast(getParameterByTag(2));
  if (names && flags && signals) {
    dependencies.ensureManager();
    dependencies.updateList(names, flags, signals, !scanning);
  }
}
void WifiSetupComponent::getSelectedSSID(Core::CStringBuffer<64> &ssid) {
  if (state.selected < 0)
    return;
  auto *list = Core::Portable::ListParam::cast(getParameterByTag(0));
  // Native dereferences the list and display parameters without null checks
  // here.
  list->getStringForValue(ssid.getBuffer(), 64, state.selected);
  getParameterByTag(5)->fromString(ssid, false);
  dependencies.ensureManager();
  if (!dependencies.findNetwork(ssid))
    return;
  if (dependencies.networkHasFlag("WEP"))
    getParameterByTag(6)->fromString("WEP", false);
  else if (dependencies.networkHasFlag("WPA-PSK-TKIP") ||
           dependencies.networkHasFlag("WPA2-PSK-TKIP"))
    getParameterByTag(6)->fromString("WPA/WPA2", false);
}
void WifiSetupComponent::networkChanged(const Presonus::WIFIManager &manager) {
  updateNetworkList(false);
  getParameterByTag(3)->fromString(dependencies.managerStatus(manager), false);
  const char *ssid = dependencies.managerSSID(manager);
  getParameterByTag(4)->fromString(ssid, false);
  getParameterByTag(9)->fromString(dependencies.managerIP(manager), true);
  dependencies.ensureManager();
  if (dependencies.findNetwork(ssid)) {
    long long signal = 0;
    std::sscanf(dependencies.networkSignal(), "%lld", &signal);
    getParameterByTag(8)->setValue(static_cast<float>(signal) * 0.01f, false);
  }
}
void WifiSetupComponent::onShow(bool showing) {
  dependencies.pageOnShow(showing);
  if (page.isVisible()) {
    state.selected = -1;
    if (auto *enabled = getParameterByTag(1004))
      enabled->setValue(0.f, true);
    timer.beginAction(-1.f);
    updateDisplayList();
  } else
    (void)timer.endAction();
}
void WifiSetupComponent::checkNetworkScanning() {
  if (!timer.isLongEnoughYet())
    return;
  phase.refreshNext = !phase.refreshNext;
  if (phase.refreshNext) {
    dependencies.ensureManager();
    dependencies.scan(false);
  } else
    updateNetworkList(false);
  timer.beginAction(-1.f);
}
} // namespace Presonus::Surface

#include <stdexcept>
namespace presonus::surface {
namespace {
WifiSetupUi *appUi = nullptr;
}
void setWifiSetupUi(WifiSetupUi *value) { appUi = value; }
int WifiSetupDependencies::joinNetwork(const char *, const char *) {
  throw std::logic_error("WifiSetup connection boundary is required");
}
WifiSetupUi &requireWifiUi() {
  if (!appUi)
    throw std::logic_error(
        "WifiSetupUi must be initialized before original construction");
  return *appUi;
}
class ManagerDependencies final : public WifiSetupDependencies {
  Presonus::Surface::WifiSetupComponent &owner;
  WifiSetupUi &ui;
  mutable Presonus::WIFIManager::NetworkItem *selected = nullptr;

public:
  ManagerDependencies(Presonus::Surface::WifiSetupComponent &owner,
                      WifiSetupUi &ui)
      : owner(owner), ui(ui) {}
  void pageOnShow(bool b) override { owner.Presonus::PageComponent::onShow(b); }
  void startPasswordInput(Core::Portable::Parameter *p, const char *title,
                          const void *completion) override {
    ui.startPasswordInput(p, title, completion);
  }
  void ensureManager() const override {
    (void)Presonus::WIFIManager::instance();
  }
  void updateList(Core::Portable::ListParam *a, Core::Portable::ListParam *b,
                  Core::Portable::ListParam *c, bool empty) const override {
    Presonus::WIFIManager::instance().updateList(a, b, c, empty);
  }
  bool findNetwork(const char *name) const override {
    selected = Presonus::WIFIManager::instance().find(name);
    return selected != nullptr;
  }
  bool networkHasFlag(const char *flag) const override {
    return selected && selected->hasFlag(flag);
  }
  const char *managerStatus(const Presonus::WIFIManager &m) const override {
    return m.statusMessage();
  }
  const char *managerSSID(const Presonus::WIFIManager &m) const override {
    return m.activeNetwork();
  }
  const char *managerIP(const Presonus::WIFIManager &m) const override {
    return m.getIP();
  }
  const char *networkSignal() const override {
    return selected ? selected->signal.str() : "";
  }
  void scan(bool b) override { Presonus::WIFIManager::instance().doScan(b); }
  int joinNetwork(const char *ssid, const char *key) override {
    return Presonus::WIFIManager::instance().doJoin(ssid, key);
  }
};
} // namespace presonus::surface
namespace Presonus::Surface {
struct WifiSetupComponent::Owned {
  presonus::surface::WifiSetupState state;
  presonus::surface::WifiScanPhase phase;
  Presonus::DelayTimer timer{10.f};
  presonus::surface::ManagerDependencies dependencies;
  bool registered = false;
  Owned(WifiSetupComponent &owner, presonus::surface::WifiSetupUi &ui)
      : dependencies(owner, ui) {}
};
WifiSetupComponent::WifiSetupComponent(
    presonus::surface::WifiSetupState &s, presonus::surface::WifiScanPhase &ph,
    presonus::surface::WifiSetupDependencies &d, Presonus::PageComponent &p,
    Presonus::DelayTimer &t)
    : PageComponent("", nullptr, 0), state(s), phase(ph), dependencies(d),
      page(p), timer(t) {}
WifiSetupComponent::~WifiSetupComponent() {
  if (owned && owned->registered) {
    Presonus::WIFIManager::instance().removeDelegate(this);
    owned->registered = false;
  }
}
void WifiSetupComponent::wifiStateChanged(Presonus::WIFIManager *manager) {
  networkChanged(*manager);
}
// Original secondary vtable binds effect-free
// WIFIManagerDelegate::adaptorConfigChanged.
void WifiSetupComponent::wifiAdaptersChanged(Presonus::WIFIManager *) {}
void WifiSetupComponent::disconnect() {
  observedD8.getBuffer()[0] = 0;
  dependencies.ensureManager();
  dependencies.joinNetwork(getName(), getName());
  getParameterByTag(0)->setValue(0.f, false);
}
void WifiSetupComponent::textInputFinished(bool canceled) {
  if (canceled)
    return;
  Core::CStringBuffer<64> password, ssid;
  getSelectedSSID(ssid);
  getParameterByTag(7)->toString(password.getBuffer(), 64);
  auto length = password.length();
  if (length == 0)
    return;
  if (password.str()[length - 1] == ' ')
    password.getBuffer()[length - 1] = 0;
  dependencies.ensureManager();
  dependencies.joinNetwork(ssid, password);
}
} // namespace Presonus::Surface

namespace Presonus::Surface {
namespace {
Core::CStringPtr initialStrings[] = {""};
const Core::Portable::ParamInfo firstParameters[] = {
    {2, 0, "WIFIlist", 0.0f, 0.0f, 0.0f, 0.0f, 1.0f, 0, nullptr, nullptr,
     initialStrings, "Available Networks", nullptr},
    {2, 1, "WIFIstrengthlist", 0.0f, 0.0f, 0.0f, 0.0f, 1.0f, 0, nullptr,
     nullptr, initialStrings, "Strength of Available Networks", nullptr},
    {2, 2, "WIFIlocklist", 0.0f, 0.0f, 0.0f, 0.0f, 1.0f, 0, nullptr, nullptr,
     initialStrings, "Lock Status of Available Networks", nullptr},
    {4, 3, "connectstatus", 0.0f, 0.0f, 0.0f, 0.0f, 0.0f, 4, nullptr, nullptr,
     nullptr, "connect status", nullptr},
    {4, 4, "activenetwork", 0.0f, 0.0f, 0.0f, 0.0f, 0.0f, 0, nullptr, nullptr,
     nullptr, "active network", nullptr},
    {4, 5, "joinname", 0.0f, 0.0f, 0.0f, 0.0f, 0.0f, 4, nullptr, nullptr,
     nullptr, "join name", nullptr},
    {4, 6, "jointype", 0.0f, 0.0f, 0.0f, 0.0f, 0.0f, 4, nullptr, nullptr,
     nullptr, "join type", nullptr},
    {4, 7, "password", 0.0f, 0.0f, 0.0f, 0.0f, 0.0f, 4, nullptr, nullptr,
     nullptr, "Network password", nullptr},
    {3, 8, "WIFISignal", 0.0f, 1.0f, 0.0f, 0.0f, 0.0020000000949949026f, 0, "",
     "", nullptr, "WIFI Signal strength", nullptr},
    {4, 9, "ipname", 0.0f, 0.0f, 0.0f, 0.0f, 0.0f, 4, nullptr, nullptr, nullptr,
     "ip name", nullptr}};
const Core::Portable::ParamInfo finalParameters[] = {
    {0, 1000, "page-up", 0.0f, 1.0f, 0.0f, 0.0f, 1.0f, 0, nullptr, nullptr,
     nullptr, nullptr, nullptr},
    {0, 1002, "page-down", 0.0f, 1.0f, 0.0f, 0.0f, 1.0f, 0, nullptr, nullptr,
     nullptr, nullptr, nullptr},
    {0, 1001, "one-up", 0.0f, 1.0f, 0.0f, 0.0f, 1.0f, 0, nullptr, nullptr,
     nullptr, nullptr, nullptr},
    {0, 1003, "one-down", 0.0f, 1.0f, 0.0f, 0.0f, 1.0f, 0, nullptr, nullptr,
     nullptr, nullptr, nullptr},
    {0, 1004, "has-selection", 0.0f, 1.0f, 0.0f, 0.0f, 1.0f, 0, nullptr,
     nullptr, nullptr, nullptr, nullptr},
    {0, 1005, "connect", 0.0f, 1.0f, 0.0f, 0.0f, 1.0f, 0, nullptr, nullptr,
     nullptr, nullptr, nullptr}};
} // namespace
WifiSetupComponent::WifiSetupComponent(const char *formName, int tag)
    : PageComponent("wifi", formName, tag),
      owned(new Owned(*this, presonus::surface::requireWifiUi())),
      state(owned->state), phase(owned->phase),
      dependencies(owned->dependencies), page(*this), timer(owned->timer) {
  paramList.add(firstParameters, 10, true);
  getParameterByTag(0)->setFeedbackNeeded(true);
  for (int row = 0; row < 5; ++row) {
    Core::Portable::ParamInfo infos[2]{};
    infos[0].type = Core::Portable::ParamInfo::kString;
    infos[0].tag = 100 + 2 * row;
    std::snprintf(infos[0].name, sizeof(infos[0].name), "name_%d", row + 1);
    infos[1].type = Core::Portable::ParamInfo::kToggle;
    infos[1].tag = 101 + 2 * row;
    std::snprintf(infos[1].name, sizeof(infos[1].name), "selected_%d", row + 1);
    infos[1].maxValue = 1.f;
    infos[1].deltaValue = 1.f;
    paramList.add(infos, 2, true);
  }
  paramList.add(finalParameters, 6, false);
  auto &manager = Presonus::WIFIManager::instance();
  manager.addDelegate(this);
  owned->registered = true;
  try {
    manager.doScan(true);
  } catch (...) {
    manager.removeDelegate(this);
    owned->registered = false;
    throw;
  }
}
} // namespace Presonus::Surface
