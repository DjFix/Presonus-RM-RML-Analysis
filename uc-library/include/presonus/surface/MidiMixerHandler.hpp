#pragma once
#include <array>
#include <cstdint>
#include <functional>
#include <string>
#include <vector>
namespace Presonus {
class MappingTable;
}
namespace presonus::surface::midi_port {
// Independent source-port state; no original layout or ownership claim.
struct State {
  bool enabled{};
  std::uint8_t mappingCount{};
  std::int32_t activeMapping{-1};
  // Borrowed terminated 44-byte descriptions. Only byte 0 (name) and byte
  // 37 (eligibility) are interpreted; this is an independent portable record.
  // The caller supplies a readable terminator and valid terminated names.
  const std::array<unsigned char, 44> *controlDescriptions{};
  Presonus::MappingTable *mappingTable{};
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
  int countMappings() const;
  const char *getName() const;
  bool canActivate() const;
  int getActiveMapping() const;
  void setActiveMapping(int);
  void setControlsEnabled(bool);
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
