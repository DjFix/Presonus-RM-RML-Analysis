#pragma once
#include "presonus/mixer/OutputComponent.hpp"
#include "presonus/trial08/MixerComponentBase.hpp"
#include <cstdint>
#include <vector>

namespace presonus::frontier01 {
// Independent portable state, named by observed native stores, not ARM fields.
struct SendState {
  presonus::output_port::Bindings &output;
  std::uint32_t sendChanged{};  // observed native +0x178
  std::uint32_t childChanged{}; // observed native +0x18c
};
} // namespace presonus::frontier01

namespace Presonus::Mixer {
// Partial source-port facades. Composition is intentional: no original complete
// inheritance, field layout, ownership or unencoded return declaration claim.
class RackMixerComponent {
public:
  RackMixerComponent(MixerComponentBase &base, std::uint32_t &cascadeState)
      : base_(base), cascadeState_(cascadeState) {}
  void onCascadeStateChange();

private:
  MixerComponentBase &base_;
  std::uint32_t &cascadeState_;
};
class SendOutputComponent {
public:
  SendOutputComponent(OutputComponent &base,
                      presonus::frontier01::SendState &state,
                      std::vector<presonus::frontier01::SendState *> &children)
      : base_(base), state_(state), children_(children) {}
  void paramChanged(Core::Portable::Parameter *, int);

private:
  OutputComponent &base_;
  presonus::frontier01::SendState &state_;
  std::vector<presonus::frontier01::SendState *> &children_;
};
// CCL-backed lifecycle source ports. Native D1 writes its own two vtable words
// and calls Component D2; compiler emits host vptr transitions and real pinned
// Component cleanup. Original secondary base declaration/layout remain unknown.
class GlobalComponent : public Core::Portable::Component {
public:
  using Core::Portable::Component::Component;
  ~GlobalComponent() override;
};
class GEQLinkHandler : public Core::Portable::Component {
public:
  using Core::Portable::Component::Component;
  ~GEQLinkHandler() override;
};
} // namespace Presonus::Mixer
