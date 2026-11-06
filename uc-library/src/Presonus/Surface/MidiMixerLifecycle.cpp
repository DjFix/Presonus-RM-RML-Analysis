#include "presonus/surface/MidiMixerHandler.hpp"
#include "presonus/surface_panel/ControlHelpers.hpp"
#include <stdexcept>
namespace Presonus::Surface {
void MidiMixerHandler::Observer::paramChanged(Core::Portable::Parameter *p,
                                              int message) {
  // Provider destruction is a source-port lifetime safeguard, not the
  // original ordinary paramChanged implementation (which formats strings).
  if (message == Core::Portable::Parameter::kDestroyed) {
    p->removeObserver(this);
    return;
  }
  owner_.paramChanged(p, message);
}
void MidiMixerHandler::initializeOwnedParameters(
    std::unique_ptr<Core::Portable::Component> local,
    PanelRegistrar &registrar) {
  if (registrar_ || !local || !state_.normalParameters)
    throw std::logic_error("MidiMixerHandler invalid owned initialization");
  // Register first: allocation failure cannot leave an installed observer.
  if (!registrar.addMidiHandler(this))
    throw std::bad_alloc();
  previousLocal_ = state_.localParameters;
  ownedLocal_ = std::move(local);
  state_.localParameters = ownedLocal_.get();
  registrar_ = &registrar;
  if (auto *p = state_.normalParameters->getParameterByTag(0xa007))
    p->addObserver(&observer_);
}
MidiMixerHandler::~MidiMixerHandler() {
  // Borrowed-only historical construction has no lifecycle side effects.
  if (!registrar_)
    return;
  if (auto *p = state_.normalParameters->getParameterByTag(0xa007))
    p->removeObserver(&observer_);
  registrar_->removeMidiHandler(this);
  // CCL owns/deletes the local component's children and parameter list.
  ownedLocal_.reset();
  state_.localParameters = previousLocal_;
}
} // namespace Presonus::Surface
