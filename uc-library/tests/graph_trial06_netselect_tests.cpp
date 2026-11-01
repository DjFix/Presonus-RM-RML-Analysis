#include "presonus/mixer/NetworkSelectComponent.hpp"
#include <array>
#include <cstdint>
#include <cstring>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>

namespace {
std::vector<std::string> events;
std::string hex(const char *text) {
  static const char digits[] = "0123456789abcdef";
  std::string out;
  for (; *text; ++text) {
    const auto ch = static_cast<unsigned char>(*text);
    out += digits[ch >> 4];
    out += digits[ch & 15];
  }
  return out.empty() ? "-" : out;
}
std::uint32_t bits(float value) {
  std::uint32_t result;
  std::memcpy(&result, &value, 4);
  return result;
}
float real(std::uint32_t value) {
  float result;
  std::memcpy(&result, &value, 4);
  return result;
}
std::string selected(int n) {
  return (std::string("SSID") + std::string(n > 4 ? n - 4 : 0, 'x'))
      .substr(0, n);
}
template <class Base> struct Param : Base {
  float value = 0;
  std::string text;
  explicit Param(const Core::Portable::ParamInfo &info) : Base(info) {}
  float getValue() const override {
    events.push_back("get:" + std::to_string(this->getTag()) + ":" +
                     std::to_string(bits(value)));
    return value;
  }
  void setValue(float v, bool edit = false) override {
    value = v;
    events.push_back("set:" + std::to_string(this->getTag()) + ":" +
                     std::to_string(bits(v)) + ":" + std::to_string(edit));
  }
  void resetValue(bool edit = false) override {
    events.push_back("reset:" + std::to_string(this->getTag()) + ":" +
                     std::to_string(edit));
  }
  void fromString(const char *s, bool edit = false) override {
    text = s;
    events.push_back("from:" + std::to_string(this->getTag()) + ":" + hex(s) +
                     ":" + std::to_string(edit));
  }
  void toString(char *s, int n) const override {
    if (n > 0) {
      std::strncpy(s, text.c_str(), n - 1);
      s[n - 1] = 0;
    }
    events.push_back("to:" + std::to_string(this->getTag()) + ":" + hex(s));
  }
};
struct Timer : presonus::network_select::FixtureTimer {
  int index;
  bool ready;
  Timer(int i, bool r) : index(i), ready(r) {}
  bool longEnough() const override {
    events.push_back("due:" + std::to_string(index) + ":" +
                     std::to_string(ready));
    return ready;
  }
  void reset() override {
    events.push_back("timer-reset:" + std::to_string(index));
  }
  void begin(float s) override {
    events.push_back("begin:" + std::to_string(index) + ":" +
                     std::to_string(bits(s)));
  }
};
struct Services : presonus::network_select::NetworkServices {
  bool found;
  unsigned flags;
  std::string signal;
  void serverNotify(const Presonus::UC::MessageAttributes &) override {
    events.push_back("server-notify");
  }
  void scan(bool b) override { events.push_back("scan:" + std::to_string(b)); }
  void idle() override { events.push_back("wifi-idle"); }
  void join(const char *a, const char *b) override {
    events.push_back("join:" + hex(a) + ":" + hex(b));
  }
  void updateList(Core::Portable::ListParam *a, Core::Portable::ListParam *b,
                  Core::Portable::ListParam *c, bool d) override {
    events.push_back("list:" + std::to_string(a->getTag()) + ":" +
                     std::to_string(b->getTag()) + ":" +
                     std::to_string(c->getTag()) + ":" + std::to_string(d));
  }
  void suspendAdaptors(bool b) override {
    events.push_back("suspend:" + std::to_string(b));
  }
  void configureInterface(const char *s) override {
    events.push_back("configure:" + hex(s));
  }
  const char *managerName(const Presonus::WIFIManager &) const override {
    return "adapter";
  }
  const char *managerSSID(const Presonus::WIFIManager &) const override {
    return "connected";
  }
  const char *managerIP(const Presonus::WIFIManager &, int i) override {
    static const char *ips[] = {"10.0.0.1", "10.0.0.2", "10.0.0.3"};
    return ips[i];
  }
  const void *find(const char *s) override {
    events.push_back("find:" + hex(s));
    return found ? this : nullptr;
  }
  bool hasFlag(const void *, const char *s) override {
    const unsigned bit = std::strcmp(s, "WEP") == 0            ? 1
                         : std::strcmp(s, "WPA-PSK-TKIP") == 0 ? 2
                                                               : 4;
    const bool result = (flags & bit) != 0;
    events.push_back("flag:" + hex(s) + ":" + std::to_string(result));
    return result;
  }
  const char *signalText(const void *) const override { return signal.c_str(); }
};
struct Component : Presonus::Mixer::NetworkSelectComponent {
  using NetworkSelectComponent::NetworkSelectComponent;
  void add(Core::Portable::Parameter *p) { paramList.add(p); }
};
struct Child : Core::Portable::Component {
  void onIdle() override { events.push_back("child-idle"); }
};
void run(const std::array<std::uint32_t, 18> &c) {
  static const char *signals[] = {
      "-64",   "75", "invalid", "922337203685477580", "-922337203685477580",
      "12tail"};
  Services service;
  service.found = c[9];
  service.flags = c[10];
  service.signal = signals[c[14]];
  std::array<Core::Portable::ParamInfo, 26> infos{};
  Component component(service);
  for (int i = 0; i < 25; ++i) {
    if (i == 11 && !c[6])
      continue;
    if (i < 3 && !(c[8] & (1u << i)))
      continue;
    infos[i].tag = i;
    infos[i].type = Core::Portable::ParamInfo::kFloat;
    infos[i].minValue = -100;
    infos[i].maxValue = 100;
    Core::Portable::Parameter *p;
    if (i < 3 && (c[8] & (1u << (i + 3)))) {
      auto *list = new Param<Core::Portable::ListParam>(infos[i]);
      list->text = selected(c[16]);
      p = list;
    } else {
      auto *number = new Param<Core::Portable::NumericParam>(infos[i]);
      number->value = real(c[7]);
      number->text = selected(c[16]);
      p = number;
    }
    component.add(p);
  }
  infos[25].tag = 99;
  infos[25].type = Core::Portable::ParamInfo::kFloat;
  Param<Core::Portable::NumericParam> scan(infos[25]);
  scan.value = real(c[3]);
  component.configureScanningParameter(c[2] ? &scan : nullptr);
  Timer scanTimer(0, c[4]), configTimer(1, c[5]);
  component.configureFixtureTimers(scanTimer, configTimer);
  component.configureFixtureToggle(c[1]);
  // Opaque identity token is never dereferenced by the independent provider.
  alignas(void *) unsigned char managerToken[sizeof(void *)]{};
  const auto &manager =
      *reinterpret_cast<const Presonus::WIFIManager *>(managerToken);
  Core::CStringBuffer<64> out("unchanged");
  Presonus::UC::MessageAttributes msg(c[11] == 0   ? nullptr
                                      : c[11] == 1 ? "requestNetworkChange"
                                                   : "other");
  if (c[12])
    msg.set("requestNetworkSSID", "joinSSID");
  if (c[13])
    msg.set("requestNetworkPw", "secret");
  if (c[0] == 5)
    component.addChild(new Child);
  events.clear();
  switch (c[0]) {
  case 1:
    component.idleScanning();
    break;
  case 2:
    component.notify(msg);
    break;
  case 3:
    events.push_back("return:" +
                     std::to_string(component.getWiredNetworkAssignMode()));
    break;
  case 4:
    component.networkChanged(manager);
    break;
  case 5:
    component.onIdle();
    break;
  case 6:
    component.adaptorConfigChanged(manager);
    break;
  case 7:
    component.getSelectedSSID(out);
    events.push_back("output:" + hex(out.str()));
    break;
  case 8:
    component.idleTasks();
    break;
  case 9:
    component.updateNetworkList(c[15]);
    break;
  case 10:
    component.disconnect();
    events.push_back("selection:" + hex(component.portSelection()));
    break;
  default:
    throw std::runtime_error("unknown target");
  }
  std::cout << "OBS";
  for (const auto &e : events)
    std::cout << ' ' << e;
  std::cout << '\n';
}
} // namespace
int main() {
  std::array<std::uint32_t, 18> c{};
  while (std::cin >> c[0]) {
    for (unsigned i = 1; i < c.size(); ++i)
      if (!(std::cin >> c[i]))
        return 2;
    run(c);
  }
}
