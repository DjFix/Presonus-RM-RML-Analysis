#include "presonus/mixer/NetworkSelectComponent.hpp"
#include "core/system/coredebug.h"
#include <cstdio>
#include <cstring>
#include <stdexcept>

namespace {
unsigned char scanToggle = 0;
bool due(Presonus::DelayTimer *timer,
         presonus::network_select::FixtureTimer *fixture) {
  if (fixture)
    return fixture->longEnough();
  if (!timer)
    throw std::logic_error("NetworkSelectComponent timers are not configured");
  return timer->isLongEnoughYet();
}
} // namespace
namespace Presonus::Mixer {
void NetworkSelectComponent::configureFixtureToggle(unsigned char value) {
  scanToggle = value;
}
void NetworkSelectComponent::idleScanning() {
  // The native comparison suppresses scanning exactly for zero (including -0).
  if (scanning && scanning->getValue() == 0.f)
    return;
  if (!due(scanningTimer, fixtureScan))
    return;
  Core::DebugPrint("NetworkSelectComponent::checkNetworkScanning:\n");
  scanToggle ^= 1;
  if (scanToggle)
    services.scan(false);
  else
    updateNetworkList(false);
  if (fixtureScan)
    fixtureScan->begin(-1.f);
  else
    scanningTimer->beginAction(-1.f);
}
void NetworkSelectComponent::notify(
    const Presonus::UC::MessageAttributes &msg) {
  services.serverNotify(msg);
  const char *id = msg.getID();
  if (!id || std::strcmp(id, "requestNetworkChange") != 0)
    return;
  const char *ssid = msg.getString("requestNetworkSSID");
  const char *pw = msg.getString("requestNetworkPw");
  if (!ssid)
    ssid = "";
  if (!pw)
    pw = "";
  Core::DebugPrintf(
      "NetworkSelectComponent::notify kRequestNetworkChange ssid=%s  pw=%s\n",
      ssid, pw);
  services.join(ssid, pw);
}
int NetworkSelectComponent::getWiredNetworkAssignMode() const {
  const auto *p = getParameterByTag(11);
  return p ? static_cast<int>(p->getValue()) : 0;
}
void NetworkSelectComponent::networkChanged(
    const Presonus::WIFIManager &manager) {
  updateNetworkList(true);
  getParameterByTag(4)->fromString(services.managerName(manager), false);
  const char *ssid = services.managerSSID(manager);
  getParameterByTag(5)->fromString(ssid, false);
  getParameterByTag(10)->fromString(services.managerIP(manager, 0), false);
  getParameterByTag(13)->fromString(services.managerIP(manager, 1), false);
  getParameterByTag(22)->fromString(services.managerIP(manager, 2), false);
  getParameterByTag(20)->resetValue(true);
  getParameterByTag(23)->resetValue(true);
  const void *item = services.find(ssid);
  if (item) {
    long long value = 0;
    std::sscanf(services.signalText(item), "%lld", &value);
    getParameterByTag(9)->setValue(static_cast<float>(value) * 0.01f, false);
  }
}
void NetworkSelectComponent::onIdle() {
  Core::Portable::Component::onIdle();
  services.idle();
  idleTasks();
}
void NetworkSelectComponent::adaptorConfigChanged(
    const Presonus::WIFIManager &) {
  Core::DebugPrintf("UCNET: un-suspending network adaptors\n");
  services.suspendAdaptors(false);
  getParameterByTag(24)->resetValue(true);
}
void NetworkSelectComponent::getSelectedSSID(Core::CStringBuffer<64> &output) {
  getParameterByTag(0)->toString(output.getBuffer(), 64);
  getParameterByTag(6)->fromString(output.str(), false);
  const void *item = services.find(output.str());
  if (!item)
    return;
  if (services.hasFlag(item, "WEP"))
    getParameterByTag(7)->fromString("WEP", false);
  else if (services.hasFlag(item, "WPA-PSK-TKIP") ||
           services.hasFlag(item, "WPA2-PSK-TKIP"))
    getParameterByTag(7)->fromString("WPA/WPA2", false);
}
void NetworkSelectComponent::idleTasks() {
  if (!due(configurationTimer, fixtureConfig)) {
    idleScanning();
    return;
  }
  if (fixtureConfig)
    fixtureConfig->reset();
  else
    configurationTimer->reset();
  Core::DebugPrintf("NetworkSelectComponent: about to configure network "
                    "adaptors mode: %d...\n",
                    getWiredNetworkAssignMode());
  if (getWiredNetworkAssignMode() == 0) {
    Core::DebugPrintf("UCNET: un-suspending network adaptors\n");
    services.suspendAdaptors(false);
  } else
    services.configureInterface("-a");
}
void NetworkSelectComponent::updateNetworkList(bool changed) const {
  auto *a = Core::Portable::ListParam::cast(getParameterByTag(0));
  auto *b = Core::Portable::ListParam::cast(getParameterByTag(1));
  auto *c = Core::Portable::ListParam::cast(getParameterByTag(2));
  if (a && b && c)
    services.updateList(a, b, c, !changed);
}
void NetworkSelectComponent::disconnect() {
  selection = "";
  services.join(selection.str(), selection.str());
  getParameterByTag(0)->setValue(0.f, false);
}
} // namespace Presonus::Mixer
