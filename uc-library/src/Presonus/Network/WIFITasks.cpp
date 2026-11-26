#include "core/public/corememstream.h"
#include "presonus/application/SimpleReader.hpp"
#include "presonus/network/WIFIManager.hpp"
#include <cstdio>
#include <cstring>
#include <memory>
namespace Presonus {
using presonus::network::wifiEnvironment;
namespace {
bool responseOK(const std::string &text, int expected) {
  Core::IO::MemoryStream stream(const_cast<char *>(text.data()),
                                static_cast<Core::uint32>(text.size()));
  SimpleReader r(stream);
  Core::CStringBuffer<256> line;
  while (r.getNextLine(line)) {
    if (std::strstr(line.str(), "OK"))
      return true;
    if (std::strstr(line.str(), "FAIL"))
      return false;
    long long n = 0;
    if (std::sscanf(line.str(), "%lld", &n) == 1)
      return n == expected;
  }
  return false;
}
} // namespace
WIFIManager::PipeTask::~PipeTask() {
  wifiEnvironment().sleep(200);
  WIFIManager::instance().resetStatusMsg();
}
void WIFIManager::PipeTask::setStatus(const char *s) {
  WIFIManager::instance().setStatusMessage(s);
}
bool WIFIManager::PipeTask::pipeOK(int expected) {
  auto &e = wifiEnvironment();
  auto p = WIFIManager::instance().scratchFile();
  std::string text;
  return e.exists(p) && e.read(p, text) && responseOK(text, expected);
}
bool WIFIManager::PipeTask::doCommand(const char *s, int n) {
  auto &e = wifiEnvironment();
  auto p = WIFIManager::instance().scratchFile();
  e.remove(p);
  Core::CStringBuffer<64> arg(s);
  if (n != -1)
    arg.appendFormat(" %d", n);
  Core::CStringBuffer<128> command("wpa_cli ");
  command.append(arg);
  command.append(" > ");
  command.append(p);
  e.command(command);
  return pipeOK(n);
}
WIFIManager::ActiveNetworkTask::~ActiveNetworkTask() = default;
WIFIManager::ReconnectTask::~ReconnectTask() = default;
WIFIManager::DisconnectTask::~DisconnectTask() = default;
WIFIManager::JoinNetworkTask::~JoinNetworkTask() = default;
WIFIManager::ConfigNetworkTask::~ConfigNetworkTask() = default;
WIFIManager::StaticIpFailoverTask::~StaticIpFailoverTask() = default;
WIFIManager::ScanWIFITask::~ScanWIFITask() = default;
void WIFIManager::ReconnectTask::work() {
  auto &m = WIFIManager::instance();
  m.setStatusMessage("reconnecting.");
  if (doCommand("reconnect", -1))
    m.retryState = 0;
}
void WIFIManager::DisconnectTask::work() {
  auto &m = WIFIManager::instance();
  m.setStatusMessage("disconnecting.");
  if (doCommand("disconnect", -1))
    m.retryState = 0;
}
void WIFIManager::ActiveNetworkTask::setNone() {
  WIFIManager::instance().setActiveNetwork("None");
}
bool WIFIManager::ActiveNetworkTask::isEthernet() {
  auto &e = wifiEnvironment();
  Core::CStringBuffer<128> path(e.tempDirectory().c_str());
  path.append("/ifconfig_tmp.txt");
  Core::CStringBuffer<128> cmd("ifconfig eth0 > ");
  cmd.append(path);
  e.command(cmd);
  std::string text;
  if (!e.exists(path) || !e.read(path, text))
    return false;
  Core::IO::MemoryStream stream(text.data(), text.size());
  SimpleReader r(stream);
  Core::CStringBuffer<64> ip;
  r.advanceToNextWord("inet addr:");
  r.getNextWord(ip, ' ');
  const char *current = WIFIManager::instance().getIP();
  return std::strstr(ip.str(), current ? current : "") == ip.str();
}
void WIFIManager::ActiveNetworkTask::work() {
  auto &e = wifiEnvironment();
  auto &m = WIFIManager::instance();
  e.remove(m.scratchFile());
  setStatus("scanning");
  e.sleep(1);
  doCommand("status", -1);
  setStatus("scanning.");
  e.sleep(100);
  setStatus("scanning..");
  e.sleep(100);
  setStatus("scanning...");
  std::string text;
  if (!e.exists(m.scratchFile()) || !e.read(m.scratchFile(), text)) {
    setNone();
    return;
  }
  Core::IO::MemoryStream stream(text.data(), text.size());
  SimpleReader r(stream);
  Core::CStringBuffer<256> line, ssid("None");
  while (r.getNextLine(line))
    if (std::strncmp(line.str(), "ssid=", 5) == 0) {
      ssid = line.str() + 5;
      break;
    }
  m.setActiveNetwork(isEthernet() ? "Ethernet" : ssid.str());
}
void WIFIManager::ConfigNetworkTask::work() {
  config();
  WIFIManager::instance().adaptersChanged();
}
void WIFIManager::JoinNetworkTask::work() {
  auto &m = WIFIManager::instance();
  auto &e = wifiEnvironment();
  m.retryState = 0;
  setStatus("joining.");
  e.remove(m.scratchFile());
  if (doCommand("remove_network all", -1)) {
    doCommand("ap_scan", 1);
    if (!doCommand("add_network", 0)) {
      m.retryState = 1;
      return;
    }
  }
  Core::CStringBuffer<256> cmd;
  cmd.appendFormat("set_network %d ssid '\"%s\"'", 0, ssid.str());
  if (!doCommand(cmd, -1)) {
    m.retryState = 2;
    return;
  }
  e.remove(m.scratchFile());
  if (!encrypted || wep) {
    if (!doCommand("set_network 0 key_mgmt NONE", -1)) {
      m.retryState = 5;
      return;
    }
  }
  if (encrypted) {
    if (wep)
      e.remove(m.scratchFile());
    cmd = "";
    cmd.appendFormat(wep ? "set_network %d wep_key0 '\"%s\"'"
                         : "set_network %d psk '\"%s\"'",
                     0, key.str());
    doCommand(cmd, -1);
    if (!pipeOK(-1)) {
      m.retryState = 3;
      return;
    }
    if (!wep) {
      e.remove(m.scratchFile());
      cmd = "";
      cmd.appendFormat("set_network %d priority 5", 0);
      doCommand(cmd, -1);
      if (!pipeOK(-1)) {
        m.retryState = 9;
        return;
      }
    }
  }
  setStatus("joining..");
  if (!doCommand("select_network", 0)) {
    m.retryState = 4;
    return;
  }
  doCommand("save_config", -1);
  e.command("ifdown wlan0");
  e.sleep(1000);
  e.command("ifup wlan0");
  for (auto s : {"joining..", "joining...", "joining...", "joining....",
                 "joining....."}) {
    setStatus(s);
    e.sleep(1000);
  }
  m.retryState = 0;
}
int WIFIManager::doJoin(const char *name, const char *key) {
  auto *p = find(name);
  if (!p)
    return 7;
  auto *t = new JoinNetworkTask;
  t->ssid = name;
  t->key = key;
  t->wep = p->hasFlag("WEP");
  t->encrypted = t->wep || p->hasFlag("WPA-PSK-TKIP") ||
                 p->hasFlag("WPA2-PSK-TKIP") || p->hasFlag("WPA-PSK-CCMP") ||
                 p->hasFlag("WPA2-PSK-CCMP");
  addTask(t);
  addTask(new ActiveNetworkTask);
  return 0;
}
} // namespace Presonus

namespace Presonus {
void WIFIManager::ScanWIFITask::work() {
  auto &e = wifiEnvironment();
  auto &m = WIFIManager::instance();
  e.remove(m.scratchFile());
  setStatus("scanning.");
  doCommand("scan", -1);
  e.sleep(200);
  setStatus("scanning..");
  e.sleep(200);
  setStatus("scanning...");
  e.sleep(200);
  setStatus("scanning....");
  doCommand("scan_results", -1);
  setStatus("scanning....");
  std::string text;
  if (!e.exists(m.scratchFile()) || !e.read(m.scratchFile(), text))
    return;
  for (int i = 0; i < items.count(); ++i)
    delete items[i];
  items.resize(0);
  items.setCount(0);
  Core::IO::MemoryStream stream(text.data(), text.size());
  SimpleReader r(stream);
  Core::CStringBuffer<256> line;
  Core::CStringBuffer<64> word;
  while (true) {
    auto pos = stream.getPosition();
    if (!r.getNextLine(line))
      break;
    if (std::strstr(line.str(), "bssid") || std::strstr(line.str(), "Selected"))
      continue;
    stream.setPosition(pos, Core::IO::kSeekSet);
    r.getNextWord(word, '\t');
    if (word.length() <= 16 || word.str()[2] != ':')
      continue;
    auto *p = new NetworkItem;
    p->bssid = word;
    r.getNextWord(p->frequency, '\t');
    r.getNextWord(p->signal, '\t');
    r.getNextWord(p->flags, '\t');
    r.getNextWord(p->ssid, '\t');
    if (p->ssid.isEmpty())
      continue;
    bool duplicate = false;
    for (int i = 0; i < items.count(); ++i)
      if (items[i] && std::strcmp(items[i]->ssid.str(), p->ssid.str()) == 0) {
        duplicate = true;
        break;
      }
    if (duplicate)
      delete p;
    else
      items.add(p);
  }
  m.setNetworkItems(items);
  m.getIP();
}
void WIFIManager::ConfigNetworkTask::config() {
  auto &e = wifiEnvironment();
  Core::CStringBuffer<32> path("config-");
  path.append(interfaceName);
  if (autoAssign) {
    Core::CStringBuffer<256> setup;
    setup.appendFormat("auto eth0\niface eth0 inet static\naddress %s\nnetmask "
                       "%s\ngateway %s\n",
                       "169.254.1.254", "255.255.0.0", "169.254.1.100");
    if (e.write(path, std::strcmp(interfaceName.str(), "eth0") == 0
                          ? setup.str()
                          : "")) {
      Core::CStringBuffer<32> down("ifdown ");
      down.append(interfaceName);
      e.command(down);
      e.sleep(5000);
      Core::CStringBuffer<32> up("ifup ");
      up.append(interfaceName);
      up.append(" -i ");
      up.append(path);
      e.command(up);
      e.sleep(5000);
    }
    bool available = false;
    if (std::strncmp(ip.str(), "169.254.1.", 10) == 0) {
      Core::CStringBuffer<128> ping;
      ping.appendFormat("ping -c1 -W1 -q %s", ip.str());
      available = e.command(ping) != 0;
    }
    if (!available) {
      for (int tries = 0; tries < 20; ++tries) {
        std::srand(static_cast<unsigned>(e.milliseconds() / 1000));
        int suffix = static_cast<int>(static_cast<float>(std::rand()) *
                                      0x1p-31f * 98.f) +
                     1;
        Core::CStringBuffer<128> ping;
        ping.appendFormat("ping -c1 -W1 -q %s%d", "169.254.1.", suffix);
        if (e.command(ping) != 0) {
          ip = "";
          ip.appendFormat("%s%d", "169.254.1.", suffix);
          break;
        }
      }
    }
    gateway = "169.254.1.100";
    subnet = "255.255.0.0";
  }
  Core::CStringBuffer<256> loop("auto lo\niface lo inet loopback\n"),
      ethernet("auto eth0\niface eth0 inet "),
      wifi("auto wlan0\niface wlan0 inet dhcp\nwireless_mode "
           "managed\nwireless_essid any\nwpa-conf /etc/wpa_supplicant.conf");
  if (dynamic)
    ethernet.append("dhcp\n");
  else {
    ethernet.append("static\naddress ");
    ethernet.append(ip);
    ethernet.append("\n");
    ethernet.append("netmask ");
    if (subnet.isEmpty())
      subnet = "255.255.0.0";
    ethernet.append(subnet);
    ethernet.append("\n");
    if (!gateway.isEmpty()) {
      ethernet.append("gateway ");
      ethernet.append(gateway);
      ethernet.append("\n");
    }
  }
  if (!e.write(path, std::string(loop.str()) + ethernet.str() + wifi.str()))
    return;
  Core::CStringBuffer<32> down("ifdown -a");
  e.command(down);
  e.sleep(5000);
  Core::CStringBuffer<32> up("ifup -a -i ");
  up.append(path);
  e.command(up);
}
} // namespace Presonus

namespace Presonus {
void WIFIManager::StaticIpFailoverTask::work() {
  auto &e = wifiEnvironment();
  Core::CStringBuffer<128> query("ip -o -f inet addr | grep ");
  query.append(interfaceName);
  std::string line;
  if (!e.pipe(query, line) || !line.empty()) {
    setStatus("eth0: valid IP lease.");
    return;
  }
  const std::string head =
      "auto lo                                   \n                            "
      "   iface lo inet loopback                    \n                         "
      "      auto eth0                                 \n                      "
      "         iface eth0 inet static                    \n                   "
      "             address ";
  const std::string tail =
      "netmask 255.255.0.0                    \n                               "
      " gateway 169.254.0.10                     \n                            "
      "   auto wlan0                                \n                         "
      "      iface wlan0 inet dhcp                     \n                      "
      "          wireless_mode managed                    \n                   "
      "             wireless_essid any                       \n                "
      "                wpa-conf /etc/wpa_supplicant.conf";
  if (e.write("static-eth0", head + ip.str() + "\n" + tail)) {
    e.command("ifdown -a ");
    e.sleep(5000);
    e.command("ifup -ai static-eth0 ");
    WIFIManager::instance().adaptersChanged();
  }
  setStatus("eth0: assigning static IP");
}
} // namespace Presonus
