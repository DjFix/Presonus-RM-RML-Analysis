#pragma once
#include "presonus/mixer/StereoLineComponent.hpp"
namespace Presonus::Mixer {
// Partial real base relationship from hash-bound original RTTI. Construction
// uses only inherited source-port tags; original fields, complete hierarchy,
// lifecycle declarations, object layout and ARM ABI remain unresolved.
class DigitalInputComponent : public StereoLineComponent {
public:
  using StereoLineComponent::StereoLineComponent;
};
} // namespace Presonus::Mixer
