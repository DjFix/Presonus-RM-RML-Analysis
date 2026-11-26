#include "presonus/network/WIFIManager.hpp"
#include "core/network/corenetwork.h"
#include "core/portable/corefile.h"
#include "core/portable/corefilename.h"
#include "core/public/corememstream.h"
#include "core/system/coretime.h"
#include "presonus/application/SimpleReader.hpp"
#include <cstdio>
#include <cstdlib>
#include <cstring>

namespace presonus::network {
namespace {
class PosixWiFiEnvironment final : public WiFiEnvironment {
public:
  int command(const char *s) override { return std::system(s); }
  bool exists(const char *p) override {
    return Core::Portable::FileUtils::fileExists(p);
  }
  void remove(const char *p) override {
    Core::Portable::FileUtils::deleteFile(p);
  }
  bool read(const char *p, std::string &out) override {
    Core::Portable::FileStream f;
    if (!f.open(p, Core::IO::kReadMode))
      return false;
    char buf[512];
    int n;
    out.clear();
    while ((n = f.readBytes(buf, sizeof(buf))) > 0)
      out.append(buf, n);
    return true;
  }
  bool write(const char *p, const std::string &text) override {
    Core::Portable::FileStream f;
    if (!f.create(p))
      return false;
    // Original fputs/fclose results do not gate interface commands.
    f.writeBytes(text.data(), static_cast<int>(text.size()));
    return true;
  }
  bool pipe(const char *s, std::string &out) override {
    FILE *p = popen(s, "r");
    if (!p)
      return false;
    char line[127];
    out.clear();
    if (fgets(line, sizeof(line), p))
      out = line;
    pclose(p);
    return true;
  }
  void sleep(unsigned n) override { Core::Threads::CurrentThread::sleep(n); }
  long long milliseconds() override {
    return Core::SystemClock::toMilliseconds(Core::SystemClock::getTime());
  }
  std::string tempDirectory() override {
    Core::Portable::FileName p;
    Core::Portable::FileUtils::getTempDir(p);
    return p.str();
  }
  std::vector<std::pair<std::string, std::string>> addresses() override {
    Core::Sockets::IPAddress a[2];
    std::vector<std::pair<std::string, std::string>> out;
    int n = Core::Sockets::Network::getLocalIPAddressList(a, 2);
    for (int i = 0; i < n && i < 2; ++i) {
      Core::CString32 name;
      Core::CString256 ip;
      Core::Sockets::Network::getInterfaceNameForIP(name, a[i]);
      Core::Sockets::Network::getAddressString(ip, a[i]);
      out.emplace_back(name.str(), ip.str());
    }
    return out;
  }
};
WiFiEnvironment *testEnvironment = nullptr;
} // namespace
WiFiEnvironment &wifiEnvironment() {
  static PosixWiFiEnvironment production;
  return testEnvironment ? *testEnvironment : production;
}
void setWiFiEnvironmentForTesting(WiFiEnvironment *p) { testEnvironment = p; }
} // namespace presonus::network
DEFINE_SINGLETON(Presonus::WIFIManager)
namespace Presonus {
using presonus::network::wifiEnvironment;
WIFIManager::WIFIManager()
    : active("None"), worker(new Core::Portable::BackgroundWorker),
      staticIp("169.254.0.100") {
  auto &e = wifiEnvironment();
  scratch = e.tempDirectory().c_str();
  scratch.append("/scan.txt");
  scanDeadline = e.milliseconds() + 28000;
  otherDeadline = e.milliseconds() + 15000;
  resetStatusMsg();
}
WIFIManager::~WIFIManager() {
  Core::Threads::ScopedLock guard(lock);
  for (int i = 0; i < items.count(); ++i)
    delete items[i];
  items.resize(0);
  items.setCount(0);
  worker->terminate();
  delete worker;
}
void WIFIManager::terminate() { worker->terminate(); }
void WIFIManager::addDelegate(WIFIManagerDelegate *p) { delegates.add(p); }
void WIFIManager::removeDelegate(WIFIManagerDelegate *p) {
  for (int i = 0; i < delegates.count(); ++i)
    if (delegates[i] == p) {
      delegates.removeAt(i);
      break;
    }
}
void WIFIManager::adaptersChanged() { adaptersDirty = true; }
bool WIFIManager::doAdHoc(const char *) { return false; }
bool WIFIManager::isActive() const {
  return std::strcmp(active.str(), "None") != 0;
}
WIFIManager::NetworkItem *WIFIManager::find(const char *s) {
  Core::Threads::ScopedLock guard(lock);
  for (int i = 0; i < items.count(); ++i)
    if (std::strcmp(items[i]->ssid.str(), s ? s : "") == 0)
      return items[i];
  return nullptr;
}
void WIFIManager::setNetworkItems(Core::Vector<NetworkItem *> &from) {
  Core::Threads::ScopedLock guard(lock);
  for (int i = 0; i < items.count(); ++i)
    delete items[i];
  items = from;
  stateDirty = true;
}
void WIFIManager::setStatusMessage(const char *s) {
  Core::Threads::ScopedLock guard(lock);
  if (std::strcmp(status.str(), s ? s : "") != 0) {
    status = s;
    stateDirty = true;
  }
}
void WIFIManager::resetStatusMsg() { setStatusMessage("Store to Join"); }
void WIFIManager::setActiveNetwork(const char *s) {
  Core::Threads::ScopedLock guard(lock);
  if (std::strcmp(active.str(), s ? s : "") != 0) {
    active = s;
    stateDirty = true;
  }
}
void WIFIManager::setStaticIp(const char *s) { staticIp = s; }
const char *WIFIManager::getWifiIP() const {
  static Core::CString256 result;
  result = "";
  for (auto &a : wifiEnvironment().addresses())
    if (a.first != "eth0") {
      result = a.second.c_str();
      break;
    }
  return result.str();
}
const char *WIFIManager::getEthernetIP() const {
  static Core::CString256 result;
  result = "";
  for (auto &a : wifiEnvironment().addresses())
    if (a.first == "eth0") {
      result = a.second.c_str();
      break;
    }
  return result.str();
}
const char *WIFIManager::getIP() const {
  return std::strcmp(active.str(), "Ethernet") == 0 ? getEthernetIP()
                                                    : getWifiIP();
}
bool WIFIManager::NetworkItem::hasFlag(const char *flag) {
  Core::IO::MemoryStream stream(flags.getBuffer(), flags.length());
  SimpleReader reader(stream);
  Core::CStringBuffer<64> word;
  reader.advanceToNextChar('[');
  while (reader.getNextWord(word, ']')) {
    if (std::strstr(word.str(), flag ? flag : ""))
      return true;
    if (!reader.advanceToNextChar('['))
      break;
  }
  return false;
}
void WIFIManager::updateList(Core::Portable::ListParam *names,
                             Core::Portable::ListParam *levels,
                             Core::Portable::ListParam *icons, bool empty) {
  Core::Threads::ScopedLock guard(lock);
  if (!names)
    return;
  names->removeAll();
  if (levels)
    levels->removeAll();
  if (icons)
    icons->removeAll();
  for (int i = 0; i < items.count(); ++i) {
    auto *p = items[i];
    names->appendString(p->ssid);
    if (levels)
      levels->appendString(p->signal);
    if (icons) {
      bool locked = p->hasFlag("WEP") || p->hasFlag("WPA-PSK-TKIP") ||
                    p->hasFlag("WPA2-PSK-TKIP") || p->hasFlag("WPA-PSK-CCMP") ||
                    p->hasFlag("WPA2-PSK-CCMP");
      icons->appendString(locked ? "locked" : "unlocked");
    }
  }
  if (!items.count() && !empty) {
    names->appendString("None");
    if (levels)
      levels->appendString("0");
    if (icons)
      icons->appendString("unlocked");
  }
  auto notify = [](Core::Portable::ListParam *p) {
    if (p) {
      p->setValue(0);
      p->changed();
      p->rangeChanged();
    }
  };
  notify(levels);
  notify(icons);
  notify(names);
}
void WIFIManager::addTask(PipeTask *t) { worker->addTask(t); }
void WIFIManager::doScan(bool activeToo) {
  addTask(new ScanWIFITask);
  if (activeToo)
    addTask(new ActiveNetworkTask);
}
void WIFIManager::reconnect() {
  addTask(new ReconnectTask);
  doScan(true);
}
void WIFIManager::disconnect() {
  addTask(new DisconnectTask);
  doScan(true);
}
void WIFIManager::configNetwork(const char *iface, const char *ip,
                                const char *mask, const char *gateway,
                                bool dynamic, bool autoAssign) {
  auto *t = new ConfigNetworkTask;
  t->interfaceName = iface;
  t->ip = ip;
  t->subnet = mask;
  t->gateway = gateway;
  t->dynamic = dynamic;
  t->autoAssign = autoAssign;
  addTask(t);
}
bool WIFIManager::resetNetwork(const char *ssid, const char *key, bool wep) {
  auto *t = new JoinNetworkTask;
  t->ssid = ssid;
  t->key = key;
  t->wep = wep;
  t->encrypted = true;
  addTask(t);
  addTask(new ActiveNetworkTask);
  return false;
}
void WIFIManager::probeEth0() {
  auto *t = new StaticIpFailoverTask;
  t->interfaceName = "eth0";
  t->ip = staticIp;
  addTask(t);
}
void WIFIManager::onIdle() {
  if (stateDirty) {
    stateDirty = false;
    for (int i = 0; i < delegates.count(); ++i)
      delegates[i]->wifiStateChanged(this);
  }
  if (adaptersDirty) {
    for (int i = 0; i < delegates.count(); ++i)
      delegates[i]->wifiAdaptersChanged(this);
    adaptersDirty = false;
  }
  if (scanDeadline && wifiEnvironment().milliseconds() > scanDeadline) {
    scanDeadline = 0;
    doScan(true);
  }
}
} // namespace Presonus
