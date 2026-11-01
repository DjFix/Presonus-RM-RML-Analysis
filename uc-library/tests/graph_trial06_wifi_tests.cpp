#include "presonus/surface/WifiSetupComponent.hpp"
#include <cstring>
#include <iostream>
#include <memory>
#include <string>
#include <vector>
// Fixture-only complete opaque token; production never defines WIFIManager.
namespace Presonus {
class WIFIManager {};
} // namespace Presonus
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
int main() {
  int method, offset, selected, delta, tag, msg, visible, expired, phase,
      exists, missing, found, flags, signal, count, show;
  std::uint32_t value;
  while (std::cin >> method >> offset >> selected >> delta >> tag >> value >>
         msg >> visible >> expired >> phase >> exists >> missing >> found >>
         flags >> signal >> count >> show) {
    presonus::surface::WifiSetupState state{offset, selected};
    presonus::surface::WifiScanPhase scan{phase != 0};
    Dependencies deps;
    deps.shown = visible;
    deps.expired = expired;
    deps.exists = exists;
    deps.found = found;
    deps.flags = flags;
    deps.signal = std::to_string(signal);
    PageBindings binding;
    binding.visible = visible;
    Presonus::PageComponent page(&binding, binding);
    binding.page = &page;
    Presonus::DelayTimer timer(1.f);
    presonus::timing::DelayTimerAccess::set(timer,
                                            {0, expired ? 0 : 1, 0, 0, false});
    Fixture f(state, scan, deps, page, timer);
    deps.expectedOwner = &f;
    std::vector<std::string> strings;
    std::vector<const char *> names;
    for (int i = 0; i < count; ++i)
      strings.push_back("net" + std::to_string(i));
    for (auto &str : strings)
      names.push_back(str.c_str());
    for (int t : {0,   1,   2,    3,    4,    5,    6,    7,   8,
                  9,   100, 101,  102,  103,  104,  105,  106, 107,
                  108, 109, 1000, 1001, 1002, 1003, 1004, 1005}) {
      if (t == missing)
        continue;
      auto *info = new ParamInfo{};
      info->tag = t;
      info->minValue = -10000;
      info->maxValue = 10000;
      if (t < 3 && missing != 2000 + t) {
        info->type = ParamInfo::kList;
        info->minValue = 0;
        info->maxValue = count - 1;
        auto *p = new ListParam(*info, true);
        p->setSharedStrings(names.data(), count);
        f.add(p);
      } else {
        info->type = ParamInfo::kFloat;
        auto *p = new Param(*info);
        if (t == tag)
          p->seed(fromBits(value));
        f.add(p);
      }
    }
    auto *changed = f.getParameterByTag(tag);
    std::unique_ptr<Param> separate;
    if (!changed) {
      auto *info = new ParamInfo{};
      info->tag = tag;
      info->minValue = -10000;
      info->maxValue = 10000;
      separate = std::make_unique<Param>(*info);
      separate->seed(fromBits(value));
      changed = separate.get();
    }
    Core::CStringBuffer<64> output("unchanged");
    int result = 0;
    Presonus::WIFIManager manager;
    switch (method) {
    case 1:
      f.connect();
      break;
    case 2:
      f.addListOffset(delta);
      break;
    case 3:
      f.paramChanged(changed, msg);
      break;
    case 4:
      result = f.getMaxListOffset();
      break;
    case 5:
      f.networkChanged(manager);
      break;
    case 6:
      f.getSelectedSSID(output);
      break;
    case 7:
      f.updateNetworkList(show);
      break;
    case 8:
      f.onShow(show);
      break;
    case 9:
      f.updateDisplayList();
      break;
    case 10:
      f.checkNetworkScanning();
      break;
    default:
      return 2;
    }
    std::cout << "S " << state.listOffset << ' ' << state.selected << ' '
              << scan.refreshNext << ' ' << hex(output) << ' ' << result << ' '
              << timer.isExecuting() << '\n';
  }
}
