#pragma once
#include <array>
#include <cstdint>
#include <functional>
#include <string>
#include <vector>
namespace presonus::surface::midi_port {
// Independent source-port state; no original layout or ownership claim.
struct State {
  bool enabled{};
  std::array<std::uint32_t, 17> accumulation{};
  std::vector<std::string> colorControls;
};
struct Services {
  virtual ~Services() = default;
  virtual void setDefaultColor(const std::string &) = 0;
  virtual bool recordParameterPresent() = 0;
  virtual float recordParameterValue() = 0;
  virtual void updateRecordMapping(bool vpot) = 0;
  // Resolve each slot at the time it is visited, permitting first-call
  // mutation.
  virtual bool idleSlotPresent(unsigned slot) = 0;
  virtual void invokeIdleSlot(unsigned slot) = 0;
};
} // namespace presonus::surface::midi_port
namespace Presonus::Surface {
class MidiMixerHandler {
public:
  // Intentional portable constructor and return choices, declarations pending.
  MidiMixerHandler(presonus::surface::midi_port::State &state,
                   presonus::surface::midi_port::Services &services)
      : state_(state), services_(services) {}
  void resetColors();
  const char *getMappingName(int);
  void resetAccumulation();
  void updateRecordReadyMappings();
  void onIdle();

private:
  presonus::surface::midi_port::State &state_;
  presonus::surface::midi_port::Services &services_;
};
} // namespace Presonus::Surface
