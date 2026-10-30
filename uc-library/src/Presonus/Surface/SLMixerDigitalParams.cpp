#include "presonus/surface/sl_mixer_encoder.hpp"
namespace Presonus::Surface {
void SLMixerHandler::setDigitalParams(Core::Portable::Parameter *first,
                                      Core::Portable::Parameter *second) {
  if (digitalFirst_ != first) {
    if (digitalFirst_)
      digitalFirst_->removeObserver(this);
    digitalFirst_ = first;
    if (first)
      first->addObserver(this);
  }
  if (digitalSecond_ != second) {
    if (digitalSecond_)
      digitalSecond_->removeObserver(this);
    digitalSecond_ = second;
    if (second)
      second->addObserver(this);
  }
}
} // namespace Presonus::Surface
