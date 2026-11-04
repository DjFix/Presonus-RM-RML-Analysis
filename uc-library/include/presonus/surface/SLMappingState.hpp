#pragma once
#include "presonus/MappingTable.hpp"
#include "presonus/surface/sl_mixer_encoder.hpp"
namespace presonus::surface {
// Independent source-port composition. No original member/layout or ownership
// declaration is asserted. Parameter storage and tree behavior come from CCL.
struct SLMappingState {
  Core::Portable::ParamList parameters;
  Core::Portable::Component *mixer = nullptr;
  bool hasSecondaryMixer = false;
  bool bankSwitchBlocked = false;
  bool meterModeTwo = false;
  Presonus::MappingTable *mappingTable = nullptr;
  Core::Portable::Component *banks[5]{};
  Core::Portable::Component *secondaryInputs = nullptr;
  Core::Portable::Component *groups = nullptr;
  Core::Vector<Core::Portable::Component *> busGeqs;
  Core::Portable::Component *mainGeqs[2]{};
};
struct SLMappingAccess {
  static void bindEq(Presonus::Surface::SLMixerHandler &v,
                     Presonus::Surface::EQPageComponent *p) {
    v.eqPage_ = p;
  }
  static void bind(Presonus::Surface::SLMixerHandler &v, SLMappingState &s) {
    v.mappingState_ = &s;
  }
};
} // namespace presonus::surface
