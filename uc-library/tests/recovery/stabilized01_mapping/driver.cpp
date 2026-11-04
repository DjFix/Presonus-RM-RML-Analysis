#include "presonus/MappablePageComponent.hpp"
#include "presonus/MappingTable.hpp"
#include "presonus/panel/control.hpp"
#include "presonus/surface/MappingComponent.hpp"
#include "presonus/surface/PageParam.hpp"
#include <cstdlib>
#include <iomanip>
#include <iostream>
#include <string>
#include <vector>
using namespace Core::Portable;
namespace {
const char *nullable(const char *s) {
  return std::string(s) == "-" ? nullptr : s;
}
ParamInfo info(int tag, const char *name, int type = ParamInfo::kInt) {
  ParamInfo p{};
  p.type = type;
  p.tag = tag;
  std::strncpy(p.name, name, 31);
  p.maxValue = 1;
  return p;
}
void emit(const std::vector<std::string> &calls) {
  std::cout << '[';
  bool first = true;
  for (auto &s : calls) {
    if (!first)
      std::cout << ',';
    first = false;
    std::cout << s;
  }
  std::cout << ']';
}
struct LegacyReject : presonus::mapping::ItemOperations {
  void fullOff(Presonus::MappingTable::Item &) override { std::abort(); }
  void inverseMode(Presonus::MappingTable::Item &, bool) override {
    std::abort();
  }
  void enabled(Presonus::MappingTable::Item &, bool) override { std::abort(); }
  void immediate(Presonus::MappingTable::Item &, bool) override {
    std::abort();
  }
};
// Virtual hardware observations are fixture boundaries; actual
// Control::getParameter and CCL AliasParam/observer code execute. No hardware
// behavior is claimed.
struct ProviderSignal final : ParamObserverBase {
  bool pending = false;
  int actualSignals = 0;
  void paramChanged(Parameter *, int msg) override {
    if (msg == Parameter::kChanged) {
      pending = true;
      ++actualSignals;
    }
  }
};
struct ControlProbe : Presonus::Panel::Control {
  ControlProbe(std::vector<std::string> &c) : Control(9), calls(c) {}
  std::vector<std::string> &calls;
  int mode = 0;
  ProviderSignal *provider = nullptr;
  bool setting = false;
  int providerBroadcasts = 0;
  int providerParameterCallbacks = 0;
  bool setParameter(Parameter *p, int m) override {
    calls.push_back("[\"set\"," + std::to_string(p != nullptr) + "," +
                    std::to_string(m) + "]");
    mode = m;
    setting = true;
    bool result = Control::setParameter(p, m);
    setting = false;
    if (provider)
      provider->pending = false;
    return result;
  }
  int getParameterMode() const override { return mode; }
  void broadcastValue(int value) override {
    if (!setting)
      calls.push_back("[\"broadcast\"," + std::to_string(value) + "]");
    else
      ++providerBroadcasts;
    Control::broadcastValue(value);
  }
  void paramChanged(Parameter *p, int msg) override {
    if (msg == Parameter::kChanged && setting)
      ++providerParameterCallbacks;
    if (msg == 3 && !setting) {
      if (provider && provider->pending)
        provider->pending = false;
      else
        calls.push_back("[\"notify\",3]");
    }
    Control::paramChanged(p, msg);
  }
};
struct PageProbe : Presonus::MappablePageComponent {
  PageProbe(std::vector<std::string> &c)
      : MappablePageComponent("p"), calls(c) {
    addMappable(1, "gain");
  }
  std::vector<std::string> &calls;
  bool connectParameter(const char *n, Parameter *p) override {
    calls.push_back("[\"connectpage\",\"" + std::string(n) + "\"," +
                    std::to_string(p != nullptr) + "]");
    return MappablePageComponent::connectParameter(n, p);
  }
};
struct MappingProbe : Presonus::Surface::MappingComponent {
  MappingProbe() : MappingComponent(presonus::surface::MappingRouteInit{}) {}
  int getBankScrollingOffset() const override { std::abort(); }
  bool isDisplayEncoderLocked() const override { std::abort(); }
  void selectedChannelUpdated() override { std::abort(); }
  // Reject every unrelated virtual path rather than synthesize app behavior.
  void encoderChanged(int) const override { std::abort(); }
  void paramChanged(Parameter *, int) override { std::abort(); }
  void onIdle() override { std::abort(); }
  int getModifiers() const override { std::abort(); }
  int getRadioValue(int, int) const override { std::abort(); }
  bool areFadersLockedToMainMix() const override { std::abort(); }
  void onSelectedChannelChanged() override { std::abort(); }
  void setRadioGroup(int, int, int, bool) override { std::abort(); }
  void onDeviceDisconnected() override { std::abort(); }
};
} // namespace
int main(int argc, char **argv) {
  if (argc < 2)
    return 2;
  std::string op = argv[1];
  if (op == "mode")
    std::cout << Presonus::MappingTable::Item::translateMode(nullable(argv[2]));
  else if (op == "page") {
    Presonus::Surface::PageParam p(argv[2]);
    p.init(nullable(argv[3]), nullable(argv[4]));
    std::cout << std::quoted(p.c_str());
  } else if (op == "name") {
    Presonus::MappablePageComponent p(argv[2]);
    std::cout << std::quoted(p.getPageName());
  } else if (op == "pageconnect") {
    auto pi = info(9, "original");
    NumericParam p(pi);
    Presonus::MappablePageComponent page("p");
    AliasParam *alias = nullptr;
    std::string kind = argv[2];
    if (kind == "alias")
      alias = &page.addMappable(1, "gain");
    else if (kind == "numeric") {
      auto q = info(1, "gain");
      page.addParameters(&q, 1, true);
    }
    bool present = std::atoi(argv[3]);
    auto result = page.connectParameter("gain", present ? &p : nullptr);
    std::cout << "{\"result\":" << result << ",\"calls\":";
    std::vector<std::string> c;
    if (alias)
      c.push_back("[\"alias\"," +
                  std::to_string(alias->getOriginal() != nullptr) + "]");
    emit(c);
    std::cout << '}';
  } else if (op == "disconnect") {
    auto pi = info(9, "original");
    NumericParam p(pi);
    Presonus::MappablePageComponent page("p");
    int n = std::atoi(argv[2]);
    std::vector<AliasParam *> aliases;
    for (int i = 0; i < n; ++i) {
      auto &a = page.addMappable(i, ("a" + std::to_string(i)).c_str());
      a.setOriginal(&p);
      aliases.push_back(&a);
    }
    page.disconnectMappables();
    std::vector<std::string> c;
    for (auto *a : aliases)
      c.push_back("[\"alias\"," + std::to_string(a->getOriginal() != nullptr) +
                  "]");
    emit(c);
  } else if (op == "get") {
    MappingProbe m;
    Component screen("screen");
    auto pi = info(42, "p");
    m.addParameters(&pi, 1, true);
    screen.addParameters(&pi, 1, true);
    if (std::atoi(argv[3]))
      m.bindMainScreenParameters(&screen);
    auto *p = std::atoi(argv[2]) == 7
                  ? m.getParamByTag(std::atoi(argv[4]))
                  : m.getMainScreenParamByTag(std::atoi(argv[4]));
    std::cout << (p != nullptr);
  } else if (op == "connect" || op == "route") {
    auto pi = info(9, "original"), ai = info(1, "alias", ParamInfo::kAlias);
    NumericParam p(pi), other(pi);
    AliasParam alias(ai);
    std::vector<std::string> calls;
    ProviderSignal provider;
    alias.addObserver(&provider);
    ControlProbe control(calls);
    control.provider = &provider;
    LegacyReject legacy;
    bool hasAlias = argc < 10 || std::atoi(argv[9]) != 0;
    Presonus::MappingTable::Item item(hasAlias ? &alias : nullptr, &control);
    presonus::mapping::Entry e{"control", &item};
    Presonus::MappingTable table(&e, 1, legacy);
    if (op == "route") {
      PageProbe page(calls);
      table.useTypedPageControllers();
      table.addMainScreenPage(&page);
      table.connect(argv[2], &p, nullptr, false);
    } else {
      bool found = std::atoi(argv[2]), ctrl = std::atoi(argv[3]),
           param = std::atoi(argv[4]), force = std::atoi(argv[6]),
           same = std::atoi(argv[7]);
      int mode = std::atoi(argv[8]);
      item.control = ctrl ? &control : nullptr;
      control.Control::setParameter(
          same ? (hasAlias ? static_cast<Parameter *>(&alias) : nullptr)
               : &other,
          mode);
      control.setting = false;
      control.mode = mode;
      control.providerBroadcasts = 0;
      control.providerParameterCallbacks = 0;
      calls.clear();
      // CCL provider observations kept separate from explicit application
      // dispatch.
      table.connect(found ? "control" : "missing", param ? &p : nullptr,
                    nullable(argv[5]), force);
      if (found && hasAlias)
        calls.insert(calls.begin(),
                     "[\"alias\"," +
                         std::to_string(alias.getOriginal() != nullptr) + "]");
    }
    emit(calls);
    std::cerr << "actual_CCL_alias_signals=" << provider.actualSignals << "\n";
    std::cerr << "actual_Control_provider_broadcasts="
              << control.providerBroadcasts << "\n";
    std::cerr << "actual_Control_provider_parameter_callbacks="
              << control.providerParameterCallbacks << "\n";
    auto *final = control.getParameter();
    std::cerr << "actual_Control_final_parameter="
              << (!final            ? "null"
                  : final == &alias ? "alias"
                                    : "other")
              << "\n";
    alias.removeObserver(&provider);
  } else
    return 3;
  std::cout << '\n';
}
