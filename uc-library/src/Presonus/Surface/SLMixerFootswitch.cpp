#include "presonus/surface/sl_mixer_encoder.hpp"
namespace Presonus::Surface {
void SLMixerHandler::handleFootswitch(FootswitchMode mode, bool pressed) {
  if (static_cast<int>(mode) == 3) {
    if (footswitchTarget_)
      footswitchTarget_->setValue(pressed ? 1.f : 0.f, true);
    return;
  }
  if (static_cast<int>(mode) != 1)
    return;
  // Original snapshots loop bound but reloads current vector storage/count
  // before each access. The borrowed nonnull vector must remain valid during
  // callbacks; removal/shrink can cause original null error-value dereference
  // and is explicitly outside this portable normal-lifetime domain.
  const int count = footswitchParameters_.count();
  for (int i = 0; i < count; ++i)
    footswitchParameters_.at(i)->setValue(pressed ? 1.f : 0.f, true);
}
} // namespace Presonus::Surface
