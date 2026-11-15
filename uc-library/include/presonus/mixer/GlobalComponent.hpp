#pragma once
#include "core/portable/coreparams.h"
#include "presonus/mixer/MixerComponentBase.hpp"
#include "presonus/mixer/OutputComponent.hpp"
#include <cstdint>
#include <vector>

namespace Presonus::Mixer {
// Partial source-port facades. Composition is intentional: no original complete
// inheritance, field layout, ownership or unencoded return declaration claim.
// CCL-backed lifecycle source ports. Native D1 writes its own two vtable words
// and calls Component D2; compiler emits host vptr transitions and real pinned
// Component cleanup. Original secondary base declaration/layout remain unknown.
class GlobalComponent : public Core::Portable::Component {
public:
  using Core::Portable::Component::Component;
  GlobalComponent() = default;
  explicit GlobalComponent(MixerComponentBase &mixer);
  ~GlobalComponent() override;
  // Borrowed actual numeric providers; no original ARM field layout claim.
  void bindHighDefParameters(Core::Portable::NumericParam *source,
                             Core::Portable::NumericParam *destination) {
    highDefSource_ = source;
    highDefDestination_ = destination;
  }
  // Provisional void return; original unencoded return remains pending.
  void updateHighDef();
  // Preserve original misspelling and provisional void return.
  void initalize();
  void bindMixer(MixerComponentBase &mixer) { mixer_ = &mixer; }
  Core::Portable::FileName getTempFilePath();

private:
  Core::Portable::NumericParam *highDefSource_ = nullptr;
  Core::Portable::NumericParam *highDefDestination_ = nullptr;
  MixerComponentBase *mixer_ = nullptr; // borrowed source-port binding
};
} // namespace Presonus::Mixer
