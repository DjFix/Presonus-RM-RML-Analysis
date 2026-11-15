#include "presonus/mixer/TalkbackInputComponent.hpp"
#include "core/public/corevector.h"
#include "presonus/mixer/MixerComponentBase.hpp"
namespace Presonus::Mixer {
std::uint8_t TalkbackInputComponent::isPostFaderAux(int) {
  return talkbackState().postFader;
}
void TalkbackInputComponent::addRemoveObservers(bool add) {
  auto *mixer = talkbackState().mixer;
  if (!mixer)
    throw std::logic_error("Talkback mixer is unbound");
  Core::Vector<Core::Portable::Parameter *> parameters;
  if (auto *settings = mixer->sceneSettings) {
    parameters.add(settings->getParameterByTag(49));
    parameters.add(settings->getParameterByTag(5));
  }
  auto *observer = static_cast<Core::Portable::IParamObserver *>(this);
  for (int i = 0; i < parameters.count(); ++i) {
    // The native method requires both parameters when settings is present;
    // a missing parameter is outside the valid binding domain, not skipped.
    auto *parameter = parameters[i];
    if (!parameter)
      throw std::logic_error("Talkback settings parameter is absent");
    if (add)
      parameter->addObserver(observer);
    else
      parameter->removeObserver(observer);
  }
}
} // namespace Presonus::Mixer
