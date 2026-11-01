#include "presonus/surface/WifiSetupComponent.hpp"
#include <cstdio>
namespace Presonus::Surface {
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
