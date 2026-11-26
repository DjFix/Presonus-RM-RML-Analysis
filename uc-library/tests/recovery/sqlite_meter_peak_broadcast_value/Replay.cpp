#include "presonus/panel/meter_peak_control.hpp"
#include "presonus/panel/protocol_comm.hpp"
#include "presonus/panel/uart_message.hpp"
#include "presonus/surface_panel/LEDState.hpp"
#include "presonus/surface_panel/MeterControl.hpp"
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <string>
#include <vector>
using namespace Presonus::Panel;
using presonus::panel::ControlAccess;
using presonus::surface_panel_port::MeterControlAccess;
namespace presonus::panel {
struct MeterPeakControlAccess {
  static void seed(MeterPeakControl &c, int offset, const DbTable *table,
                   int mode) {
    c.peakOffset_ = offset;
    c.scaleTable_ = table;
    c.scaleMode_ = mode;
  }
};
} // namespace presonus::panel
struct Sink final : IPanelIO {
  std::vector<Uart_Msg_Type> packets;
  int readMsg(Uart_Msg_Type &) override { std::abort(); }
  int writeMsg(Uart_Msg_Type &m) override {
    packets.push_back(m);
    return 0;
  }
  int open(const char *) override { std::abort(); }
  void close() override { std::abort(); }
  int enableHISpeed(bool) override { std::abort(); }
};
int main(int argc, char **argv) {
  if (argc != 9)
    return 2;
  std::string kind = argv[1], mode = argv[7], table = argv[8];
  int tag = std::stoi(argv[2]);
  auto bits = static_cast<std::uint32_t>(std::stoull(argv[3]));
  int last;
  std::memcpy(&last, &bits, 4);
  int offset = std::stoi(argv[4]), message = std::stoi(argv[6]);
  float value = std::stof(argv[5]);
  const float input[] = {-12.041199826559248f, -6.020599913279624f, 0.f};
  const float output[] = {-6.020599913279624f, 0.f};
  const float over[] = {-18.06179973983887f, -2.4987747321659985f};
  MeterControl::setMeterSteps(3, 2, input, output);
  DbTable overrideTable(over, table == "empty" ? 0 : 2);
  Core::Portable::ParamInfo info{};
  Core::Portable::NumericParam parameter(info);
  parameter.setValueFast(value);
  Sink sink;
  MeterPeakControl c(tag), other(999);
  c.setIO(&sink);
  ControlAccess::lastLevel(c) = last;
  presonus::panel::MeterPeakControlAccess::seed(
      c, offset,
      (table == "override" || table == "empty") ? &overrideTable : nullptr,
      table == "output" ? 1 : 0);
  auto &dispatch = presonus::surface_panel_port::ledDispatchState();
  dispatch.disabled = mode == "direct" ? 0 : 1;
  dispatch.dirty.removeAll();
  dispatch.dirty.resize(0);
  dispatch.dirty.setDelta(1);
  if (mode == "duplicate")
    dispatch.dirty.add(&c);
  if (mode == "room" || mode == "full")
    dispatch.dirty.add(&other);
  if (mode == "room")
    dispatch.dirty.resize(4);
  const auto oldCapacity = dispatch.dirty.getCapacity();
  // Real provider observer registration and base destruction notification.
  if (kind == "param" && message == Core::Portable::Parameter::kDestroyed) {
    ControlAccess::parameter(c) = &parameter;
    parameter.addObserver(&c);
  }
  if (kind == "param")
    c.paramChanged(&parameter, message);
  else if (kind == "broadcast")
    c.broadcastValue(static_cast<int>(std::stoll(argv[5])));
  else
    c.transmit();
  std::cout << static_cast<std::uint32_t>(ControlAccess::lastLevel(c)) << ' '
            << dispatch.dirty.count() << ' ';
  for (int i = 0; i < dispatch.dirty.count(); ++i)
    std::cout << (dispatch.dirty.at(i) == &c) << ' ';
  std::cout << sink.packets.size() << ' ';
  for (auto &m : sink.packets) {
    for (int i = 0; i < 3; ++i)
      std::cout << unsigned(m.bytes[i]) << ' ';
    char encoded[64]{};
    int n = uart_protocol_encode(&m, encoded);
    if (n <= 0)
      return 4;
    std::cout << std::string(encoded, n) << ' ';
  }
  if (kind == "param" && message == Core::Portable::Parameter::kDestroyed &&
      ControlAccess::parameter(c))
    return 6;
  if (mode == "full" && dispatch.dirty.getCapacity() <= oldCapacity)
    return 7;
  std::cout << '\n';
  dispatch.dirty.removeAll();
  dispatch.disabled = 0;
}
