#include "presonus/surface/sl_mixer_encoder.hpp"
namespace Presonus::Surface {
SLMixerHandler::SLMixerHandler(OwnedLifecycle, EQPageComponent *eq,
                               GeqPageComponent *geq,
                               Presonus::IColorConverter *ownedConverter)
    : encoderTimer_(1.f), ownedLifecycle_(true),
      ownedColorConverter_(ownedConverter), lifecycleGeqPage_(geq) {
  eqPage_ = eq;
  if (eqPage_)
    eqPage_->addObserver(this);
  if (lifecycleGeqPage_)
    lifecycleGeqPage_->addObserver(this);
}
SLMixerHandler::~SLMixerHandler() {
  if (ownedLifecycle_) {
    if (eqPage_)
      eqPage_->removeObserver(this);
    if (lifecycleGeqPage_)
      lifecycleGeqPage_->removeObserver(this);
    setDigitalParams(nullptr, nullptr);
    delete ownedColorConverter_;
  }
  // Real CCL member providers and DelayTimer finish normal cleanup. The
  // compatibility constructor's borrowed page identities are never owned here.
}
} // namespace Presonus::Surface
