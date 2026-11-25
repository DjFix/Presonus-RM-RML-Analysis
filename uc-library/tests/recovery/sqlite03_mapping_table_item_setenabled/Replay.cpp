#include "presonus/MappingTable.hpp"
#include "presonus/panel/switch_control.hpp"
#include <array>
#include <iostream>
#include <memory>
#include <string_view>
#include <vector>

namespace {
using namespace Presonus::Panel;
using Core::Portable::NumericParam;
using Core::Portable::ParamInfo;
using Presonus::MappingTable;
using presonus::panel::ControlAccess;
using presonus::panel_binding::SwitchAccess;
using Event = std::array<int, 3>;
enum { cast = 1, disable = 2, broadcast = 5, transmitEvent = 6 };

template <typename Base> class Observed : public Base {
public:
  template <typename... Args>
  explicit Observed(std::vector<Event> &events, Args... args)
      : Base(args...), events_(events) {}

  void *castTo(int tag) override {
    events_.push_back({cast, tag, 0});
    return Base::castTo(tag);
  }
  void disableControl(bool disabled, bool reset) override {
    events_.push_back({disable, disabled, reset});
    Base::disableControl(disabled, reset);
  }
  void broadcastValue(int level) override {
    events_.push_back({broadcast, level, 0});
    Base::broadcastValue(level);
  }
  void transmit() override { events_.push_back({transmitEvent, 0, 0}); }

private:
  std::vector<Event> &events_;
};

bool run(std::string_view method, int kind, bool attached, int initial,
         int calls) {
  ParamInfo info{};
  info.type = ParamInfo::kFloat;
  info.minValue = 0.f;
  info.maxValue = 1.f;
  info.defaultValue = 0.25f;
  NumericParam parameter(info);
  parameter.setValue(0.75f);
  std::vector<Event> events;
  std::unique_ptr<Control> control;
  SwitchControl *sw = nullptr;
  if (kind == 1)
    control = std::make_unique<Observed<Control>>(events, 10);
  if (kind == 2)
    control = std::make_unique<Observed<LEDControl>>(events, 10, 11, -1);
  if (kind == 3) {
    auto owned =
        std::make_unique<Observed<SwitchControl>>(events, 10, 11, initial != 0);
    sw = owned.get();
    SwitchAccess::disabled(*sw) = initial != 0;
    control = std::move(owned);
  }
  if (attached && !control->setParameter(&parameter, 0))
    return false;
  if (control)
    ControlAccess::lastLevel(*control) = initial;
  MappingTable::Item item(nullptr, control.get());
  const auto originalLevel = control ? ControlAccess::lastLevel(*control) : 0;
  const auto originalImmediate = sw ? sw->isImmediate() : 0;
  const auto originalDisabled = sw ? SwitchAccess::disabled(*sw) : 0;
  for (int i = 0; i < calls; ++i) {
    bool argument;
    if (!(std::cin >> argument))
      return false;
    events.clear();
    int state = 0;
    if (method == "setenabled") {
      item.setEnabled(argument);
      if (sw)
        state = SwitchAccess::disabled(*sw);
    } else if (method == "setimmediate") {
      item.setImmediate(argument);
      if (sw)
        state = sw->isImmediate();
    } else if (method == "setfulloff") {
      item.setFullOff();
      if (control)
        state = ControlAccess::lastLevel(*control);
    } else {
      return false;
    }
    if (item.control != control.get() || item.alias ||
        (method != "setfulloff" && control &&
         ControlAccess::lastLevel(*control) != originalLevel) ||
        (method != "setimmediate" && sw &&
         sw->isImmediate() != originalImmediate) ||
        (method != "setenabled" && sw &&
         SwitchAccess::disabled(*sw) != originalDisabled) ||
        (attached && (parameter.getValue() != 0.75f ||
                      control->getParameter() != &parameter)))
      return false;
    std::cout << state;
    for (const auto &event : events)
      std::cout << ' ' << event[0] << ' ' << event[1] << ' ' << event[2];
    std::cout << '\n';
  }
  return true;
}
} // namespace

int main(int argc, char **argv) {
  if (argc != 2)
    return 2;
  int kind, initial, calls;
  bool attached;
  while (std::cin >> kind >> attached >> initial >> calls)
    if (!run(argv[1], kind, attached, initial, calls))
      return 1;
  return std::cin.eof() ? 0 : 1;
}
