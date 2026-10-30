#include "presonus/surface_panel/LEDState.hpp"
#include <array>
#include <cstdint>
#include <cstdio>
#include <fstream>
#include <sstream>
#include <string>
#include <vector>

using Presonus::Panel::LEDControl;
using presonus::surface_panel_port::LEDStateAccess;
using State = std::array<std::uint32_t, 5>;
struct Event {
  char kind;
  std::uint32_t pointerMatches;
  std::uint32_t message;
  State state;
  bool operator==(const Event &other) const {
    return kind == other.kind && pointerMatches == other.pointerMatches &&
           message == other.message && state == other.state;
  }
};
struct CapturingLED final : LEDControl {
  CapturingLED() : LEDControl(0, 0, -1) {}
  ~CapturingLED() override {
    presonus::panel::ControlAccess::parameter(*this) = nullptr;
  }
  Core::Portable::Parameter *expectedParameter = nullptr;
  std::vector<Event> events;
  void transmit() override {
    events.push_back({'T', 0, 0, LEDStateAccess::state(*this)});
  }
  void paramChanged(Core::Portable::Parameter *parameter,
                    int message) override {
    events.push_back({'P', parameter == expectedParameter,
                      static_cast<std::uint32_t>(message),
                      LEDStateAccess::state(*this)});
  }
};
int main(int argc, char **argv) {
  if (argc != 2)
    return 2;
  std::ifstream input(argv[1]);
  std::string line;
  unsigned cases = 0;
  while (std::getline(input, line)) {
    std::istringstream row(line);
    char operation;
    unsigned role, present, eventCount;
    std::uint32_t argument;
    State before{}, after{};
    row >> operation >> role >> argument >> present;
    for (auto &value : before)
      row >> value;
    for (auto &value : after)
      row >> value;
    row >> eventCount;
    std::vector<Event> expected;
    for (unsigned i = 0; i < eventCount; ++i) {
      Event event{};
      row >> event.kind >> event.pointerMatches >> event.message;
      for (auto &value : event.state)
        row >> value;
      expected.push_back(event);
    }
    if (!row)
      return 3;
    CapturingLED control;
    int opaqueToken = 0;
    auto *parameter =
        present ? reinterpret_cast<Core::Portable::Parameter *>(&opaqueToken)
                : nullptr;
    control.expectedParameter = parameter;
    LEDStateAccess::setState(control, parameter, before);
    const auto value = static_cast<std::int32_t>(argument);
    switch (operation) {
    case 'M':
      control.setmatchvalue(value);
      break;
    case 'B':
      control.setBlinkMode(static_cast<LEDControl::BlinkMode>(value));
      break;
    case 'C':
      control.setColor(static_cast<RGBLedColors>(value));
      break;
    case 'F':
      control.setFullOff();
      break;
    case 'V':
      control.broadcastValue(value);
      break;
    default:
      return 4;
    }
    if (LEDStateAccess::state(control) != after || control.events != expected) {
      std::fprintf(stderr, "Mismatch case %u op %c role %u events %zu/%zu\n",
                   cases, operation, role, control.events.size(),
                   expected.size());
      return 1;
    }
    ++cases;
  }
  if (!input.eof() || cases == 0)
    return 5;
  std::printf("PASS: %u original ARM LEDControl state/dispatch cases\n", cases);
}
