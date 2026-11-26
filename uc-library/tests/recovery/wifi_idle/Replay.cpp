#include "presonus/surface/WifiSetupComponent.hpp"
#include <array>
#include <cstring>
#include <iostream>
#include <memory>
#include <string>
#include <vector>
// Use the accepted production WIFIManager; fixture dependencies own
// observations.
namespace {
using namespace Core::Portable;
std::uint32_t bits(float v) {
  std::uint32_t n;
  std::memcpy(&n, &v, 4);
  return n;
}
float fromBits(std::uint32_t n) {
  float v;
  std::memcpy(&v, &n, 4);
  return v;
}
std::string hex(const char *text) {
  std::string result;
  for (auto *p = reinterpret_cast<const unsigned char *>(text); *p; ++p) {
    result += "0123456789abcdef"[*p >> 4];
    result += "0123456789abcdef"[*p & 15];
  }
  return result.empty() ? "-" : result;
}
void textEvent(int tag, const char *text, bool edit) {
  std::cout << "T " << tag << ' ' << edit << ' ' << hex(text) << '\n';
}
struct Param : NumericParam {
  explicit Param(const ParamInfo &info) : NumericParam(info, true) {}
  void fromString(const char *s, bool edit) override {
    textEvent(getTag(), s, edit);
  }
  void setValue(float v, bool edit) override {
    std::cout << "V " << getTag() << ' ' << bits(v) << ' ' << edit << '\n';
    value = v;
  }
  void enable(bool enabled) override {
    std::cout << "E " << getTag() << ' ' << enabled << '\n';
  }
  void seed(float v) { value = v; }
};
struct Dependencies : presonus::surface::WifiSetupDependencies {
  bool shown, expired, exists, found;
  int flags;
  std::string signal;
  const void *expectedOwner = nullptr;
  void pageOnShow(bool v) override { std::cout << "SHOW " << v << '\n'; }
  void startPasswordInput(Parameter *p, const char *prompt,
                          const void *owner) override {
    std::cout << "INPUT " << p->getTag() << ' ' << hex(prompt) << ' '
              << (owner == expectedOwner) << '\n';
  }
  void ensureManager() const override {
    if (!exists) {
      std::cout << "INIT\n";
      const_cast<Dependencies *>(this)->exists = true;
    }
  }
  void updateList(ListParam *a, ListParam *b, ListParam *c,
                  bool refresh) const override {
    std::cout << "LIST " << refresh << ' ' << a->getTag() << ' ' << b->getTag()
              << ' ' << c->getTag() << '\n';
  }
  bool findNetwork(const char *ssid) const override {
    std::cout << "FIND " << hex(ssid) << '\n';
    return found;
  }
  bool networkHasFlag(const char *flag) const override {
    std::cout << "FLAG " << hex(flag) << '\n';
    return (flags & (std::strcmp(flag, "WEP") == 0            ? 1
                     : std::strcmp(flag, "WPA-PSK-TKIP") == 0 ? 2
                                                              : 4)) != 0;
  }
  const char *managerStatus(const Presonus::WIFIManager &) const override {
    return "connected";
  }
  const char *managerSSID(const Presonus::WIFIManager &) const override {
    return "net2";
  }
  const char *managerIP(const Presonus::WIFIManager &) const override {
    return "192.0.2.1";
  }
  const char *networkSignal() const override { return signal.c_str(); }
  void scan(bool v) override { std::cout << "SCAN " << v << '\n'; }
};
struct PageBindings : presonus::page::Bindings {
  bool visible;
  const void *page = nullptr;
  void *castOwner(void *owner, int) const override { return owner; }
  const void *currentPage(void *) const override {
    return visible ? page : nullptr;
  }
  void stopTextInput(void *, bool) const override {}
  bool isEditingText(void *) const override { return false; }
};
class Fixture : public Presonus::Surface::WifiSetupComponent {
public:
  using WifiSetupComponent::WifiSetupComponent;
  void add(Parameter *p) { paramList.add(p); }
};
} // namespace
extern "C" void
__real__ZN8Presonus10DelayTimer11beginActionEf(Presonus::DelayTimer *, float);
extern "C" bool
__real__ZN8Presonus10DelayTimer9endActionEv(Presonus::DelayTimer *);
extern "C" void
__wrap__ZN8Presonus10DelayTimer11beginActionEf(Presonus::DelayTimer *timer,
                                               float seconds) {
  std::cout << "BEGIN " << bits(seconds) << '\n';
  __real__ZN8Presonus10DelayTimer11beginActionEf(timer, seconds);
}
extern "C" bool
__wrap__ZN8Presonus10DelayTimer9endActionEv(Presonus::DelayTimer *timer) {
  std::cout << "END\n";
  return __real__ZN8Presonus10DelayTimer9endActionEv(timer);
}

struct Child : Core::Portable::Component {
  int id;
  explicit Child(int id) : id(id) {}
  void onIdle() override { std::cout << "CHILD " << id << '\n'; }
};
int main() {
  int expired, initial, children;
  while (std::cin >> expired >> initial >> children) {
    presonus::surface::WifiSetupState state{};
    presonus::surface::WifiScanPhase scan{initial != 0};
    Dependencies deps{};
    deps.exists = true;
    PageBindings binding{};
    Presonus::PageComponent page(&binding, binding);
    Presonus::DelayTimer timer(1.f);
    presonus::timing::DelayTimerAccess::set(timer,
                                            {0, expired ? 0 : 1, 0, 0, false});
    Fixture f(state, scan, deps, page, timer);
    std::array<Core::Portable::ParamInfo, 3> info{};
    for (int tag = 0; tag < 3; ++tag) {
      info[tag].type = Core::Portable::ParamInfo::kList;
      info[tag].tag = tag;
      f.add(new Core::Portable::ListParam(info[tag]));
    }
    for (int i = 0; i < children; ++i)
      f.addChild(new Child(i));
    f.onIdle();
    std::cout << "STATE " << scan.refreshNext << ' ' << timer.isExecuting()
              << '\n';
  }
}
