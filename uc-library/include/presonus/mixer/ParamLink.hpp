#pragma once
#include "core/portable/coreparams.h"
#include "presonus/mixer/ControlMapping.hpp"
namespace Core::Portable {
class Component;
}
namespace Presonus {
class MixerClientComponentBase;
}
namespace Presonus::Mixer {
// Portable source port using the real canonical base and pinned CCL observer.
// Native fields/secondary vtable offsets are evidence, not a host layout claim.
class ParamLink : public ControlMapping,
                  public Core::Portable::ParamObserverBase {
public:
  ParamLink(Core::Portable::Parameter *, const char *, bool);
  // Independent source-port cleanup; no original ParamLink destructor
  // recovered.
  ~ParamLink();
  void paramChanged(Core::Portable::Parameter *, int) override;
  void connect(Presonus::MixerClientComponentBase *);
  // Explicit identity-checked bridge for original embedded root Component+0x30.
  void portableBindClientRoot(Presonus::MixerClientComponentBase &client,
                              Core::Portable::Component &root) {
    client_ = &client;
    clientRoot_ = &root;
  }
  bool portableFlag() const { return flag_; }
  Core::Portable::Parameter *portableTarget() const { return target_; }
  void portableSetTarget(Core::Portable::Parameter *target) {
    target_ = target;
  }

private:
  Presonus::MixerClientComponentBase *client_ = nullptr;
  Core::Portable::Component *clientRoot_ = nullptr;
  bool flag_;
  Core::Portable::Parameter *target_;
  Core::Portable::Parameter *observed_;
};
} // namespace Presonus::Mixer
