#include "presonus/DAWTimeInfo.hpp"
#include <cstdlib>
#include <iostream>
namespace Presonus::UC {
class TimeCodeEvent {};
class MessageAttributes {};
} // namespace Presonus::UC
struct Boundary final : Presonus::DAWTimeInfo::Services {
  unsigned updates = 0;
  void updateTempo(const Presonus::UC::MessageAttributes &) override {
    ++updates;
  }
  void updateSignature(const Presonus::UC::MessageAttributes &) override {
    ++updates;
  }
  std::array<Core::Portable::Parameter *, 3>
  parameters(Presonus::DAWClientComponent &) override {
    throw 1;
  }
  unsigned eventKind(const Presonus::UC::TimeCodeEvent &) const override {
    return 0;
  }
  unsigned count(const Presonus::UC::TimeCodeEvent &) const override {
    return 0;
  }
  Item item(const Presonus::UC::TimeCodeEvent &, unsigned) const override {
    throw 1;
  }
  void append(Presonus::UC::TimeCodeEvent &, const Item &) override {
    ++updates;
  }
  void print(std::array<char, 32> &, const Item &, unsigned) override {
    throw 1;
  }
  void locate(Presonus::DAWClientComponent &,
              const Presonus::DAWTimeInfo::TimeString &, bool, bool) override {
    throw 1;
  }
  void locateRelative(Presonus::DAWClientComponent &, int,
                      const Presonus::DAWTimeInfo::TimeString &, bool,
                      bool) override {
    throw 1;
  }
};
int main() {
  // Raw borrowed bytes retain full zero-extension, including non-boolean 255.
  unsigned char borrowed[309]{};
  Presonus::DAWTimeInfo raw(borrowed);
  for (unsigned byte : {0u, 1u, 255u}) {
    borrowed[0x134] = static_cast<unsigned char>(byte);
    if (raw.isMusicalDisplay() != byte)
      std::abort();
  }
  // The independent mutable State wins over conflicting legacy bytes.
  // All three parameter pointers are explicitly null: setters perform no
  // provider calls on this domain; production uses actual CCL Parameter.
  Presonus::DAWTimeInfo::State mutableState;
  mutableState.parameters.fill(nullptr);
  Presonus::DAWTimeInfo adapted(borrowed, mutableState);
  for (bool flag : {false, true}) {
    mutableState.musicalDisplay = flag;
    if (adapted.isMusicalDisplay() != unsigned(flag))
      std::abort();
  }
  mutableState.musicalDisplay = false;
  if (adapted.isMusicalDisplay() != 0)
    std::abort();
  adapted.setMusicalDisplay(true);
  if (adapted.isMusicalDisplay() != 1)
    std::abort();
  adapted.setMusicalDisplay(false);
  if (adapted.isMusicalDisplay() != 0)
    std::abort();

  for (unsigned method = 0; method < 10; ++method)
    for (unsigned flag = 0; flag < 2; ++flag) {
      unsigned char old[309]{};
      Boundary boundary;
      Presonus::DAWTimeInfo::State state;
      state.services = &boundary;
      state.musicalDisplay = flag;
      state.milliSeconds = flag;
      state.locating = flag;
      Presonus::DAWTimeInfo value(old, state);
      Presonus::UC::TimeCodeEvent event;
      Presonus::UC::MessageAttributes attrs;
      Presonus::DAWTimeInfo::TimeString time;
      switch (method) {
      case 0:
        value.updateTimeContext(attrs);
        break;
      case 1:
        value.displayMilliSeconds(flag);
        break;
      case 2:
        value.setMusicalDisplay(flag);
        break;
      case 3:
        value.updateTimeParam(nullptr, time);
        break;
      case 4:
        value.init(nullptr);
        break;
      case 5:
        value.locateTransport(time);
        break;
      case 6:
        value.locateTransportRelative(0);
        break;
      case 7:
        value.updateTime(event);
        break;
      case 8:
        value.parseTime(event, time);
        break;
      case 9:
        value.createTimeEvent(event, time);
        break;
      }
      std::cout << method << ' ' << flag << ' ' << state.musicalDisplay << ' '
                << state.locating << ' ' << state.milliSeconds << ' '
                << boundary.updates << '\n';
    }
}
