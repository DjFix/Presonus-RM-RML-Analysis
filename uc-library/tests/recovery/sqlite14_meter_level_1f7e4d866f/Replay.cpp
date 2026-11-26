#include "presonus/panel/meter_level_control.hpp"
#include "presonus/panel/protocol_comm.hpp"
#include "presonus/panel/uart_message.hpp"
#include "presonus/surface_panel/LEDState.hpp"
#include <cassert>
#include <cstring>
#include <iostream>
#include <string>
#include <vector>
using namespace Presonus::Panel;
using presonus::panel::ControlAccess;
using presonus::panel::MeterLevelControlAccess;
using presonus::surface_panel_port::MeterControlAccess;
struct IO : IPanelIO {
  std::vector<std::array<unsigned char, 4>> messages;
  int readMsg(Uart_Msg_Type &) override { return 0; }
  int writeMsg(Uart_Msg_Type &m) override {
    messages.push_back(m.bytes);
    return 0;
  }
  int open(const char *) override { return 0; }
  void close() override {}
  int enableHISpeed(bool) override { return 0; }
};
void observerLifetime() {
  const float db[] = {-60.f, -30.f, -12.f, 0.f};
  MeterControl::setMeterSteps(4, 4, db, db);
  Core::Portable::ParamInfo info{};
  info.type = Core::Portable::ParamInfo::kFloat;
  info.maxValue = 1.f;
  std::strcpy(info.name, "meterLife");
  IO io;
  Core::Portable::NumericParam alternate(info);
  {
    MeterLevelControl control(7);
    control.setIO(&io);
    auto *primary = new Core::Portable::NumericParam(info);
    primary->setNormalized(.5f);
    assert(control.setParameter(primary, 0));
    assert(!control.setParameter(primary, 0));
    assert(control.setParameter(primary, 12));
    assert(ControlAccess::lastLevel(control) == 127);
    assert(control.setClipParameter(&alternate));
    auto n = io.messages.size();
    alternate.setValue(1.f);
    assert(io.messages.size() == n + 2);
    n = io.messages.size();
    primary->setNormalized(1.f);
    assert(io.messages.size() == n + 2);
    delete primary;
    assert(control.getParameter() == nullptr);
    assert(control.castTo(0x4d4c436c) == &control);
    assert(control.getParameterMode() == 12);
  }
  auto n = io.messages.size();
  alternate.setValue(0.f);
  assert(io.messages.size() == n);
}
int main() {
  observerLifetime();
  std::string op;
  int mode, direction, alt, enabled, disabled, meter, custom, action, tag,
      offset, hasPrimary, notifyAlt, repeat;
  float value, clip;
  while (std::cin >> op >> mode >> value >> direction >> alt >> clip >>
         enabled >> disabled >> meter >> custom >> action >> tag >> offset >>
         hasPrimary >> notifyAlt >> repeat) {
    Core::Portable::ParamInfo info{};
    info.type = Core::Portable::ParamInfo::kFloat;
    info.maxValue = 1.f;
    std::strcpy(info.name, meter ? "meterX" : "gainX");
    Core::Portable::NumericParam primary(info), alternate(info);
    primary.setNormalized(value);
    primary.enable(enabled);
    alternate.setValue(clip);
    const float db[] = {-60.f, -30.f, -12.f, 0.f};
    MeterControl::setMeterSteps(4, 4, db, db);
    MeterControl::setDbRange(-60.f, 0.f);
    DbTable customTable(db, 4);
    customTable.setDbRange(-60.f, 0.f);
    int count = 4;
    IO io;
    MeterLevelControl control(tag);
    control.setIO(&io);
    ControlAccess::parameter(control) = hasPrimary ? &primary : nullptr;
    ControlAccess::altParameter(control) = alt ? &alternate : nullptr;
    MeterControlAccess::setState(control, custom ? &count : nullptr, direction);
    MeterLevelControlAccess::customTable(control) =
        custom ? &customTable : nullptr;
    MeterLevelControlAccess::parameterMode(control) =
        op == "setmode" ? 0 : mode;
    MeterLevelControlAccess::transmittedMode(control) =
        op == "setmode" ? 0 : mode;
    MeterLevelControlAccess::offset(control) = offset;
    auto &dispatch = presonus::surface_panel_port::ledDispatchState();
    dispatch.disabled = disabled;
    dispatch.dirty.removeAll();
    dispatch.dirty.resize(16);
    int result = -999;
    if (op == "changed") {
      control.paramChanged(notifyAlt ? &alternate : &primary, action);
      if (repeat)
        control.paramChanged(notifyAlt ? &alternate : &primary, action);
    } else if (op == "broadcast")
      control.broadcastValue(static_cast<int>(value));
    else if (op == "transmit")
      control.transmit();
    else if (op == "steps")
      result = control.getNumMeterSteps(true);
    else if (op == "set" || op == "setmode")
      result = control.setParameter(&primary, mode);
    else
      result = control.setClipParameter(&alternate);
    std::cout << ControlAccess::lastLevel(control) << ' '
              << MeterLevelControlAccess::transmittedMode(control) << ' '
              << MeterLevelControlAccess::blank(control) << ' '
              << MeterLevelControlAccess::clipActive(control) << ' '
              << dispatch.dirty.count() << ' ' << result << ' '
              << io.messages.size();
    for (auto &m : io.messages)
      for (auto b : m)
        std::cout << ' ' << static_cast<int>(b);
    std::cout << '\n';
    dispatch.dirty.removeAll();
    // Seeded pointers were not registered; detach before the genuine
    // destructor.
    ControlAccess::parameter(control) = nullptr;
    ControlAccess::altParameter(control) = nullptr;
  }
}
