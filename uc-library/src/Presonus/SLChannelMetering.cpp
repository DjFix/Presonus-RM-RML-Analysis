#include "presonus/SLChannel.hpp"

namespace Presonus {
void SLChannelBase::idleMeters() {
  levelMeter_.idle();
  for (auto &meter : gainReduction_)
    meter.idle();
}
void SLChannelBase::updateMeter(int kind, float level) {
  switch (kind) {
  case 1818588780:
    levelMeter_.setLevel(level);
    break;
  case 1919247477:
    gainReduction_[0].setLevel(level);
    break;
  case 1668441444:
    gainReduction_[1].setLevel(level);
    break;
  case 1735550308:
    gainReduction_[2].setLevel(level);
    break;
  case 1819436388:
    gainReduction_[3].setLevel(level);
    break;
  }
}
void SLChannelBase::onIdle() {
  Core::Portable::Component::onIdle();
  if (idleTimer_.isLongEnoughYet()) {
    idleMeters();
    idleTimer_.reset();
    idleTimer_.beginAction(-1.f);
  }
}
} // namespace Presonus
