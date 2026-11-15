#pragma once
#include <cstdint>
namespace Presonus::Mixer {
// Stateless partial portable source port. No original inheritance,
// construction, layout, lifecycle or ARM ABI claim. The return declaration is
// provisional.
class GambitMixerComponent {
public:
  struct SourcePortConstruction {};
  explicit GambitMixerComponent(SourcePortConstruction) {}
  virtual std::int32_t numHWMicLineIn() const;
};
} // namespace Presonus::Mixer
